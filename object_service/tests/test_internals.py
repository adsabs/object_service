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
                    "OBJECTS_SIMBAD_TAP_URL_CDS",
                    "OBJECTS_NED_URL",
                    "OBJECTS_NED_OBJSEARCH",
                    "OBJECTS_SIMBAD_MAX_RADIUS",
                    "OBJECTS_NED_MAX_RADIUS",
                    "OBJECTS_CACHE_TIMEOUT",
                    "OBJECTS_DEFAULT_RADIUS",
                    "OBJECTS_SIMBAD_MAX_NUMBER",
                    "OBJECTS_NED_URL",
                    "OBJECTS_SOLRQUERY_URL",
                    "API_URL"
                    ]
        missing = [x for x in required if x not in self.app.config.keys()]
        self.assertTrue(len(missing) == 0)

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
    def test_do_ned_query_identifiers_readtimeout(self):
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
        result = get_ned_data(identifiers, "identifiers")
        expected = {'Error': 'Unable to get results!', 'Error Info': 'NED request timed out: Connection timed out.'}
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

    def test_ned_simple_query(self):
        '''Test to see if the "simple" input type works properly'''
        from object_service.NED import get_ned_data

        identifiers = ['NGC_1234','Abell_678']
        result = get_ned_data(identifiers, 'simple')
        expected = {'data': {'Abell_678': {'canonical': 'Abell 678', 'id': 'Abell_678'},
                            'NGC_1234': {'canonical': 'NGC 1234', 'id': 'NGC_1234'}},
                    'skipped':[]
                   }
        self.assertDictEqual(result, expected)

    def test_ned_unknown_inputtype(self):
        '''Test to see if unknown input type works properly'''
        from object_service.NED import get_ned_data

        identifiers = ['NGC_1234','Abell_678']
        result = get_ned_data(identifiers, 'foo')
        expected = {'Error': 'Unable to get results!', 'Error Info': 'Unknown input type specified!'}
        self.assertDictEqual(result, expected)

    def test_simbad_unknown_inputtype(self):
        '''Test to see if unknown input type works properly'''
        from object_service.SIMBAD import get_simbad_data

        identifiers = ['NGC_1234','Abell_678']
        result = get_simbad_data(identifiers, 'foo')
        expected = {'Error': 'Unable to get results!', 'Error Info': 'Unknown input type specified!'}
        self.assertDictEqual(result, expected)


    @httpretty.activate
    def test_get_simbad_objects_timeout(self):
        '''Test to see if retrieval of SIMBAD objects method behaves as expected'''
        from object_service.SIMBAD import get_simbad_data

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        identifiers = ["3133169", "1575544"]
        self.app.config['OBJECTS_SIMBAD_TIMEOUT'] = 1
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_simbad_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!', 'Error Info': 'SIMBAD request timed out: Connection timed out.'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_get_simbad_position_query_timeout(self):
        '''Test to see if SIMBAD position query method behaves as expected'''
        from object_service.SIMBAD import simbad_position_query
        from astropy.coordinates import SkyCoord
        from astropy.coordinates import Angle
        from astropy import units as u

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        identifiers = ["3133169", "1575544"]
        self.app.config['OBJECTS_SIMBAD_TIMEOUT'] = 1
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        c = SkyCoord("0.1 0.1", unit=(u.deg, u.deg))
        r = Angle('0.1 degrees')
        result = simbad_position_query(c, r)
        expected = {'Error Info': 'SIMBAD request timed out: Connection timed out.', 'Error': 'Unable to get results!'}

        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_get_ned_position_query_timeout(self):
        '''Test to see if NED position query method behaves as expected'''
        from object_service.NED import ned_position_query
        from astropy.coordinates import SkyCoord
        from astropy.coordinates import Angle
        from astropy import units as u

        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')

        identifiers = ["3133169", "1575544"]
        self.app.config['OBJECTS_SIMBAD_TIMEOUT'] = 1
        QUERY_URL = self.app.config.get('OBJECTS_NED_OBJSEARCH')
        httpretty.register_uri(
            httpretty.GET, QUERY_URL,
            body=exceptionCallback)
        
        c = SkyCoord("11.1 11.1", unit=(u.deg, u.deg))
        r = Angle('0.1 degrees')
        result = ned_position_query(c, r)
        expected = {'Error Info': 'NED cone search timed out: Connection timed out.', 'Error': 'Unable to get results!'}

        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_get_ned_position_query_exception(self):
        '''Test to see if NED position query method behaves as expected'''
        from object_service.NED import ned_position_query
        from astropy.coordinates import SkyCoord
        from astropy.coordinates import Angle
        from astropy import units as u

        def exceptionCallback(request, uri, headers):
            raise Exception('Houston, we have a problem!')

        identifiers = ["3133169", "1575544"]
        self.app.config['OBJECTS_SIMBAD_TIMEOUT'] = 1
        QUERY_URL = self.app.config.get('OBJECTS_NED_OBJSEARCH')
        httpretty.register_uri(
            httpretty.GET, QUERY_URL,
            body=exceptionCallback)
        c = SkyCoord("11.1 11.1", unit=(u.deg, u.deg))
        r = Angle('0.1 degrees')
        result = ned_position_query(c, r)
        expected = {'Error Info': 'NED cone search failed (Houston, we have a problem!)', 'Error': 'Unable to get results!'}

        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_get_simbad_objects_exception(self):
        '''Test to see if retrieval of SIMBAD objects method behaves as expected'''
        from object_service.SIMBAD import get_simbad_data

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')

        identifiers = ["3133169", "1575544"]
        self.app.config['OBJECTS_SIMBAD_TIMEOUT'] = 1
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_simbad_data(identifiers, 'identifiers')
        expected = {'Error': 'Unable to get results!', 'Error Info': 'SIMBAD request failed (not timeout): Oops! Something went boink!'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_cone_search(self):
        '''Test to see if SIMBAD cone search method behaves as expected'''
        from object_service.utils import parse_position_string
        from object_service.SIMBAD import simbad_position_query
        pstring = "80.89416667 -69.75611111:0.166666"
        mockdata = {"data":[["2003A&A...405..111G"],["2011AcA....61..103G"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # First parse the position string and see we if get the expected results back
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], ['80.8942','-69.7561',0.166666])
        # Next query with this positional information
        result = simbad_position_query(coords, radius)
        expected = [u'2011AcA....61..103G', u'2003A&A...405..111G']
        self.assertEqual(result, expected)

    @httpretty.activate
    def test_do_cone_search_exception(self):
        '''Test to see if SIMBAD cone search method behaves as expected'''
        from object_service.SIMBAD import simbad_position_query
        from astropy.coordinates import SkyCoord
        from astropy.coordinates import Angle
        from astropy import units as u

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')

        pstring = "80.89416667 -69.75611111:0.166666"
        mockdata = {"data":[["2003A&A...405..111G"],["2011AcA....61..103G"]]}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body=exceptionCallback)
        # First parse the position string and see we if get the expected results back
        c = SkyCoord("80.89416667 -69.7561111", unit=(u.deg, u.deg))
        r = Angle('0.2 degrees')
        result = simbad_position_query(c, r)
        print "XXXX"
        print result
        expected = {'Error Info': 'SIMBAD request failed (not timeout): Oops! Something went boink!', 'Error': u'Unable to get results!'}
        self.assertDictEqual(result, expected)

    @httpretty.activate
    def test_do_cone_search_malformed_response(self):
        '''Test to see if SIMBAD cone search method behaves as expected'''
        from object_service.SIMBAD import simbad_position_query
        from astropy.coordinates import SkyCoord
        from astropy.coordinates import Angle
        from astropy import units as u

        def exceptionCallback(request, uri, headers):
            raise Exception('Oops! Something went boink!')

        mockdata = {"foo":"bar"}
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(mockdata))
        # First parse the position string and see we if get the expected results back
        c = SkyCoord("80.89416667 -69.7561111", unit=(u.deg, u.deg))
        r = Angle('0.2 degrees')
        result = simbad_position_query(c, r)
        expected = {'Error Info': 'Unable to retrieve SIMBAD identifiers from SIMBAD response (no "data" key)!', 'Error': 'Unable to get results!'}
        self.assertDictEqual(result, expected)

    def test_parse_position_string_default_radius(self):
        '''Test to see if SIMBAD cone search method interprets position string correctly'''
        from object_service.utils import parse_position_string
        from object_service.utils import IncorrectPositionFormatError

        pstring = "80.89416667 -69.75611111:0.166666"
        # Get the value of the default radius
        default_radius = self.app.config.get('OBJECTS_DEFAULT_RADIUS')
        # First parse the position string and see we if get the expected results back
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'80.8942', u'-69.7561', 0.166666])
        # An invalid radius results in the the default radius
        pstring = "80.89416667 -69.75611111:1 2 3 4"
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'80.8942', u'-69.7561', default_radius])
        # Check if the hms to decimal conversion works as expected
        pstring = "80.89416667 -69.75611111:1 30"
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'80.8942', u'-69.7561', 1.5])
        # No radius in input string results in default radius
        pstring = "80.89416667 -69.75611111"
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'80.8942', u'-69.7561', default_radius])
        # Invalid hms string results in default radius
        pstring = "80.89416667 -69.75611111:a b"
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'80.8942', u'-69.7561', default_radius])
        #
        pstring = "80.89416667 -69.75611111:a"
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'80.8942', u'-69.7561', default_radius])
        # There has to be RA and DEC
        pstring = "80.89416667"
        error = ''
        try:
            result = parse_position_string(pstring)
        except IncorrectPositionFormatError:
            error = 'Incorrect Position Format'
        self.assertEqual(error, 'Incorrect Position Format')
        # Check position strings of the format "hh mm ss [+-]dd mm ss"
        pstring = "18 04 20.99 -29 31 08.9"
        coords, radius = parse_position_string(pstring)
        RA, DEC = coords.to_string('decimal').split()
        self.assertEqual([RA, DEC, radius.degree], [u'18.0725', u'-29.5191', default_radius])

    def test_cleanup_obhect_names_simbad(self):
        '''Test to see if SIMBAD cleans up object string correctly'''
        from object_service.SIMBAD import cleanup_object_name
        # The function should remove catalogue prefixes
        cats = ['NAME','*','V*','SV*']
        objects = ["%s foobar"%c for c in cats]
        result = list(set([cleanup_object_name(o) for o in objects]))
        self.assertEqual(result, ['foobar'])

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

if __name__ == '__main__':
    unittest.main()
