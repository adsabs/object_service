import sys
import os
from flask_testing import TestCase
from flask import request
from flask import url_for, Flask
import unittest
import requests
import time
from object_service import app
import json
import httpretty
import timeout_decorator

class TestConfig(TestCase):

    '''Check if config has necessary entries'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    def test_config_values(self):
        '''Check if all required config variables are there'''
        required = ["OBJECTS_SIMBAD_TAP_URL",
                    "OBJECTS_CACHE_TIMEOUT",
                    "OBJECTS_DEFAULT_RADIUS",
                    "OBJECTS_SIMBAD_MAX_REC",
                    "OBJECTS_NED_URL",
                    ]
        missing = [x for x in required if x not in self.app.config.keys()]
        self.assertTrue(len(missing) == 0)
        # Check if API has an actual value
        #if os.path.exists("%s/local_config.py" % PROJECT_HOME):
        #    self.assertTrue(
        #        self.app.config.get('OBJECTS_API_TOKEN', None) != None)

class TestDataRetrieval(TestCase):

    '''Check if methods return expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    @httpretty.activate
    def test_get_simbad_identifiers(self):
        '''Test to see if retrieval of SIMBAD identifiers method behaves as expected'''
        from object_service.SIMBAD import get_simbad_data
        objects = ['Andromeda','LMC']
        mockdata = {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_simbad_data(objects, 'objects')
        expected = {'data': {u'LMC': {'id': '3133169', 'canonical': u'LMC'}, u'ANDROMEDA': {'id': '1575544', 'canonical': u'ANDROMEDA'}}}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_simbad_objects(self):
        '''Test to see if retrieval of SIMBAD objects method behaves as expected'''
        from object_service.SIMBAD import get_simbad_data
        identifiers = ["3133169", "1575544"]
        mockdata = {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_simbad_data(identifiers, 'identifiers')
        expected = {'data': {u'3133169': {'id': '3133169', 'canonical': u'LMC'}, u'1575544': {'id': '1575544', 'canonical': u'ANDROMEDA'}}}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_ned_objects(self):
        '''Test to see if retrieval of NED objects method behaves as expected'''
        from object_service.NED import get_ned_data
        identifiers = ["LMC"]
        mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology', 
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'}, 
                    u'ResultCode': 3, u'StatusCode': 100}
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_ned_data(identifiers, 'identifiers')
        expected = {'data': {u'LMC': {'id': 'LMC', 'canonical': u'Large Magellanic Cloud'}}}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_ned_objects_unknown_object(self):
        '''Test to see if retrieval of NED objects method behaves as expected'''
        from object_service.NED import get_ned_data
        identifiers = ["LMC"]
        mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
                    u'ResultCode': 0, u'StatusCode': 100}
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_ned_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!','Error Info': "No results were found for NED identifiers: ['LMC']"}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_ned_objects_unsuccessful(self):
        '''Test to see if retrieval of NED objects method behaves as expected'''
        from object_service.NED import get_ned_data
        identifiers = ["LMC"]
        mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
                    u'ResultCode': 0, u'StatusCode': 300}
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_ned_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!','Error Info': "No results were found for NED identifiers: ['LMC']"}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_ned_objects_unexpected_resultcode(self):
        '''Test to see if retrieval of NED objects method behaves as expected'''
        from object_service.NED import get_ned_data
        identifiers = ["LMC"]
        mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
                    u'ResultCode': 10, u'StatusCode': 100}
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_ned_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!','Error Info': "No results were found for NED identifiers: ['LMC']"}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_ned_objects_service_error(self):
        '''Test to see if retrieval of NED objects method behaves as expected'''
        from object_service.NED import get_ned_data
        identifiers = ["LMC"]
        mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
                    u'ResultCode': 10, u'StatusCode': 100}
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=500,
            body='%s'%json.dumps(mockdata))
        result = get_ned_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!','Error Info': "No results were found for NED identifiers: ['LMC']"}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_do_ned_query(self):
        '''Test to see if single NED object lookup behaves'''
        from object_service.NED import do_ned_object_lookup
        identifier = "LMC"
        mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
                    u'ResultCode': 3, u'StatusCode': 100}
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=500,
            body='%s'%json.dumps(mockdata))
        result = do_ned_object_lookup(QUERY_URL, identifier)
        expected = {"Error": "Unable to get results!", "Error Info": "NED returned status 500"}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_do_ned_query_readtimeout(self):
        '''Test to see if single NED throws proper exception at timeout'''
        from object_service.NED import do_ned_object_lookup
        from time import sleep

        def exceptionCallback(request, uri, headers):
            mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
                    u'ResultCode': 3, u'StatusCode': 100}
            sleep(2)
            return 200, headers, json.dumps(mockdata)

        self.app.config['OBJECTS_NED_TIMEOUT'] = 1
        QUERY_URL = "http://aaaa.org"
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = do_ned_object_lookup(QUERY_URL, "bar")

        expected = {'Error': 'Unable to get results!', 'Error Info': "NED request failed (HTTPConnectionPool(host='aaaa.org', port=80): Read timed out. (read timeout={0}))".format(self.app.config['OBJECTS_NED_TIMEOUT'])}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_get_simbad_objects_timeout(self):
        '''Test to see if retrieval of SIMBAD objects method behaves as expected'''
        from object_service.SIMBAD import get_simbad_data
        from time import sleep

        def exceptionCallback(request, uri, headers):
            mockdata = {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
            sleep(2)
            return 200, headers, json.dumps(mockdata)

        identifiers = ["3133169", "1575544"]
        self.app.config['OBJECTS_SIMBAD_TIMEOUT'] = 1
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_simbad_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!', 'Error Info': "NED request failed (HTTPConnectionPool(host='aaaa.org', port=80): Read timed out. (read timeout={0}))".format(self.app.config['OBJECTS_NED_TIMEOUT'])}
        expected = {"Error": "Unable to get results!", "Error Info": "SIMBAD request failed (not timeout)."}
        self.assertDictEqual(result, expected)

#    def test_do_simbad_query_readtimeout(self):
#        '''Test to see if SIMBAD throws proper exception at timeout'''
#        from NED import do_ned_object_lookup
#        from time import sleep
#
#        def exceptionCallback(request, uri, headers):
#            mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
#                    u'Preferred': {u'Name': u'Large Magellanic Cloud'},
#                    u'ResultCode': 3, u'StatusCode': 100}
#            sleep(2)
#            return 200, headers, json.dumps(mockdata)
#
#        self.app.config['OBJECTS_NED_TIMEOUT'] = 1
#        QUERY_URL = "http://aaaa.org"
#        httpretty.register_uri(
#            httpretty.POST, QUERY_URL,
#            body=exceptionCallback)
#        result = do_ned_object_lookup(QUERY_URL, "bar")
#
#        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED connection error.'}
#        expected = {'Error': 'Unable to get results!', 'Error Info': "NED request failed (HTTPConnectionPool(host='aaaa.org', port=80): Read timed out. (read timeout={0}))".format(self.app.config['OBJECTS_NED_TIMEOUT'])}
#        self.assertEqual(result, expected)

    @httpretty.activate
    def test_do_cone_search(self):
        '''Test to see if SIMBAD cone search method behaves as expected'''
        from object_service.SIMBAD import parse_position_string
        from object_service.SIMBAD import do_position_query
        pstring = "80.89416667 -69.75611111:0.166666"
        mockdata = {"data":[["2003A&A...405..111G"],["2011AcA....61..103G"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # First parse the position string and see we if get the expected results back
        RA, DEC, radius = parse_position_string(pstring)
        self.assertEqual([RA, DEC, radius], [80.89416667,-69.75611111,'0.166666'])
        # Next query with this positional information
        result = do_position_query(RA, DEC, radius)
        expected = {'data': [u'2011AcA....61..103G', u'2003A&A...405..111G']}
        self.assertEqual(result, expected)

@timeout_decorator.timeout(2)
def timeout(s):
    time.sleep(s)
    return s

class TestTimeOut(TestCase):

    '''Check if the timeout decorator works as expected'''

    def create_app(self):
        '''Create the wsgi application'''
        _app = app.create_app()
        return _app

    def test_timeout(self):
        '''Test if timeout decorator works properly'''
        try:
            res = timeout(1)
        except timeout_decorator.timeout_decorator.TimeoutError:
            res = 'timeout'
        self.assertEqual(res, 1)
        try:
            res = timeout(3)
        except timeout_decorator.timeout_decorator.TimeoutError:
            res = 'timeout'
        self.assertEqual(res, 'timeout')

class TestQueryStringParsing(TestCase):

    '''Check if the query parser works as expected'''

    def create_app(self):
        '''Create the wsgi application'''
        _app = app.create_app()
        return _app

    def test_query_parsing(self):
        '''Test parsing of query strings'''
        from object_service.utils import get_objects_from_query_string as parse
        test_cases = {
            'object:Bla':['Bla'],
            'object:"Small Magellanic Cloud"':['Small Magellanic Cloud'],
            'object:"Bla OR Something"':['Bla', 'Something'],
            'object:(("*Foo +Ba" OR SMC) AND Andromeda)':['*Foo +Ba', 'SMC', 'Andromeda'],
            'object:((("*Foo +Ba" OR SMC) AND Andromeda) OR "Something Else")':['*Foo +Ba', 'SMC', 'Andromeda', 'Something Else'],
            'mod1:bar object:Bla mod2:foo':['Bla'],
            'mod1:bar object:"Bla OR Something" mod2:foo':['Bla', 'Something'],
            'bibstem:"A&A" object:(("*Foo +Ba" OR SMC) AND Andromeda) year:2015':['*Foo +Ba', 'SMC', 'Andromeda'],
            'bibstem:A&A object:(("*Foo +Ba" OR SMC) AND Andromeda) year:2015':['*Foo +Ba', 'SMC', 'Andromeda'],
            'object:Foo object:Bar':['Foo', 'Bar'],
            'object:Foo OR object:Bar':['Foo', 'Bar'],
            'object:("Foo Bar" OR Something)':['Foo Bar', 'Something'],
            'mod1:bar object:"Bla OR Something" mod2:foo object:"X OR Y"':['Bla', 'Something', 'X', 'Y']
            }

        for qstring, expected in test_cases.items():
            self.assertEqual(parse(qstring), expected)

if __name__ == '__main__':
    unittest.main()
