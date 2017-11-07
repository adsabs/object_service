import re
import sys
import traceback
from flask import current_app
import requests
import json
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError
import timeout_decorator

def do_ned_object_lookup(url, oname):
    # Prepare the headers for the query
    payload = {
        "name": {"v": "{object}".format(object=oname)}
    }
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    # Get timeout for request from the config (use 1 second if not found)
    TIMEOUT = current_app.config.get('OBJECTS_NED_TIMEOUT',1)
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=TIMEOUT)
    except (ConnectTimeout, ReadTimeout) as err:
        print "XXXXXXXX"
        current_app.logger.info('NED request to %s timed out! Request took longer than %s second(s)'%(url, TIMEOUT))
        return {"Error": "Unable to get results!", "Error Info": "NED request timed out: {0}".format(str(err))}
    except Exception, err:
        print "YYYYYYY"
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
            odata = do_ned_object_lookup(QUERY_URL, ident)
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
    else:
        return {"Error": "Unable to get results!", "Error Info": "Unknown input type specified!"}

    if len(results['data']) > 0:
        return results
    else:
        return {"Error": "Unable to get results!", "Error Info": "No results were found for NED identifiers: {0}".format(id_list)}
