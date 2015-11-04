from flask import current_app, request
from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
from flask.ext.cache import Cache
from SIMBAD import get_simbad_identifiers
from SIMBAD import get_simbad_objects
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

    def get(self, **kwargs):
        # Given the input objects, the following happens:
        # 1. translate user-supplied object names to canonical SIMBAD names
        #    (caching is key-ed on canonical names)
        # 2. retrieve results from cache
        # 3. for remainder retrieve results from SIMBAD
        # 4. return the combined results (cache + SIMBAD)
        stime = time.time()
        # Create a list from the comma-separated input string
        try:
            objects = [o.strip() for o in kwargs.get('objects').split(',')]
        except:
            objects = []
        object_num = len(objects)
        # Find out for which service we want object identifiers (SIMBAD, NED or both)
        source = kwargs.get('source','all').lower()
        if source in ['simbad','all'] and len(objects) > 0:
            # See if we happen to have results stored in our cache
            cached = [current_app.cache.get(o) for o in objects]
            # Remove all 'None' entries
            cached = filter(None, cached)
            # and remove the cached objects from our initial list
            if cached:
                current_app.logger.debug('Received %s objects. Using %s entries from cache.' % (object_num, len(cached)))
                objects = [o for o in objects if o not in [co['object'] for co in cached if co]]
            if objects:
                # Have objects that were not in the cache (and may have cached results)
                result = get_simbad_identifiers(objects)
                if 'Error' in result:
                    # An error was returned!
                    current_app.logger.error('Failed to find identifiers for SIMBAD object query!')
                    return result
                else:
                    # We have results!
                    duration = time.time() - stime
                    current_app.logger.info('Found identifiers for SIMBAD objects in %s user seconds.' % duration)
                    # Before returning results, cache them
                    for item in result.get('data',[]):
                        current_app.cache.set(item['object'], item, timeout=current_app.config.get('OBJECTS_CACHE_TIMEOUT'))
                    if cached:
                        return cached + result.get('data',[])
                    else:
                        return result.get('data',[])
            elif cached:
                # We only had cached results
                return cached
            else:
                # This should never happen
                current_app.logger.error('No identifiers found, even though we had objects! Should never happen!')
                result = {
                    'Error': 'Failed to find identifiers for SIMBAD object query!',
                    'Error Info': 'No results found, where results were expected! Needs attention!'
                    }
                return result

    def post(self):
        stime = time.time()
        # Get the supplied list of identifiers
        try:
            identifiers = request.json['identifiers']
        except:
            current_app.logger.error('No identifiers were specified for SIMBAD object query')
            return {'Error': 'Unable to get results!',
                    'Error Info': 'No identifiers found in POST body'}, 200
        id_num = len(identifiers)
        if id_num == 0:
            return {'Error': 'Unable to get results!',
                    'Error Info': 'No identifiers found in POST body'}, 200
        # Source to query 
        source = 'simbad'
        # Now check if we have anything cached for them
        cached = [current_app.cache.get(id) for id in identifiers]
        # Filter out any 'None' values
        cached = filter(None, cached)
        if source in ['simbad','all'] and len(identifiers) > 0:
             # If we have cached values, filter those out from the initial list
            if cached:
                current_app.logger.debug('Received %s identifiers. Using %s entries from cache.' % (id_num, len(cached)))
                identifiers = [id for id in identifiers if id not in [ci['simbad_id'] for ci in cached if ci]]
            if identifiers:
                # We have identifiers, not found in the cache
                result = get_simbad_objects(identifiers)
                if 'Error' in result:
                    # An error was returned!
                    current_app.logger.error('Failed to find objects for SIMBAD identifier query!')
                    return result
                else:
                    # We have results!
                    duration = time.time() - stime
                    current_app.logger.info('Found objects for SIMBAD identifiers in %s user seconds.' % duration)
                    # Before returning results, cache them
                    for item in result['data']:
                        current_app.cache.set(item['simbad_id'], item, timeout=current_app.config.get('OBJECTS_CACHE_TIMEOUT'))
                    if cached:
                        return cached + result.get('data',[])
                    else:
                        return result.get('data',[])
            elif cached:
                # We only had cached results
                return cached
            else:
                # This should never happen
                current_app.logger.error('No identifiers found, even though we had objects! Should never happen!')
                result = {
                    'Error': 'Failed to find identifiers for SIMBAD object query!',
                    'Error Info': 'No results found, where results were expected! Needs attention!'
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
