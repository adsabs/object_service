from flask import current_app, request
from flask_restful import Resource
from flask_discoverer import advertise
from flask import Response
from SIMBAD import get_simbad_data
from SIMBAD import simbad_position_query
from SIMBAD import verify_tap_service

from NED import get_ned_data
from NED import get_NED_refcodes
from NED import ned_position_query

from utils import parse_query_string
from utils import get_object_translations
from utils import translate_query
from utils import isBalanced
from utils import parse_position_string
from utils import verify_query

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
        # Verify which TAP service to use
        u = verify_tap_service()
        current_app.config['OBJECTS_SIMBAD_TAP_URL'] = u
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
        # For a SIMBAD query with type "identifiers", the list should contain only integers
        if source == 'SIMBAD' and input_type == 'identifiers':
            wrong_identifiers = [e for e in identifiers if not str(e).isdigit()]
            if len(wrong_identifiers) > 0:
                current_app.logger.error('Warning! Found non-integer SIMBAD identifiers: %s'% ",".join(wrong_identifiers))
            # remove any non-integer identifiers
            identifiers = [e for e in identifiers if str(e).isdigit()]
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
            current_app.logger.error('Original request: %s'%str(request.json))
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

class QuerySearch(Resource):

    """Given a Solr query with object names, return a Solr query with SIMBAD identifiers"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def post(self):
        stime = time.time()
        # Verify which TAP service to use
        try:
            u = verify_tap_service()
            current_app.config['OBJECTS_SIMBAD_TAP_URL'] = u
        except:
            # This is not supposed to throw an exception, but
            # if so, we continue with the CDS TAP service
            current_app.config['OBJECTS_SIMBAD_TAP_URL'] = current_app.config.get('OBJECTS_SIMBAD_TAP_URL_CDS')
        # Get the supplied list of identifiers
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
        translated_query = solr_query
        current_app.logger.info('Received object query: %s'%solr_query)
        # Check if an explicit target service was specified
        try:
            targets = [t.strip() for t in request.json['target'].lower().split(',')]
        except:
            targets = ['simbad', 'ned']
        # Get the object names and individual object queries from the Solr query
        try:
            object_names, object_queries = parse_query_string(solr_query)
        except Exception, err:
            current_app.logger.error('Parsing the identifiers out of the query string blew up!')
            return {"Error": "Unable to get results!",
                    "Error Info": "Parsing the identifiers out of the query string blew up! (%s)"%str(err)}, 200
        # If no object names were found, return
        if len(object_names) == 0:
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in Solr object query"}, 200
        # First we check if the object query was in fact a cone search. This would have been a queery of the form
        #  object:"80.89416667 -69.75611111:0.166666"
        # resulting in 1 entry in the variable object_queries (namely: ['object:"80.89416667 -69.75611111:0.166666"'])
        # and with 1 entry in object_names (namely: [u'80.89416667 -69.75611111:0.166666']).
        is_cone_search = False
        if len(object_queries) == 1:
            # We received a cone search, which needs to be translated into a query in terms of 'simbid' and 'nedid'
            try:
                coordinates, radius = parse_position_string(object_names[0])
                RADEC = coordinates.to_string('hmsdms')
                current_app.logger.info('Starting cone search at RA, DEC, radius: {0}, {1}'.format(RADEC, radius))
                is_cone_search = True
            except:
                pass
        # If this is a comne search, we go a different path
        if is_cone_search:
            result = {'simbad':[], 'ned':[]}
            simbad_fail = False
            ned_fail = False
            sids = simbad_position_query(coordinates, radius)
            if len(sids) > 0:
                vq = verify_query(sids, 'simbid')
                if not vq:
                    current_app.logger.info('SIMBAD identifiers not in Solr index: {0}'.format(",".join(sids)))
                    simbad_fail = 'SIMBAD identifiers not found in Solr index'
                    sids = []
            result['simbad'] = sids
            if 'Error' in result['simbad']:
                simbad_fail = result['simbad']['Error Info']
            nids = ned_position_query(coordinates, radius)
            if len(nids) > 0:
                vq = verify_query(nids, 'nedid')
                if not vq:
                    current_app.logger.info('NED identifiers not in Solr index: {0}'.format(",".join(nids)))
                    ned_fail = 'NED identifiers not found in Solr index'
                    nids = []
            result['ned'] = nids
            if 'Error' in result['ned']:
                ned_fail = result['ned']['Error Info']
            # If both SIMBAD and NED errored out, return an error
            if simbad_fail and ned_fail:
                return {"Error": "Unable to get results!", 
                        "Error Info": "{0}, {1}".format(simbad_fail, ned_fail)}, 200
            # Form the query in terms on simbid and nedid:
            cone_components = []
            if len(result['simbad']) > 0:
                cone_components.append('simbid:({0})'.format(" OR ".join(result['simbad'])))
            if len(result['ned']) > 0:
                cone_components.append('nedid:({0})'.format(" OR ".join(result['ned'])))
            oquery = "({0})".format(" OR ".join(cone_components))
            translated_query = solr_query.replace(object_queries[0], oquery)
            return {'query': translated_query}
        # Create the translation map from the object names provided to identifiers indexed in Solr (simbid and nedid)
        name2id = get_object_translations(object_names, targets)
        # Now we have all necessary information to created the translated query
        translated_query = translate_query(solr_query, object_queries, targets, object_names, name2id)
 
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
            status = 400
            error_info = results.get('Error Info', 'NA')
            if error_info.find('timed out') > -1:
                status = 504
            current_app.logger.error('Classic Object Search request request blew up. Error info: %s' % error_info)
            return results, status
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
            
