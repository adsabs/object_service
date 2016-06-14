import sys
import os
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)
from flask.ext.testing import TestCase
from flask import request
from flask import url_for, Flask
import unittest
import requests
import time
import app
import json
import httpretty

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
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=500,
            body='')
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
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='{}')
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
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='{}')
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
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[["2003A&A...405..111G"],["2011AcA....61..103G"]]}
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # Do the GET request
        url = url_for('positionsearch', pstring="80.89416667 -69.75611111:0.166666")
        r = self.client.get(url)
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {u'data': [u'2011AcA....61..103G', u'2003A&A...405..111G']}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_position_search_poserror(self):
        '''Test position query with invalid position string'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[["2003A&A...405..111G"],["2011AcA....61..103G"]]}
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # First an incorrectly formatted search radius: 
        # this should result in using the default radius and return a valid result
        pstring = "80.89416667 -69.75611111:1 2 3 4"
        url = url_for('positionsearch', pstring=pstring)
        r = self.client.get(url)
        # See if we received the expected results
        expected = {u'data': [u'2011AcA....61..103G', u'2003A&A...405..111G']}
        self.assertEqual(r.json, expected)
        # Next an invalid type for RA and DEC
        pstring = "A B:0.166666"
        url = url_for('positionsearch', pstring=pstring)
        r = self.client.get(url)
        # See if we received the expected results
        expected = 'Invalid position string: %s'%pstring
        self.assertEqual(r.json['Error Info'], expected)
        # Test no sign for DEC
        pstring = "80.89416667 69.75611111:0.166666"
        url = url_for('positionsearch', pstring=pstring)
        r = self.client.get(url)
        # See if we received the expected results
        expected = 'Invalid position string: %s'%pstring
        self.assertEqual(r.json['Error Info'], expected)

    @httpretty.activate
    def test_id_search_200(self):
        '''Test to see if calling the id search endpoint
           works for valid data'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        # We will be doing a POST request with a set of identifiers
        objects = ["Andromeda", "LMC"]
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
        expected = {u'LMC': {'id': '3133169', 'canonical': u'LMC'}, u'Andromeda': {'id': '1575544', 'canonical': u'ANDROMEDA'}}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_query_search_200(self):
        '''test translation Solr query with "object:" modifier'''
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"],[3253618, "NAME SMC", "NAME SMC"]]}
        # The test query we will provide
        query = 'bibstem:A&A object:Andromeda year:2015'
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # Do the POST request
        r = self.client.post(
            url_for('querysearch'),
            content_type='application/json',
            data=json.dumps({'query': query}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {"query": "bibstem:A&A simbid:1575544 year:2015"}
        self.assertEqual(r.json, expected)
