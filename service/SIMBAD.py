import re
from flask import current_app
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
import timeout_decorator
from astropy import units as u
from astropy.coordinates import SkyCoord

class IncorrectPositionFormatError(Exception):
    pass

def parse_position_string(pstring):
    pstring = re.sub('\ \ +',' ',re.sub('[dhms]',' ',pstring).strip()).replace(' :',':')
    # Split position string up in position and radius (if specified, otherwise default radius)
    if pstring.find(':') > -1:
        position, radius = pstring.split(':')
        radius = radius.strip()
        position = position.strip()
        # If the radius is not decimal, convert it to decimal
        if radius.count(' ') > 0:
            if radius.count(' ') > 2:
                current_app.logger.warning('Incorrectly formatted radius (%s). Setting default radius!' % radius)
                search_radius = current_app.config.get('OBJECTS_DEFAULT_RADIUS')
            else:
                # Assumption: 1 digit means 'seconds', 2 means 'minutes' and 'seconds'
                # Under this assumption always pad to get 3 digits and convert to decimal
                conversion = [1,0.016666666666666666,0.0002777777777777778]
                try:
                    search_radius = sum([a*b for a,b in zip(map(int,(2-radius.count(' '))*[0] + radius.split()),conversion)])
                except:
                    search_radius = current_app.config.get('OBJECTS_DEFAULT_RADIUS')
        else:
            search_radius = radius
    else:
        position = pstring.strip()
        search_radius = current_app.config.get('OBJECTS_DEFAULT_RADIUS')
    # Now turn the position into a decimal RA and DEC
    # If we have ony one space in the position string, we are done
    if position.count(' ') == 1:
        RA, DEC = map(float, position.split())
        if str(DEC)[0] not in ['+','-']:
            raise IncorrectPositionFormatError
    else:
        # Before converting, a quick sanity check on the position string
        # There has to be a '+' or '-' in the string (declination)
        # The string is assumed to be of the form "hh mm ss [+-]dd mm ss"
        # so the 4th entry has to start with either + or -
        if position.split()[3][0] not in ['+','-']:
            raise IncorrectPositionFormatError
        # We need to convert to decimal degrees
        try:
            c = SkyCoord(position, unit=(u.hourangle, u.deg))
            RA, DEC = c.to_string('decimal').split()
        except:
            raise IncorrectPositionFormatError
    return RA, DEC, radius

def get_simbad_data(id_list, input_type):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    current_app.logger.info('TAP service used to get SIMBAD data: %s'%QUERY_URL)

    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }
    results = {}
    # Establish the SIMBAD query, based on the type of input
    if input_type == 'objects':
        results['data'] = {k:None for k in id_list}
        # For the object names query we want to have all variants returned, cache them, and select only those entries that match the input
        qfilter = " OR ".join(map(lambda a: "ident2.id=\'%s\'"%a.upper(),id_list))
        params['query'] = 'SELECT ident1.oidref, ident1.id, basic.main_id FROM ident AS ident1 JOIN ident AS ident2 ON ident1.oidref = ident2.oidref JOIN basic ON ident1.oidref = basic.oid WHERE %s;' % qfilter
    elif input_type == 'identifiers':
        # For the identifiers query we just want to have the canonical names returned
        qfilter = " OR ".join(map(lambda a: "oid=\'%s\'"%a,id_list))
        params['query'] = "SELECT oid, main_id, main_id FROM basic WHERE %s;" % qfilter
    elif input_type == 'facets':
        # For the facets query we expect a list of hierarchical facets of the form
        #   ["<level>/<object type>/<object id>", ...]
        # which will get translated into
        #   ["<level>/<object type>/<canonical object name>", ...]
        # First deal with potential top level facets
        top_level = [f for f in id_list if f.count('/') < 2]
        # Assure we only have the next level facets
        id_list = [f for f in id_list if f.count('/') == 2]
        # If we only have top level facets, we can already return
        if len(top_level) > 0 and len(id_list) == 0:
            results['data'] = {f:f for f in top_level}
            return results
        idmap = {oid:{'level':level, 'type':otype} for (level,otype,oid) in  [x.split('/') for x in id_list]}
        # Get data using the same recipe as the 'identifiers' case
        qfilter = " OR ".join(map(lambda a: "oid=\'%s\'"%a,idmap.keys()))
        params['query'] = "SELECT oid, main_id, main_id FROM basic WHERE %s;" % qfilter
    else:
        return {"Error": "Unable to get results!", "Error Info": "Unknown input type specified!"}
    # Fire off the query
    # Get timeout for request from the config (use 1 second if not found)
    TIMEOUT = current_app.config.get('OBJECTS_SIMBAD_TIMEOUT',1)
    try:
        r = requests.post(QUERY_URL, data=params, timeout=TIMEOUT)
    except ConnectTimeout, ReadTimeout:
        current_app.logger.info('SIMBAD request to %s timed out! Request took longer than %s second(s)'%(QUERY_URL, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD request timed out."}
    except Exception, err:
        current_app.logger.error("SIMBAD request to %s failed (%s)"%(QUERY_URL, err))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD request failed (not timeout)."}
    # Report if the SIMBAD server did not like our query
    if r.status_code != 200:
        current_app.logger.info('SIMBAD request to %s failed! Status code: %s'%(QUERY_URL, r.status_code))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD returned status %s" % r.status_code}
    # Contruct the results
    # The "data" attribute of the JSON returned consists of tuples with the following entries
    # 0. SIMBAD identifier
    # 1. Object name
    # 2. Canonical object name
    try:
        if input_type == 'objects':
            res = {d[1].replace('NAME ',''): {"canonical": d[2].replace('NAME ',''), "id": str(d[0])} for d in r.json()['data']}
            results['data'] = res.copy()
            results['data'].update({k.replace(' ',''):v for k,v in results['data'].items()})
        elif input_type == 'identifiers':
            results['data'] = {str(d[0]): {"canonical": d[2].replace('NAME ',''), "id": str(d[0])} for d in r.json()['data']}
        else:
            results['data'] = {"%s/%s/%s" % (idmap.get(str(d[0]))['level'], idmap.get(str(d[0]))['type'], d[0]):"%s/%s/%s" % (idmap.get(str(d[0]))['level'], idmap.get(str(d[0]))['type'], d[2].replace('NAME ','')) for d in r.json()['data']}
            if len(top_level) > 0:
                top_dict = {f:f for f in top_level}
                res = top_dict.copy()
                res.update(results.get('data',{}))
                results['data'] = res
    except:
        results = {"Error": "Unable to get results!", "Error Info": "Bad data returned by SIMBAD"}
    return results

@timeout_decorator.timeout(5)
def do_position_query(RA, DEC, RADIUS):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    current_app.logger.info('TAP service used for position query: %s'%QUERY_URL)
    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json',
        'maxrec' : current_app.config.get('OBJECTS_SIMBAD_MAX_REC')
    }
    params['query'] = "SELECT DISTINCT coo_bibcode \
                       FROM basic \
                       WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', %s, %s, %s)) = 1 \
                       AND coo_bibcode IS NOT NULL \
                       AND ra IS NOT NULL \
                       AND dec IS NOT NULL;" % (RA, DEC, RADIUS)
    try:
        r = requests.post(QUERY_URL, data=params)
    except Exception, err:
        results = {'Error': 'Unable to get results from %s!'%QUERY_URL, 'Error Info': 'SIMBAD query blew up (%s)'%err}
    try:
        bibcodes = list(set([d[0] for d in r.json()['data']]))
    except Exception, err:
        return {'Error': 'Unable to get results!', 'Error Info': err}
    return {'data': bibcodes}
