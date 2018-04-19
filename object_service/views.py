from flask import current_app, request
from flask_restful import Resource
from flask_discoverer import advertise
from flask import Response
from SIMBAD import get_simbad_data
from SIMBAD import do_position_query
from SIMBAD import parse_position_string
from NED import get_ned_data
from NED import get_NED_refcodes
from utils import get_objects_from_query_string
from utils import translate_query
import time
import timeout_decorator

class IncorrectPositionFormatError(Exception):
    pass

class ObjectSearch(Resource):

    """Return object identifiers for a given object string"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def post(self):
        stime = time.time()
        # Get the supplied list of identifiers
        identifiers = []
        input_type = None
        # determine whether a source for the data was specified
        try:
            source = request.json['source'].lower()
        except:
            source = 'simbad'
        # We only deal with SIMBAD or NED as source
        if source not in ['simbad','ned']:
            current_app.logger.error('Unsupported source for object data specified: %s'%source)
            return {"Error": "Unable to get results!",
                   "Error Info": "Unsupported source for object data specified: %s"%source}, 200
        for itype in ['identifiers', 'objects']:
            try:
                identifiers = request.json[itype]
                identifiers = map(str, identifiers)
                input_type  = itype
            except:
                pass
        if not input_type:
            current_app.logger.error('No identifiers and objects were specified for SIMBAD object query')
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}, 200
        # We should either have a list of identifiers or a list of object names
        if len(identifiers) == 0:
            current_app.logger.error('No identifiers or objects were specified for SIMBAD object query')
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}, 200
        # We have a known object data source and a list of identifiers. Let's start!
        # We have identifiers
        if source == 'simbad':
            result = get_simbad_data(identifiers, input_type)
        else:
            if input_type == 'identifiers':
                input_type = 'simple'
            result = get_ned_data(identifiers, input_type)
        if 'Error' in result:
            # An error was returned!
            err_msg = result['Error Info']
            current_app.logger.error('Failed to find data for %s %s query (%s)!'%(source.upper(), input_type,err_msg))
            return result
        else:
            # We have results!
            duration = time.time() - stime
            current_app.logger.info('Found objects for %s %s in %s user seconds.' % (source.upper(), input_type, duration))
            # Now pick the entries in the results that correspond with the original object names
            if input_type == 'objects':
#                result['data'] = {k: result['data'].get(k.upper()) for k in identifiers}
                result['data'] = {k: result['data'].get(k) or result['data'].get(k.upper())  for k in identifiers}
            # Send back the results
            return result.get('data',{})

class PositionSearch(Resource):

    """Return publication information for a cone search"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]
    def get(self, pstring):
        # The following position strings are supported
        # 1. 05 23 34.6 -69 45 22:0 6 (or 05h23m34.6s -69d45m22s:0m6s)
        # 2. 05 23 34.6 -69 45 22:0.166666 (or 05h23m34.6s -69d45m22s:0.166666)
        # 3. 80.89416667 -69.75611111:0.166666
        stime = time.time()
        # If we're given a string with qualifiers ('h', etc), convert to one without
        current_app.logger.info('Attempting SIMBAD position search: %s'%pstring)
        try:
            RA, DEC, radius = parse_position_string(pstring)
        except Exception, err:
            current_app.logger.error('Position string could not be parsed: %s' % pstring)
            return {'Error': 'Unable to get results!',
                    'Error Info': 'Invalid position string: %s'%pstring}, 200
        try:
            result = do_position_query(RA, DEC, radius)
        except timeout_decorator.timeout_decorator.TimeoutError:
            current_app.logger.error('Position query %s timed out' % pstring)
            return {'Error': 'Unable to get results!',
                    'Error Info': 'Position query timed out'}, 200
        return result

