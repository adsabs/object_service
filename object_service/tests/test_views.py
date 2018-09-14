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

class TestViews(TestCase):

    '''Check if methods return expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    @httpretty.activate
    def test_empty_post_request(self):
        '''test ObjectSearch view - empty request'''
        from object_service.views import ObjectSearch
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        def request_callback(request, uri, headers):
            data = request.body
            return (200, headers, '%s'%json.dumps(mockdata))
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=request_callback)
        ObjSrch = ObjectSearch()
        # First do empty post request
        result = ObjSrch.post()
        expected = ({'Error Info': 'No identifiers/objects found in POST body', 'Error': 'Unable to get results!'}, 200)
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_post_request_exception(self):
        '''test ObjectSearch view - empty request'''
        from object_service.views import ObjectSearch
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        QUERY_URL_CDS = self.app.config.get('OBJECTS_SIMBAD_TAP_URL_CDS')
        mockdata =  {"data":[[1575544, "NAME ANDROMEDA","NAME ANDROMEDA"],[3133169, "NAME LMC", "NAME LMC"]]}
        def request_callback(request, uri, headers):
            data = request.body
            status = 200
            if data.find('TOP') == -1:
                return (200, headers, '%s'%json.dumps(mockdata))
            else:
                raise Exception('Problem with CfA TAP service!')
        # Mock the reponse
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, QUERY_URL_CDS,
            content_type='application/json',
            status=200,
            body=request_callback)
        ObjSrch = ObjectSearch()
        # First do empty post request
        result = ObjSrch.post()
        self.assertEqual(self.app.config.get('OBJECTS_SIMBAD_TAP_URL'), self.app.config.get('OBJECTS_SIMBAD_TAP_URL_CDS'))
