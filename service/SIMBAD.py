from flask import current_app
import requests
import timeout_decorator

def translate_object_names(object_list):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }
    filter = " OR ".join(map(lambda a: "id=\'%s\'"%a,object_list))
    params['query'] = "SELECT id FROM ident WHERE %s" % filter
    r = requests.post(QUERY_URL, data=params)
    try:
        results = [d[0] for d in r.json()['data']]
    except:
        results = []
    return results

def get_simbad_identifiers(object_list):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }
    filter = " OR ".join(map(lambda a: "id=\'%s\'"%a,object_list))
    params['query'] = "SELECT id,oidref FROM ident WHERE %s" % filter
    r = requests.post(QUERY_URL, data=params)
    try:
        results = {'data':[{'object':d[0], 'simbad_id': str(d[1])} for d in r.json()['data']]}
    except Exception, err:
        results = {'Error': 'Unable to get results!', 'Error Info': err}
    return results

def get_simbad_objects(id_list):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }
    filter = " OR ".join(map(lambda a: "oidref=\'%s\'"%a,id_list))
    params['query'] = "SELECT DISTINCT basic.OID,main_id FROM basic JOIN ident ON oidref = oid WHERE %s" % filter
    r = requests.post(QUERY_URL, data=params)
    try:
        results = {'data':[{'object':d[1], 'simbad_id': str(d[0])} for d in r.json()['data']]}
    except Exception, err:
        results = {'Error': 'Unable to get results!', 'Error Info': err}
    return results

@timeout_decorator.timeout(5)
def do_position_query(RA, DEC, RADIUS):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }
    params['query'] = "SELECT coo_bibcode \
                       FROM basic \
                       WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', %s, %s, %s)) = 1 \
                       AND coo_bibcode IS NOT NULL \
                       AND ra IS NOT NULL \
                       AND dec IS NOT NULL;" % (RA, DEC, RADIUS)
    try:
        r = requests.post(QUERY_URL, data=params)
    except Exception, err:
        results = {'Error': 'Unable to get results!', 'Error Info': 'SIMBAD query blew up (%s)'%err}
    try:
        bibcodes = list(set([d[0] for d in r.json()['data']]))
    except Exception, err:
        return {'Error': 'Unable to get results!', 'Error Info': err}
    return {'data': bibcodes}
