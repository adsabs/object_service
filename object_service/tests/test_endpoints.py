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
import mock
from requests.exceptions import ConnectTimeout, ReadTimeout

class TestExpectedResults(TestCase):

    '''Check if the service returns expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    @httpretty.activate
    def test_object_search_200(self):
        '''Test to see if calling the object search endpoint
           works for valid data'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        # We will be doing a POST request with a set of identifiers
        identifiers = ["3133169", "1575544"]
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # Do the POST request
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({'identifiers': identifiers}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {u'3133169': {u'id': '3133169', u'canonical': u'LMC'}, u'1575544': {u'id': '1575544', u'canonical': u'ANDROMEDA'}}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_object_search_500(self):
        '''Test to see if a 500 from SIMBAD is processed correctly'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        identifiers = ["3133169", "1575544"]
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        def request_callback(request, uri, headers):
            data = request.body
            status = 200
            if data.find('TOP') == -1:
                status = 500
            return (status, headers, '%s'%json.dumps(mockdata))
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=request_callback)
        # Do the POST request
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({'identifiers': identifiers}))
        # See if we received the expected results
        self.assertEqual(r.json['Error'], 'Unable to get results!')
        self.assertEqual(r.json['Error Info'], 'SIMBAD returned status 500')

    @httpretty.activate
    def test_object_search_bad_data(self):
        '''Test to see if bad data from SIMBAD is processed correctly'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        identifiers = ["3133169", "1575544"]
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        def request_callback(request, uri, headers):
            data = request.body
            status = 200
            if data.find('TOP') == -1:
                return (status, headers, '{}')
            else:
                return (status, headers, '%s'%json.dumps(mockdata))
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=request_callback)
        # Do the POST request
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({'identifiers': identifiers}))
        # See if we received the expected results
        self.assertEqual(r.json['Error'], 'Unable to get results!')
        self.assertEqual(r.json['Error Info'], 'Bad data returned by SIMBAD')

    @httpretty.activate
    def test_object_search_empty_list(self):
        '''Test to see if an empty id list is processed correctly'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        def request_callback(request, uri, headers):
            data = request.body
            status = 200
            if data.find('TOP') == -1:
                return (status, headers, '{}')
            else:
                return (status, headers, '%s'%json.dumps(mockdata))
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=request_callback)
        # Do the POST request
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({}))
        # First we omit the 'identifiers' attribute in the input
        # See if we received the expected results
        self.assertEqual(r.json['Error'], 'Unable to get results!')
        self.assertEqual(r.json['Error Info'], 'No identifiers/objects found in POST body')
        # The same should happen with an empty identifiers list
        identifiers = []
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({'identifiers': identifiers}))
        # See if we received the expected results
        self.assertEqual(r.json['Error'], 'Unable to get results!')
        self.assertEqual(r.json['Error Info'], 'No identifiers/objects found in POST body')

    @httpretty.activate
    def test_position_search_200(self):
        '''Test to see if calling the position search endpoint
           works for valid data'''
        # Define mock data to be returned to mock external SIMBAD query
        SIMBAD_QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        simbad_mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"],[3253618, "NAME SMC", "NAME SMC"]]}
        # Define mock data to be returned to mock external NED query
        NED_QUERY_URL = self.app.config.get('OBJECTS_NED_OBJSEARCH')
        ned_mockdata = "\n".join(['bibcode1|Andromeda|foo|bar'])
        # The test query we will provide
        query = 'bibstem:A&A object:"80.89416667 -69.75611111:0.166666" year:2015'
        # Mock the SIMBAD reponse
        httpretty.register_uri(
            httpretty.POST, SIMBAD_QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(simbad_mockdata))
        # Mock the NED response
        httpretty.register_uri(
            httpretty.GET, NED_QUERY_URL,
            content_type='text/plain',
            status=200,
            body='%s'%json.dumps(ned_mockdata))
        # Do the POST request
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({'query': query}))
        # The response should have a status code 200
        # See if we received the expected results
        expected = {u'query': u'bibstem:A&A (simbid:(3253618 OR 1575544 OR 3133169) OR nedid:(Andromeda)) year:2015'}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_position_search_NED_SIMBAD_error(self):
        '''Test to see if calling the position search endpoint
           works for valid data'''
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        def exceptionCallback(request, uri, headers):
            data = request.body
            if data.find('SELECT+TOP+1+') > -1:
                return (200, headers, '%s'%json.dumps(mockdata))
            service = 'SIMBAD'
            if 'caltech' in uri:
                service = 'NED'
            raise Exception('Query to {0} blew up!'.format(service))
        # Define mock data to be returned to mock external SIMBAD query
        SIMBAD_QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        simbad_mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"],[3253618, "NAME SMC", "NAME SMC"]]}
        # Define mock data to be returned to mock external NED query
        NED_QUERY_URL = self.app.config.get('OBJECTS_NED_OBJSEARCH')
        ned_mockdata = "\n".join(['bibcode1|Andromeda|foo|bar'])
        # The test query we will provide
        query = 'bibstem:A&A object:"80.89416667 -69.75611111:0.166666" year:2015'
        # Mock the SIMBAD reponse
        httpretty.register_uri(
            httpretty.POST, SIMBAD_QUERY_URL,
            content_type='application/json',
            body=exceptionCallback)
        # Mock the NED response
        httpretty.register_uri(
            httpretty.GET, NED_QUERY_URL,
            content_type='text/plain',
            body=exceptionCallback)
        # Do the POST request
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({'query': query}))
        # The response should have a status code 200
        # See if we received the expected results
        expected = {'Error':'Unable to get results!',
                    'Error Info':'SIMBAD request failed (not timeout): Query to SIMBAD blew up!, NED cone search failed (Query to NED blew up!)'}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_id_search_200(self):
        '''Test to see if calling the id search endpoint
           works for valid data'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],
                             [3133169, "NAME LMC", "NAME LMC"],
                             [1471968,"* 51 Peg b","* 51 Peg b"],
                             [1471968,"NAME Dimidium","* 51 Peg b"],
                             [3267798,"V* W Cen","V* W Cen"]]}
        # We will be doing a POST request with a set of identifiers
        objects = ["Andromeda", "LMC", "51 Peg b", "Dimidium", "w Cen"]
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # Do the POST request
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({'objects': objects}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {'LMC': {'id': '3133169', 'canonical': 'LMC'}, 
                    'Andromeda': {'id': '1575544', 'canonical': 'ANDROMEDA'},
                    '51 Peg b': {'id': '1471968', 'canonical': '51 Peg b'},
                    'Dimidium': {'id': '1471968', 'canonical': '51 Peg b'},
                    'w Cen': {'id': '3267798', 'canonical': 'W Cen'}}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_query_search_200(self):
        '''test translation Solr query with "object:" modifier'''
        # Define mock data to be returned to mock external SIMBAD query
        SIMBAD_QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        simbad_mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"],[3253618, "NAME SMC", "NAME SMC"]]}
        # Define mock data to be returned to mock external NED query
        NED_QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        ned_mockdata = {'NameResolver': 'NED-Egret', 
                        'Copyright': '(C) 2017 California Institute of Technology',
                        'Preferred': {'Name': 'Andromeda'},
                        'ResultCode': 3, 
                        'StatusCode': 100}
        # The test query we will provide
        query = 'bibstem:A&A object:Andromeda year:2015'
        # Mock the SIMBAD reponse
        httpretty.register_uri(
            httpretty.POST, SIMBAD_QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(simbad_mockdata))
        # Mock the NED response
        httpretty.register_uri(
            httpretty.POST, NED_QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(ned_mockdata))
        # Do the POST request
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({'query': query}))
        # The response should have a status code 200
        # See if we received the expected results
        expected = {'query': 'bibstem:A&A ((abs:Andromeda OR simbid:1575544 OR nedid:Andromeda) database:astronomy) year:2015'}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_list_query_search_200(self):
        '''test translation Solr query (submitted as list) with "object:" modifier'''
        # Define mock data to be returned to mock external SIMBAD query
        SIMBAD_QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        simbad_mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"],[3253618, "NAME SMC", "NAME SMC"]]}
        # Define mock data to be returned to mock external NED query
        NED_QUERY_URL = self.app.config.get('OBJECTS_NED_URL')
        ned_mockdata = {'NameResolver': 'NED-Egret',
                        'Copyright': '(C) 2017 California Institute of Technology',
                        'Preferred': {'Name': 'Andromeda'},
                        'ResultCode': 3,
                        'StatusCode': 100}
        # The test query we will provide
        query = ['bibstem:A&A object:Andromeda year:2015']
        # Mock the SIMBAD reponse
        httpretty.register_uri(
            httpretty.POST, SIMBAD_QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(simbad_mockdata))
        # Mock the NED response
        httpretty.register_uri(
            httpretty.POST, NED_QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(ned_mockdata))
        # Do the POST request
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({'query': query}))
        # The response should have a status code 200
        # See if we received the expected results
        expected = {'query': 'bibstem:A&A ((abs:Andromeda OR simbid:1575544 OR nedid:Andromeda) database:astronomy) year:2015'}
        self.assertEqual(r.json, expected)

    def test_object_search_empty_query(self):
        '''An empty query string should result in an error'''
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {"Error": "Unable to get results!",
                    "Error Info": "No identifiers/objects found in POST body"}
        self.assertEqual(r.json, expected)

    def exceptionCallback():
        return Exception('Something went wrong!')

    @mock.patch('object_service.utils.isBalanced')
    def test_query_search_parsing_error(self, mock_isBalanced):
        mock_isBalanced.side_effect = Exception('Something went wrong!')
        query = 'bibstem:A&A object:Andromeda year:2015'
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({'query': query}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {"Error": "Unable to get results!",
                "Error Info": 'Parsing the identifiers out of the query string blew up! (Something went wrong!)'}
        self.assertEqual(r.json, expected)

    def object_search_unknown_source(self):
        '''Test to see if calling the object search endpoint
           with an unknown source throws an error'''
        # We will be doing a POST request with a set of identifiers
        identifiers = ["3133169", "1575544"]
        source = "edwin"
        # Do the POST request
        r = self.client.post(
            url_for('objectsearch'),
            content_type='application/json',
            data=json.dumps({'identifiers': identifiers, 'source':source}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {"Error": "Unable to get results!",
                    "Error Info": "Unsupported source for object data specified: %s"%source}
        self.assertEqual(r.json, expected)

if __name__ == '__main__':
    unittest.main()
