import sys
import os
from flask_testing import TestCase
from flask import request
from flask import url_for, Flask
import unittest
import requests
from requests.exceptions import ReadTimeout
import time
from object_service import app
import json
import httpretty
import datetime

now = datetime.datetime.now()


class TestDataRetrieval(TestCase):

    '''Check if methods return expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

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
        expected = {'skipped': [], 'data': {u'LMC': {'id': 'LMC', 'canonical': u'Large Magellanic Cloud'}}}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_ned_objects_unknown_object(self):
        '''Test to see if retrieval of NED objects method behaves as expected'''
        from object_service.NED import get_ned_data
        identifiers = map(str, range(4))
        def get_mock_data(v, status_code=100):
            mockdata = {u'NameResolver': u'NED-Egret', 
                        u'Copyright': u'(C) 2017 California Institute of Technology',
                        u'Preferred': {u'Name': u'FOO BAR'}}
            try:
                mockdata['ResultCode'] = int(v)
            except:
                mockdata['ResultCode'] = 0
            mockdata['StatusCode'] = status_code
            return mockdata

        def request_callback(request, uri, headers):
            data = request.body
            v = json.loads(request.body)["name"]["v"]
            try:
                return (200, headers, json.dumps(get_mock_data(v)))
            except:
                return (200, headers, json.dumps(get_mock_data('0')))

        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=request_callback)

        result = get_ned_data(identifiers, 'identifiers')
        expected = {'data': {'3': {'canonical': u'FOO BAR', 'id': '3'}},
                    'skipped': ['0','1','2']} 
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
        expected = {'data': {}, 'skipped': ['LMC']}
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
        expected = {'data': {}, 'skipped': ['LMC']}
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
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED returned status 500'}
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
    def test_do_ned_lookup_readtimeout(self):
        '''Test to see if single NED object lookup throws proper exception at timeout'''
        from object_service.NED import do_ned_object_lookup

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = "http://aaaa.org"
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = do_ned_object_lookup(QUERY_URL, "bar")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request timed out: Connection timed out.'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_lookup_readtimeout(self):
        '''Test to see if single NED object lookup throws proper exception at timeout'''
        from object_service.NED import do_ned_object_lookup

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = "http://aaaa.org"
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = do_ned_object_lookup(QUERY_URL, "bar")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request timed out: Connection timed out.'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_refcode_query_readtimeout(self):
        '''Test to see if single NED refcode query throws proper exception at timeout'''
        from object_service.NED import get_NED_refcodes

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        obj_data = {'objects':['FOO_BAR']}
        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_NED_refcodes(obj_data)
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request timed out: Connection timed out.'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_refcode_query_exception(self):
        '''Test to see if single NED refcode query throws proper exception at non-timeout exception'''
        from object_service.NED import get_NED_refcodes

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')

        obj_data = {'objects':['FOO_BAR']}
        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_NED_refcodes(obj_data)
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request failed (Oops! Something went boink!)'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_refcode_query_non200(self):
        '''Test to see if single NED refcode query throws proper exception at non-timeout exception'''
        from object_service.NED import get_NED_refcodes

        obj_data = {'objects':['FOO_BAR']}
        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            status=500,
            body={})
        result = get_NED_refcodes(obj_data)
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED returned status 500'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_query_objects_readtimeout(self):
        '''Test to see if single NED query throws proper exception at timeout'''
        from object_service.NED import get_ned_data

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        identifiers = ['FOO_BAR']
        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_ned_data(identifiers, "objects")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request timed out: Connection timed out.'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_lookup_exception(self):
        '''Test to see if single NED lookupthrows proper exception at timeout'''
        from object_service.NED import do_ned_object_lookup

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')

        self.app.config['OBJECTS_NED_TIMEOUT'] = 0.1
        QUERY_URL = "http://aaaa.org"
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = do_ned_object_lookup(QUERY_URL, "bar")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request failed (Oops! Something went boink!)'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_query_identifiers_exception(self):
        '''Test to see if single NED query hrows proper exception at timeout'''
        from object_service.NED import get_ned_data

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')
 
        identifiers = ['FOO_BAR']
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_ned_data(identifiers, "identifiers")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request failed (Oops! Something went boink!)'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_ned_query_objects_exception(self):
        '''Test to see if single NED query hrows proper exception at timeout'''
        from object_service.NED import get_ned_data

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')

        identifiers = ['FOO_BAR']
        QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_ned_data(identifiers, "objects")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request failed (Oops! Something went boink!)'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_malformed_solr_response(self):
        '''Test to see if single NED object lookup behaves'''
        from object_service.NED import get_NED_refcodes
        # Inpiut data
        obj_data = {'objects':['FOO_BAR'], 'journals':['ApJ','A&A'], 'refereed_status':'refereed'}
        # Solr mock
        solr_mockdata = {'foo':'bar'}
        SOLR_URL = self.app.config.get('OBJECTS_SOLRQUERY_URL')
        httpretty.register_uri(
            httpretty.GET, SOLR_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(solr_mockdata))
        # NED mock
        ned_mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'FOO BAR'},
                    u'ResultCode': 3, u'StatusCode': 100}
        NED_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, NED_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(ned_mockdata))
        # Now run the query
        result = get_NED_refcodes(obj_data)
        expected = {"Error": "Unable to get results!", 
                    "Error Info": "No bibcodes returned for query: nedid:FOO_BAR year:1800-%s bibstem:(ApJ OR A&A) property:refereed"%now.year}
        self.assertEqual(result, expected) 
    
    @httpretty.activate
    def test_error_solr_response(self):
        '''Test to see if single NED object lookup behaves'''
        from object_service.NED import get_NED_refcodes
        # Inpiut data
        obj_data = {'objects':['FOO_BAR']}
        # Solr mock
        solr_mockdata = {'foo':'bar'}
        SOLR_URL = self.app.config.get('OBJECTS_SOLRQUERY_URL')
        httpretty.register_uri(
            httpretty.GET, SOLR_URL,
            content_type='application/json',
            status=500,
            body='we have a problem')
        # NED mock
        ned_mockdata = {u'NameResolver': u'NED-Egret', u'Copyright': u'(C) 2017 California Institute of Technology',
                    u'Preferred': {u'Name': u'FOO BAR'},
                    u'ResultCode': 3, u'StatusCode': 100}
        NED_URL = self.app.config.get('OBJECTS_NED_URL')
        httpretty.register_uri(
            httpretty.POST, NED_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(ned_mockdata))
        # Now run the query
        result = get_NED_refcodes(obj_data)
        expected = {"Error": "Unable to get results!", 
                    "Error Info": "we have a problem",
                    "Status Code": 500}
        self.assertEqual(result, expected) 

if __name__ == '__main__':
    unittest.main()
