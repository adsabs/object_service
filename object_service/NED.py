import re
import sys
import traceback
from flask import current_app
import requests
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
        r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=TIMEOUT)
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

    params = {
        'request' : 'doQuery',
        'lang' : 'adql',
        'format' : 'json'
    }
    results = {}
    results['data'] = {}
    # Establish the NED query, based on the type of input
    if input_type == 'identifiers':
        for ident in id_list:
            # Since all spaces in the identifiers where replaced by underscores, we have to undo this
            odata = do_ned_object_lookup(QUERY_URL, ident.replace('_',' '))
            if "Error" in odata:
                # NED query failed, no need to proceed with this identifier
                continue
            # Did we get a successful result back?
            statuscode = odata.get("StatusCode", 999)
            if statuscode == 100:
                # success
                resultcode = odata.get("ResultCode", 999)
                if resultcode == 3:
                    # Proper object name, known by NED
                    results['data'][ident] = {'id': ident, 'canonical': odata['Preferred']['Name']}
                elif resultcode in [0,1,2]:
                    # Unable to create usable results
                    current_app.logger.info('NED returned result code {rcode} for object {object}'.format(rcode=resultcode, object=ident))
                    continue
                else:
                    # Unexpected result code!
                    current_app.logger.info('Unexpected result code from NED! NED returned result code {rcode} for object {object}'.format(rcode=resultcode, object=ident))
                    continue
            else:
                # NED query was not successful
                current_app.logger.info('NED query failed! NED returned status code {rcode} for object {object}'.format(rcode=statuscode, object=ident))
                continue
    elif input_type == 'simple':
        # We just take the indexed NED identifier value and remove the underscore
        results = {}
        results['data'] = {}
        for ident in id_list:
            results['data'][ident] = {'id': ident, 'canonical': ident.replace('_',' ')}
    else:
        return {"Error": "Unable to get results!", "Error Info": "Unknown input type specified!"}

    if len(results['data']) > 0:
        return results
    else:
        return {"Error": "Unable to get results!", "Error Info": "No results were found for NED identifiers: {0}".format(id_list)}

def get_NED_refcodes(obj_data):
    # We use the Ned component of astroquery to interact with NED
    from astroquery.ned import Ned
    # Where we will store results
    result = {}
    result['data'] = []
    # We're here, so the data submitted has an 'objects' attribute
    objects = obj_data.get('objects')
    # Let's just check to be sure that the list actually contains entries
    if len(objects) == 0:
        return {"Error": "Unable to get results!",
                "Error Info": "No object names provided"}
    # Now attempt to retrieve refcodes for each of the object names submitted
    for object_name in objects:
        # To check if there is an entry in the NED database, try to get the canonical object name
        try:
            object_check = Ned.query_object(object_name)
            NED_name = object_check['Object Name']
        except:
            continue
        # There is an entry, so now try to get the associated refcodes
        result_table = Ned.get_table(object_name, 
                               table='references', 
                               from_year=obj_data.get('start_year', 1800),
                               to_year=obj_data.get('end_year', datetime.datetime.now().year))
        # If there are no refcode entries, we just skip to the next object (if there's any left)
        try:
            result['data'] += [r['Refcode'] for r in result_table]
        except:
            continue

    return result
        
   
