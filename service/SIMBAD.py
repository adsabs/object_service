import re
from flask import current_app
import requests
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
    ofilter = " OR ".join(map(lambda a: "id=\'%s\'"%a,object_list))
    params['query'] = "SELECT id,oidref FROM ident WHERE %s" % ofilter
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
    if r.status_code != 200:
        return {'Error': 'Unable to get results!', 'Error Info': 'SIMBAD returned status %s' % r.status_code}
    try:
        results = {'data':[{'object':d[1], 'simbad_id': str(d[0])} for d in r.json()['data']]}
    except:
        results = {'Error': 'Unable to get results!', 'Error Info': 'Bad data returned by SIMBAD'}
    return results

@timeout_decorator.timeout(5)
def do_position_query(RA, DEC, RADIUS):
    QUERY_URL = current_app.config.get('OBJECTS_SIMBAD_TAP_URL')
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
        results = {'Error': 'Unable to get results!', 'Error Info': 'SIMBAD query blew up (%s)'%err}
    try:
        bibcodes = list(set([d[0] for d in r.json()['data']]))
    except Exception, err:
        return {'Error': 'Unable to get results!', 'Error Info': err}
    return {'data': bibcodes}
