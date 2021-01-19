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

class TestExpectedResults(TestCase):

    '''Check if the service returns expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    @httpretty.activate
    def test_classic_query_search_200(self):
        '''test query for the ADS Classic NED support'''
        NED_URL = self.app.config.get('OBJECTS_NED_URL')
        SOLRQUERY_URL = self.app.config.get('OBJECTS_SOLRQUERY_URL')
        # Mock data to simulate a NED response
        neddata =  {u'NameResolver': u'NED-Egret',
                     u'Copyright': u'(C) 2018 California Institute of Technology',
                     u'Preferred': {u'ObjType': {u'RefCode': None, u'Value': u'G'},
                     u'Position': {u'PosAngle': 0.0,
                                   u'UncSemiMinor': 2.222222222e-05,
                                   u'RefCode': u'2010ApJS..189...37E',
                                   u'RA': 10.68479292,
                                   u'Dec': 41.269065,
                                   u'UncSemiMajor': 2.222222222e-05},
                     u'Name': u'MESSIER 031',
                     u'Redshift': {u'QualityFlag': None,
                                   u'Uncertainty': 1.29999999e-05,
                                   u'RefCode': u'1991RC3.9.C...0000d',
                                   u'Value': -0.00100100006}},
                     u'QueryTime': u'Tue Feb 13 08:22:54 2018',
                     u'Interpreted': {u'Name': u'NGC 0224'},
                     u'Version': u'2.0',
                     u'Supplied': u'NGC 224',
                     u'ResultCode': 3,
                     u'StatusCode': 100}
        # Mock data to simulate a SOlr response
        solrdata = {u'responseHeader': {u'status': 0,
                                        u'QTime': 89,
                                        u'params': {u'q': u'nedid:3C_273 OR nedid:NGC_0224 year:2016-2018',
                                                    u'rows': u'10000', u'fl': u'bibcode', u'wt': u'json'}
                                       },
                                       u'response': {
                                           u'start': 0,
                                           u'numFound': 43,
                                           u'docs': [{u'bibcode': u'2016ApJ...817..111D'}, {u'bibcode': u'2016A&A...587A..52M'}]}
                    }
        # Mock the NED reponse
        httpretty.register_uri(
            httpretty.POST, NED_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(neddata))
        # Mock the Solr response
        httpretty.register_uri(
            httpretty.GET, SOLRQUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(solrdata))
        # Do the POST request
        r = self.client.post(
            url_for('classicobjectsearch'),
            content_type='application/json',
            data=json.dumps({'objects': ["NGC 224"]}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {u'ambiguous': [], u'data': [u'2016ApJ...817..111D', u'2016A&A...587A..52M']}
        self.assertEqual(r.json, expected)
        # Do the query asking for ASCII output
        r = self.client.post(
            url_for('classicobjectsearch'),
            content_type='application/json',
            data=json.dumps({'objects': ["NGC 224"], 'output_format':'ascii'}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)

    @httpretty.activate
    def test_classic_query_search_ambiguous(self):
        '''test query for the ADS Classic NED support - NED returns ambiguous results'''
        NED_URL = self.app.config.get('OBJECTS_NED_URL')
        SOLRQUERY_URL = self.app.config.get('OBJECTS_SOLRQUERY_URL')
        # Mock data to simulate a NED response
        neddata =  {u'NameResolver': u'NED-Egret',
                     u'Copyright': u'(C) 2018 California Institute of Technology',
                     u'Preferred': {u'ObjType': {u'RefCode': None, u'Value': u'G'},
                     u'Position': {u'PosAngle': 0.0,
                                   u'UncSemiMinor': 2.222222222e-05,
                                   u'RefCode': u'2010ApJS..189...37E',
                                   u'RA': 10.68479292,
                                   u'Dec': 41.269065,
                                   u'UncSemiMajor': 2.222222222e-05},
                     u'Name': u'MESSIER 031',
                     u'Redshift': {u'QualityFlag': None,
                                   u'Uncertainty': 1.29999999e-05,
                                   u'RefCode': u'1991RC3.9.C...0000d',
                                   u'Value': -0.00100100006}},
                     u'QueryTime': u'Tue Feb 13 08:22:54 2018',
                     u'Interpreted': {u'Aliases': ['a','b','c']},
                     u'Version': u'2.0',
                     u'Supplied': u'NGC 224',
                     u'ResultCode': 1,
                     u'StatusCode': 100}
        # Mock data to simulate a SOlr response
        solrdata = {u'responseHeader': {u'status': 0,
                                        u'QTime': 89,
                                        u'params': {u'q': u'nedid:3C_273 OR nedid:NGC_0224 year:2016-2018',
                                                    u'rows': u'10000', u'fl': u'bibcode', u'wt': u'json'}
                                       },
                                       u'response': {
                                           u'start': 0,
                                           u'numFound': 43,
                                           u'docs': [{u'bibcode': u'2016ApJ...817..111D'}, {u'bibcode': u'2016A&A...587A..52M'}]}
                    }
        # Mock the NED reponse
        httpretty.register_uri(
            httpretty.POST, NED_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(neddata))
        # Mock the Solr response
        httpretty.register_uri(
            httpretty.GET, SOLRQUERY_URL,
            content_type='application/json',
            status=200,
            body='%s'%json.dumps(solrdata))
        # Do the POST request
        r = self.client.post(
            url_for('classicobjectsearch'),
            content_type='application/json',
            data=json.dumps({'objects': ["NGC 224"]}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {u'ambiguous': [{'NGC 224':['a','b','c']}], u'data': [u'2016ApJ...817..111D', u'2016A&A...587A..52M']}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_classic_query_search_empty_submission(self):
        '''test query for the ADS Classic NED support - empty request - should throw error'''
        # Do the POST request
        r = self.client.post(
            url_for('classicobjectsearch'),
            content_type='application/json',
            data=json.dumps({'objects': []}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 400)
        # See if we received the expected results
        expected = {u'Error Info': u'No object names provided', u'Error': u'Unable to get results!'}
        self.assertEqual(r.json, expected)

    @httpretty.activate
    def test_classic_query_search_incorrect_submission(self):
        '''test query for the ADS Classic NED support - empty request - should throw error'''
        # Do the POST request
        r = self.client.post(
            url_for('classicobjectsearch'),
            content_type='application/json',
            data=json.dumps({}))
        # The response should have a status code 200
        self.assertTrue(r.status_code == 200)
        # See if we received the expected results
        expected = {u'Error Info': u'No object names found in POST body', u'Error': u'Unable to get results!'}
        self.assertEqual(r.json, expected)

if __name__ == '__main__':
    unittest.main()