class QuerySearch(Resource):

    """Given a Solr query with object names, return a Solr query with SIMBAD identifiers"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def post(self):
        stime = time.time()
        # Get the supplied list of identifiers
        identifiers = []
        query = None
        itype = None
        name2id = {}
        try:
            query = request.json['query']
            input_type = 'query'
        except:
            current_app.logger.error('No query was specified for the  object search')
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}, 200
        # If we get the request from BBB, the value of 'query' is actually an array
        if isinstance(query, list):
            solr_query = query[0]
        else:
            solr_query = query
        current_app.logger.info('Received object query: %s'%solr_query)
        # This query will be split up into two components: a SIMBAD and a NED object query
        simbad_query = solr_query.replace('object:','simbid:')
        ned_query = solr_query.replace('object:','nedid:')
        # Check if an explicit target service was specified
        try:
            target = request.json['target']
        except:
            target = 'all'
        # If we receive a (Solr) query string, we need to parse out the object names
        try:
            identifiers = get_objects_from_query_string(solr_query)
        except Exception, err:
            current_app.logger.error('Parsing the identifiers out of the query string blew up!')
            return {"Error": "Unable to get results!",
                    "Error Info": "Parsing the identifiers out of the query string blew up! (%s)"%str(err)}, 200
        identifiers = [iden for iden in identifiers if iden.lower() not in ['object',':']]
        # How many object names did we fid?
        id_num = len(identifiers)
        # Keep a list with the object names we found
        identifiers_orig = identifiers
        # If we did not find any object names, there is nothing to do!
        if id_num == 0:
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in Solr object query"}, 200
        # Get translations
        simbad_query = ''
        ned_query = ''
        translated_query = ''
        if target.lower() in ['simbad', 'all']:
            name2simbid = {}
            for ident in identifiers:
                result = get_simbad_data([ident], 'objects')
                if 'Error' in result or 'data' not in result:
                    # An error was returned!
                    current_app.logger.error('Failed to find data for SIMBAD object {0}!: {1}'.format(ident, result.get('Error Info','NA')))
                    name2simbid[ident] = 0
                    continue
                try:
                    SIMBADid =[e.get('id',0) for e in result['data'].values()][0]
                except:
                    SIMBADid = "0"
                name2simbid[ident] = SIMBADid
            simbad_query = translate_query(solr_query, identifiers, name2simbid, 'simbid:')
        if target.lower() in ['ned', 'all']:
            name2nedid = {}
            for ident in identifiers:
                result = get_ned_data([ident], 'objects')
                if 'Error' in result or 'data' not in result:
                    # An error was returned!
                    current_app.logger.error('Failed to find data for NED object {0}!: {1}'.format(ident, result.get('Error Info','NA')))
                    name2nedid[ident] = 0
                    continue
                try:
                    NEDid =[e.get('id',0) for e in result['data'].values()][0]
                except:
                    NEDid = 0
                name2nedid[ident] = str(NEDid)
            ned_query = translate_query(solr_query, identifiers, name2nedid, 'nedid:')

        if simbad_query and ned_query:
            translated_query = '({0}) OR ({1})'.format(simbad_query, ned_query)
        elif simbad_query:
            translated_query = simbad_query
        elif ned_query:
            translated_query = ned_query
        else:
            translated_query = 'simbid:0'
 
        return {'query': translated_query}        

class ClassicObjectSearch(Resource):

    """Return object NED refcodes for a given object list"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def post(self):
        stime = time.time()
        results = {}
        # Get the supplied list of identifiers
        if not request.json or 'objects' not in request.json:
                current_app.logger.error('No objects were provided to Classic Object Search')
                return {'Error': 'Unable to get results!',
                            'Error Info': 'No object names found in POST body'}, 200

        results = get_NED_refcodes(request.json)

        if "Error" in results:
            error_info = results.get('Error Info', 'NA')
            current_app.logger.error('Classic Object Search request request blew up. Error info: %s' % error_info)
            return results, 500
        duration = time.time() - stime
        current_app.logger.info('Classic Object Search request successfully completed in %s real seconds'%duration)
        # what output format?
        try:
            oformat = request.json['output_format']
        except:
            oformat = 'json'
        # send the results back in the requested format
        if oformat == 'json':
            return results
        else:
            output = "\n".join(results['data'])
            return Response(output, mimetype='text/plain; charset=us-ascii')
            
