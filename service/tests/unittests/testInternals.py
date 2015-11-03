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
import mock
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
                    "OBJECTS_SIMBAD_MAX_REC"]
        missing = [x for x in required if x not in self.app.config.keys()]
        self.assertTrue(len(missing) == 0)
        # Check if API has an actual value
        if os.path.exists("%s/local_config.py" % PROJECT_HOME):
            self.assertTrue(
                self.app.config.get('OBJECTS_API_TOKEN', None) != None)

class TestDataRetrieval(TestCase):

    '''Check if methods return expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    @httpretty.activate
    def test_object_translation(self):
        '''Test to see if object translation method behaves as expected'''
        from SIMBAD import translate_object_names
        objects = ['Andromeda','LMC']
        mockdata = {"metadata":[{"name":"id","description":"Identifier","datatype":"char","arraysize":"*","ucd":"meta.id"}],"data":[["NAME ANDROMEDA"],["NAME LMC"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))

        result = translate_object_names(objects)
        expected = ["NAME ANDROMEDA","NAME LMC"]
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_simbad_identifiers(self):
        '''Test to see if retrieval of SIMBAD identifiers method behaves as expected'''
        from SIMBAD import get_simbad_identifiers
        objects = ['Andromeda','LMC']
        mockdata = {"metadata":[{"name":"id","description":"Identifier","datatype":"char","arraysize":"*","ucd":"meta.id"},{"name":"oidref","description":"Object internal identifier","datatype":"long","arraysize":"1"}],"data":[["NAME ANDROMEDA",1575544],["NAME LMC",3133169]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_simbad_identifiers(objects)
        expected = {'data': [{'object': u'NAME ANDROMEDA', 'simbad_id': '1575544'}, {'object': u'NAME LMC', 'simbad_id': '3133169'}]}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_get_simbad_identifiers(self):
        '''Test to see if retrieval of SIMBAD objects method behaves as expected'''
        from SIMBAD import get_simbad_objects
        identifiers = ["3133169", "1575544"]
        mockdata = {"metadata":[{"name":"oid","description":"Object internal identifier","datatype":"long","arraysize":"1","ucd":"meta.record;meta.id"},{"name":"main_id","description":"Main identifier for an object","datatype":"char","arraysize":"*","ucd":"meta.id;meta.main"}],"data":[[3133169,"NAME LMC"],[1575544,"M 31"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        result = get_simbad_objects(identifiers)
        expected = {'data': [{'object': u'NAME LMC', 'simbad_id': '3133169'}, {'object': u'M 31', 'simbad_id': '1575544'}]}
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_do_cone_search(self):
        '''Test to see if SIMBAD cone search method behaves as expected'''
        from SIMBAD import parse_position_string
        from SIMBAD import do_position_query
        pstring = "80.89416667 -69.75611111:0.166666"
        mockdata = {"metadata":[{"name":"coo_bibcode","description":"Coordinate reference","datatype":"char","arraysize":"19","ucd":"meta.bib.bibcode;pos.eq"}],"data":[["2003A&A...405..111G"],["2011AcA....61..103G"]]}
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