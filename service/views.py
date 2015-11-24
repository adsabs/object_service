from flask import current_app, request
from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
from flask.ext.cache import Cache
from SIMBAD import get_simbad_data
from SIMBAD import do_position_query
from SIMBAD import parse_position_string
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
        objects = []
        try:
            identifiers = request.json['identifiers']
            input_type  = 'identifiers'
        except:
            try:
                identifiers = request.json['objects']
                input_type  = 'objects'
            except:
                current_app.logger.error('No identifiers and objects were specified for SIMBAD object query')
                return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}, 200
        # We should either have a list of identifiers or a list of object names
        if len(identifiers) == 0 and len(objects) == 0:
            current_app.logger.error('No identifiers and objects were specified for SIMBAD object query')
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}, 200
        id_num = len(identifiers)
        if id_num == 0:
            return {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}, 200
        # Source to query 
        source = 'simbad'
        # Now check if we have anything cached for them
        cached = {id:current_app.cache.get(id.upper()) for id in identifiers if current_app.cache.get(id.upper())}
        if source in ['simbad','all'] and len(identifiers) > 0:
             # If we have cached values, filter those out from the initial list
            if cached:
                current_app.logger.debug('Received %s %s. Using %s entries from cache.' % (id_num, input_type, len(cached)))
                identifiers = [id for id in identifiers if id.upper() not in cached]
            if identifiers:
                ident_upper = [i.upper() for i in identifiers]
                # We have identifiers, not found in the cache
                result = get_simbad_data(identifiers, input_type)
                if 'Error' in result:
                    # An error was returned!
                    current_app.logger.error('Failed to find data for SIMBAD %s query!'%input_type)
                    return result
                else:
                    # We have results!
                    duration = time.time() - stime
                    current_app.logger.info('Found objects for SIMBAD %s in %s user seconds.' % (input_type, duration))
                    # Before returning results, cache them
                    for ident, value in result['data'].items():
                        current_app.cache.set(ident.upper(), value, timeout=current_app.config.get('OBJECTS_CACHE_TIMEOUT'))
                    # Now pick the entries in the results that correspond with the original object names
                    if input_type == 'objects':
                        result['data'] = {k: result['data'].get(k.upper()) for k in identifiers}
                    # If we had results from cache, merge these in
                    if cached:
                        res = cached.copy()
                        res.update(result.get('data',{}))
                        return res
                    # Otherwise just send back the results
                    else:
                        return result.get('data',{})
            elif cached:
                # We only had cached results
                return cached
            else:
                # This should never happen
                current_app.logger.error('No data found, even though we had %s! Should never happen!'%input_type)
                result = {
                    "Error": "Failed to find data for SIMBAD %s query!"%input_type,
                    "Error Info": "No results found, where results were expected! Needs attention!"
                    }
                return result

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
