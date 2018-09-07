import re
from flask import current_app
from requests.exceptions import ConnectTimeout, ReadTimeout
import timeout_decorator
import json

def do_tap_query(query, search_type, maxrec):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    current_app.logger.info('TAP service used to get SIMBAD data: %s'%QUERY_URL)

    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json',
        'query' : query
    }
    
    if int(maxrec) > 0:
        params['maxrec'] = int(maxrec)

    headers = {
        'User-Agent': 'ADS Object Service ({0})'.format(search_type)
    }
    
    TIMEOUT = current_app.config.get('OBJECTS_SIMBAD_TIMEOUT',1)

    try:
        r = current_app.client.post(QUERY_URL, data=params, headers=headers, timeout=TIMEOUT)
    except (ConnectTimeout, ReadTimeout) as err:
        current_app.logger.info('SIMBAD request to %s timed out! Request took longer than %s second(s)'%(QUERY_URL, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD request timed out: {0}".format(err)}
    except Exception, err:
        current_app.logger.error("SIMBAD request to %s failed (%s)"%(QUERY_URL, err))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD request failed (not timeout): %s"%err}
    # Report if the SIMBAD server did not like our query
    if r.status_code != 200:
        current_app.logger.info('SIMBAD request to %s failed! Status code: %s'%(QUERY_URL, r.status_code))
        return {"Error": "Unable to get results!", "Error Info": "SIMBAD returned status %s" % r.status_code}
    data = r.json()
    return data
    
def verify_tap_service():
    # The default TAP service (CfA) is sometimes down, in which
    # case we temporarily want to use the CDS mirror
    # The ADQL query used here should always return results
    tap_url = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    q = 'SELECT TOP 1 * FROM basic;'
    verify = do_tap_query(q, 'TAP Service Verification', 0)
    if verify.get('Error', None):
        # If the test query failed, we return the CDS TAP service URL
        # Failure can happen for the following reasons:
        # 1. The request threw an exception
        # 2. The request was successful but returned a non-200 HTTP status
        current_app.logger.info('CfA TAP service unavailable. Switching to CDS service. Test query diagnostics: {0}'.format(verify.get('Error Info')))
        tap_url = current_app.config.get('OBJECTS_SIMBAD_TAP_URL_CDS')
    else:
        # The TAP service returned results, but we still need to check
        # The 'data' attribute for the test query cannot be empty
        if not verify.get('data', True):
            current_app.logger.info('Test query returned empty data. Switching to CDS service')
            tap_url = current_app.config.get('OBJECTS_SIMBAD_TAP_URL_CDS')
        
    return tap_url
    
def cleanup_object_name(object_name):
    # remove catalog prefix if present
    return re.sub('^(NAME|\*|S?V\*)\s+','',object_name)

def get_simbad_data(id_list, input_type):
    results = {}
    # Establish the SIMBAD query, based on the type of input
    if input_type == 'objects':
        results['data'] = {k:None for k in id_list}
        # For the object names query we want to have all variants returned, cache them, and select only those entries that match the input
        qfilter = " OR ".join(map(lambda a: "ident2.id=\'%s\'"%a, id_list))
        q = 'SELECT ident1.oidref, ident1.id, basic.main_id FROM ident AS ident1 JOIN ident AS ident2 ON ident1.oidref = ident2.oidref JOIN basic ON ident1.oidref = basic.oid WHERE %s;' % qfilter
    elif input_type == 'identifiers':
        # For the identifiers query we just want to have the canonical names returned
        qfilter = " OR ".join(map(lambda a: "oid=\'%s\'"%a,id_list))
        q = "SELECT oid, main_id, main_id FROM basic WHERE %s;" % qfilter
    else:
        return {"Error": "Unable to get results!", "Error Info": "Unknown input type specified!"}
    # Fire off the query
    r = do_tap_query(q, 'Object Search', 0)
    if r.get('Error', None):
        return r
    # Contruct the results
    # The "data" attribute of the JSON returned consists of tuples with the following entries
    # 0. SIMBAD identifier
    # 1. Object name
    # 2. Canonical object name
    try:
        if input_type == 'objects':
            res = {cleanup_object_name(d[1]).upper(): {"canonical": cleanup_object_name(d[2]), "id": str(d[0])} for d in r['data']}
            results['data'] = res.copy()
            results['data'].update({k.replace(' ',''):v for k,v in results['data'].items()})
        else:
            results['data'] = {str(d[0]): {"canonical": cleanup_object_name(d[2]), "id": str(d[0])} for d in r['data']}
    except:
        results = {"Error": "Unable to get results!", "Error Info": "Bad data returned by SIMBAD"}
    return results

def simbad_position_query(COORD, RADIUS):
    RA, DEC = COORD.to_string('decimal').split()
    MAX_RADIUS = float(current_app.config.get('OBJECTS_SIMBAD_MAX_RADIUS'))
    MAX_NUMBER = current_app.config.get('OBJECTS_SIMBAD_MAX_NUMBER')
    RADIUS = min(float(RADIUS.degree), MAX_RADIUS)
    
    q = "SELECT TOP %s oid, \
                       DISTANCE( \
                       POINT('ICRS', ra, dec), \
                       POINT('ICRS', %s, %s)) AS dist \
                       FROM basic \
                       WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', %s, %s, %s)) = 1 \
                       AND coo_bibcode IS NOT NULL \
                       AND ra IS NOT NULL \
                       AND dec IS NOT NULL \
                       ORDER BY dist ASC;" % (MAX_NUMBER, RA, DEC, RA, DEC, RADIUS)

    r = do_tap_query(q, 'Cone Search', MAX_NUMBER)
    if r.get('Error', None):
        return r
    try:
        simbids = list(set([str(d[0]) for d in r['data']]))
    except Exception, err:
        return {'Error': 'Unable to get results!', 'Error Info': 'Unable to retrieve SIMBAD identifiers from SIMBAD response (no "data" key)!'}
    return simbids
