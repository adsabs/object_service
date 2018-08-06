import re
from flask import current_app
from requests.exceptions import ConnectTimeout, ReadTimeout
import timeout_decorator

def cleanup_object_name(object_name):
    # remove catalog prefix if present
    return re.sub('^(NAME|\*|S?V\*)\s+','',object_name)

def get_simbad_data(id_list, input_type):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    current_app.logger.info('TAP service used to get SIMBAD data: %s'%QUERY_URL)

    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }

    headers = {
        'User-Agent': 'ADS Object Service (Object Search)'
    }

    results = {}
    # Establish the SIMBAD query, based on the type of input
    if input_type == 'objects':
        results['data'] = {k:None for k in id_list}
        # For the object names query we want to have all variants returned, cache them, and select only those entries that match the input
        qfilter = " OR ".join(map(lambda a: "ident2.id=\'%s\'"%a, id_list))
        params['query'] = 'SELECT ident1.oidref, ident1.id, basic.main_id FROM ident AS ident1 JOIN ident AS ident2 ON ident1.oidref = ident2.oidref JOIN basic ON ident1.oidref = basic.oid WHERE %s;' % qfilter
    elif input_type == 'identifiers':
        # For the identifiers query we just want to have the canonical names returned
        qfilter = " OR ".join(map(lambda a: "oid=\'%s\'"%a,id_list))
        params['query'] = "SELECT oid, main_id, main_id FROM basic WHERE %s;" % qfilter
    else:
        return {"Error": "Unable to get results!", "Error Info": "Unknown input type specified!"}
    # Fire off the query
    # Get timeout for request from the config (use 1 second if not found)
    TIMEOUT = current_app.config.get('OBJECTS_SIMBAD_TIMEOUT',1)
    try:
        r = current_app.client.post(QUERY_URL, data=params, headers=headers, timeout=TIMEOUT)
    except (ConnectTimeout, ReadTimeout) as err:
        current_app.logger.info('SIMBAD request to %s timed out! Request took longer than %s second(s)'%(QUERY_URL, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD request timed out: {0}".format(err)}
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
            res = {cleanup_object_name(d[1]).upper(): {"canonical": cleanup_object_name(d[2]), "id": str(d[0])} for d in r.json()['data']}
            results['data'] = res.copy()
            results['data'].update({k.replace(' ',''):v for k,v in results['data'].items()})
        else:
            results['data'] = {str(d[0]): {"canonical": cleanup_object_name(d[2]), "id": str(d[0])} for d in r.json()['data']}
    except:
        results = {"Error": "Unable to get results!", "Error Info": "Bad data returned by SIMBAD"}
    return results

def simbad_position_query(RA, DEC, RADIUS):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    current_app.logger.info('TAP service used for position query: %s'%QUERY_URL)
    MAX_RADIUS = float(current_app.config.get('OBJECTS_SIMBAD_MAX_RADIUS'))
    MAX_NUMBER = current_app.config.get('OBJECTS_SIMBAD_MAX_NUMBER')
    RADIUS = min(float(RADIUS), MAX_RADIUS)
    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json',
        'maxrec' : MAX_NUMBER
    }
#    params['query'] = "SELECT DISTINCT oid \
#                       FROM basic \
#                       WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', %s, %s, %s)) = 1 \
#                       AND coo_bibcode IS NOT NULL \
#                       AND ra IS NOT NULL \
#                       AND dec IS NOT NULL;" % (RA, DEC, RADIUS)
    params['query'] = "SELECT TOP %s oid, \
                       DISTANCE( \
                       POINT('ICRS', ra, dec), \
                       POINT('ICRS', %s, %s)) AS dist \
                       FROM basic \
                       WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', %s, %s, %s)) = 1 \
                       AND coo_bibcode IS NOT NULL \
                       AND ra IS NOT NULL \
                       AND dec IS NOT NULL \
                       ORDER BY dist ASC;" % (MAX_NUMBER, RA, DEC, RA, DEC, RADIUS)
    headers = {
        'User-Agent': 'ADS Object Service (Cone Search)'
    }
    TIMEOUT = current_app.config.get('OBJECTS_SIMBAD_TIMEOUT',1)
    try:
        r = current_app.client.post(QUERY_URL, data=params, headers=headers, timeout=TIMEOUT)
    except (ConnectTimeout, ReadTimeout) as err:
        current_app.logger.info('SIMBAD request to %s timed out! Request took longer than %s second(s)'%(QUERY_URL, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD position query timed out: {0}".format(err)}
    except Exception, err:
        return {'Error': 'Unable to get results from %s!'%QUERY_URL, 'Error Info': 'SIMBAD position query blew up (%s)'%err}
    try:
        simbids = list(set([str(d[0]) for d in r.json()['data']]))
    except Exception, err:
        return {'Error': 'Unable to get results!', 'Error Info': 'Unable to retrieve SIMBAD identifiers from SIMBAD response (no "data" key)!'}
    return simbids
