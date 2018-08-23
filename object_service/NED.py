import re
import sys
import traceback
from flask import current_app
from flask import request
from client import client
import json
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError
import timeout_decorator
import datetime

def do_ned_object_lookup(url, oname):
    # Prepare the headers for the query
    payload = {
        "name": {"v": "{object}".format(object=oname)}
    }
    headers = {
        'User-Agent': 'ADS Object Service (Object Search)',
        'Content-type': 'application/json',
        'Accept': 'text/plain'
    }
    # Get timeout for request from the config (use 1 second if not found)
    TIMEOUT = current_app.config.get('OBJECTS_NED_TIMEOUT',1)
    try:
        r = current_app.client.post(url, data=json.dumps(payload), headers=headers)
    except (ConnectTimeout, ReadTimeout) as err:
        current_app.logger.info('NED request to %s timed out! Request took longer than %s second(s)'%(url, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "NED request timed out: {0}".format(str(err))}
    except Exception, err:
        current_app.logger.error("NED request to %s failed (%s)"%(url, err))
        return {"Error": "Unable to get results!", "Error Info": "NED request failed ({0})".format(err)}
    # Check if we got a 200 status code back
    if r.status_code != 200:
        current_app.logger.info('NED request to %s failed! Status code: %s'%(url, r.status_code))
        return {"Error": "Unable to get results!", "Error Info": "NED returned status %s" % r.status_code}
    # Return query results
    return r.json()

def get_ned_data(id_list, input_type):
    QUERY_URL = current_app.config.get('OBJECTS_NED_URL')
    current_app.logger.info('URL used to get NED data: %s'%QUERY_URL)

    results = {}
    results['data'] = {}
    results['skipped'] = []
    # Establish the NED query, based on the type of input
    if input_type in ['identifiers', 'objects']:
        for ident in id_list:
            # Since all spaces in the identifiers where replaced by underscores, we have to undo this
            odata = do_ned_object_lookup(QUERY_URL, ident.strip().replace('_',' '))
            if "Error" in odata:
                # NED query failed. This failure either means timeout or service problems
                # We return nothing for the entire query, with the proper error message
                return odata
            # Did we get a successful result back?
            statuscode = odata.get("StatusCode", 999)
            if statuscode == 100:
                # success
                resultcode = odata.get("ResultCode", 999)
                if resultcode == 3:
                    # Proper object name, known by NED
                    if input_type == 'identifiers':
                        results['data'][ident] = {'id': ident, 'canonical': odata['Preferred']['Name']}
                    else:
                        results['data'][ident] = {'id': odata['Preferred']['Name'].strip().replace(' ','_'), 'canonical': odata['Preferred']['Name']}
                elif resultcode in [0,1,2]:
                    # Unable to create usable results
                    results['skipped'].append(ident)
                    current_app.logger.info('NED returned result code {rcode} for object {object}'.format(rcode=resultcode, object=ident))
                    continue
                else:
                    # Unexpected result code!
                    results['skipped'].append(ident)
                    current_app.logger.info('Unexpected result code from NED! NED returned result code {rcode} for object {object}'.format(rcode=resultcode, object=ident))
                    continue
            else:
                # NED query was not successful
                results['skipped'].append(ident)
                current_app.logger.info('NED query failed! NED returned status code {rcode} for object {object}'.format(rcode=statuscode, object=ident))
                continue
    elif input_type == 'simple':
        # We just take the indexed NED identifier value and remove the underscore
        results = {}
        results['data'] = {}
        results['skipped'] = []
        for ident in id_list:
            results['data'][ident] = {'id': ident, 'canonical': ident.strip().replace('_',' ')}
    else:
        return {"Error": "Unable to get results!", "Error Info": "Unknown input type specified!"}

    return results

def ned_position_query(COORD, RADIUS):
    nedids = []
    RA, DEC = COORD.to_string('hmsdms').split()
    QUERY_URL = current_app.config.get('OBJECTS_NED_OBJSEARCH')
    TIMEOUT = current_app.config.get('OBJECTS_NED_TIMEOUT',1)
    MAX_RADIUS = float(current_app.config.get('OBJECTS_NED_MAX_RADIUS'))
    MAX_OBJECTS = int(current_app.config.get('OBJECTS_NED_MAX_NUMBER'))
    # set headers for query
    headers = {
        'User-Agent': 'ADS Object Service (Cone Search)',
        'Content-type': 'application/json',
        'Accept': 'text/plain'
    }
    # First set the default query parameters
    query_params = {
        'of':'ascii_bar',
        'search_type':'Near Position Search',
        'img_stamp':'NO',
        'list_limit':'5',
        'zv_breaker':'30000.0',
        'obj_sort':'Distance to search center',
        'out_equinox':'J2000.0',
        'out_csys':'Equatorial',
        'nmp_op':'ANY',
        'ot_include':'ANY',
        'z_unit':'z',
        'z_value1':'',
        'z_value2':'',
        'z_constraint':'Unconstrained',
        'corr_z':'1',
        'omegav':'0.73',
        'omegam':'0.27',
        'hconst':'73',
        'radius':'2',
        'in_equinox':'J2000.0',
        'in_csys':'Equatorial',
        }
    # Now add the position information
    query_params['lon'] = RA
    query_params['lat'] = DEC
    # NED wants radius in arcminutes
    query_params['radius'] = min(float(RADIUS.degree), MAX_RADIUS)
    # Do the query
    try:
        response = current_app.client.get(QUERY_URL, headers=headers, params=query_params)
    except (ConnectTimeout, ReadTimeout) as err:
        current_app.logger.info('NED cone search to %s timed out! Request took longer than %s second(s)'%(QUERY_URL, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "NED cone search timed out: {0}".format(str(err))}
    except Exception, err:
        current_app.logger.error("NED cone search to %s failed (%s)"%(QUERY_URL, err))
        return {"Error": "Unable to get results!", "Error Info": "NED cone search failed ({0})".format(err)}
    data = response.text.split('\n')
    nedids = [e.split('|')[1].strip().replace(' ','_') for e in data if e.find('|') > -1]
    try:
        nedids.remove('Object_Name')
    except:
        pass
    return nedids[:MAX_OBJECTS]

def get_NED_refcodes(obj_data):
    # NED endpoint to get data
    ned_url = current_app.config.get('OBJECTS_NED_URL')
    # Where we will store results
    result = {}
    # For ambiguous object names we will return lists of aliases
    result['ambiguous'] = []
    # Canonical object names returned from NED
    canonicals = []
    # Parameters for NED query
    payload = {}
    # Headers for request
    headers = {
        'User-Agent': 'ADS Object Service (Classic Object Search)',
        'Content-type': 'application/json',
        'Accept': 'text/plain'
    }
    # We're here, so the data submitted has an 'objects' attribute
    objects = obj_data.get('objects')
    # Let's just check to be sure that the list actually contains entries
    if len(objects) == 0:
        return {"Error": "Unable to get results!",
                "Error Info": "No object names provided"}
    # Now attempt to retrieve refcodes for each of the object names submitted
    for object_name in objects:
        # Payload per NED documentation: https://ned.ipac.caltech.edu/ui/Documents/ObjectLookup
        payload["name"] = {"v": "{0}".format(object_name)}
        # There is an entry, so now try to get the associated refcodes
        # Get timeout for request from the config (use 1 second if not found)
        TIMEOUT = current_app.config.get('OBJECTS_NED_TIMEOUT',1)
        # Query NED API to retrieve the canonical object names for the ones provided
        # (if known to NED)
        try:
            r = current_app.client.post(ned_url, data=json.dumps(payload), headers=headers)
        except (ConnectTimeout, ReadTimeout) as err:
            current_app.logger.info('NED request to %s timed out! Request took longer than %s second(s)'%(ned_url, TIMEOUT))
            return {"Error": "Unable to get results!", "Error Info": "NED request timed out: {0}".format(str(err))}
        except Exception, err:
            current_app.logger.error("NED request to %s failed (%s)"%(ned_url, err))
            return {"Error": "Unable to get results!", "Error Info": "NED request failed ({0})".format(err)}
        # Check if we got a 200 status code back
        if r.status_code != 200:
            current_app.logger.info('NED request to %s failed! Status code: %s'%(ned_url, r.status_code))
            return {"Error": "Unable to get results!", "Error Info": "NED returned status %s" % r.status_code}
        # We got a proper response back with data
        ned_data = r.json()
        # We are not interested in these cases: either not a valid object name, or a known one, but there
        # is no entry in the NED database
        if ned_data['ResultCode'] in [0,2]:
            # No or no unique result
            continue
        # This is still a useless case, but we want to send some data back for potential use. These are
        # "ambiguous" cases, where there are a number of potential candidates. This info is sent back.
        elif ned_data['ResultCode'] == 1:
            result['ambiguous'].append({object_name:ned_data['Interpreted']['Aliases']})
        else:
        # We have a canonical name. Store it in the appropriate list, so that we can query Solr with
        # it and retrieve bibcodes
            canonicals.append(ned_data['Preferred']['Name'].strip())
    # We retrieve bibcodes with one Solr query, using "nedid:" (we use canonical object names as identifiers,
    # with spaces replaced by underscores)
    obj_list = " OR ".join(map(lambda a: "nedid:%s" % a.replace(' ','_'), canonicals))
    q = '%s' % obj_list
    # Format the date range for filtering: year:YYYY-YYYY
    date_range = "{0}-{1}".format(obj_data.get('start_year', str(1800)), obj_data.get('end_year', str(datetime.datetime.now().year)))
    q += ' year:{0}'.format(date_range)
    # Did we get a bibstem filter?
    if obj_data.has_key('journals'):
        jrnl_list = " OR ".join(map(lambda a: "%s" % a, obj_data['journals']))
        q += ' bibstem:({0})'.format(jrnl_list)
    # Do we want refereed publications only?
    if obj_data.has_key('refereed_status'):
        q += ' property:{0}'.format(obj_data['refereed_status'])
    # Get the information from Solr
    headers = {'X-Forwarded-Authorization': request.headers.get('Authorization')}
    params = {'wt': 'json', 'q': q, 'fl': 'bibcode',
                      'rows': current_app.config.get('OBJECT_SOLR_MAX_HITS')}
    response = client().get(current_app.config.get('OBJECTS_SOLRQUERY_URL'), params=params,headers=headers)
    # See if our request was successful
    if response.status_code != 200:
        return {"Error": "Unable to get results!",
                        "Error Info": response.text,
                        "Status Code": response.status_code}
    # Retrieve the bibcodes from the data sent back. Throw an error if no bibcodes were found (should not happen)
    resp = response.json()
    try:
        result['data'] = [d['bibcode'] for d in resp['response']['docs']]
        return result
    except:
        return {"Error": "Unable to get results!", "Error Info": "No bibcodes returned for query: {0}".format(q)}



