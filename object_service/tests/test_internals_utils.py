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


class TestDataRetrieval(TestCase):

    '''Check if methods return expected results'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    def test_balanced_parentheses(self):
        '''Check the function that checks for balanced parentheses'''
        from object_service.utils import isBalanced
        # First give a test that should return True
        balanced = 'trending(references(citations(object:(Andromeda OR LMC) AND M1)))'
        self.assertTrue(isBalanced(balanced))
        # Now check an unbalanced example
        unbalanced = 'trending(references(citations(object:(Andromeda OR LMC AND M1)))'
        self.assertFalse(isBalanced(unbalanced))
        # No parentheses should return True
        noparenths = 'foo'
        self.assertTrue(isBalanced(noparenths))
        # Wrong order should return False
        test = ')x('
        self.assertFalse(isBalanced(test))

    def test_parse_query_string_unbalanced(self):
        '''Check is query string is parsed correctly'''
        from object_service.utils import parse_query_string
        # Unbalanced parentheses should return an empty list
        unbalanced = 'trending(references(citations(object:(Andromeda OR LMC AND M1)))'
        object_names, object_queries = parse_query_string(unbalanced)
        self.assertEqual(object_names, [])
        self.assertEqual(object_queries, [])
    
    def test_parse_query_string(self):
        '''Check is query string is parsed correctly'''
        from object_service.utils import parse_query_string
        qstring = 'citations(object:((Andromeda OR LMC) AND M1) OR fulltext:SMC) year:2010 property:refereed object:foo'
        object_names, object_queries = parse_query_string(qstring)
        self.assertEqual(object_names, ['Andromeda', 'LMC', 'M1','foo'])
        self.assertEqual(object_queries, ['object:((Andromeda OR LMC) AND M1)','object:foo'])
    
    def test_parse_query_string_empty(self):
        '''Check is query string is parsed correctly'''
        from object_service.utils import parse_query_string
        # Unbalanced parentheses should return an empty list
        empty = 'object:""'
        object_names, object_queries = parse_query_string(empty)
        self.assertEqual(object_names, [])

    def test_parse_query_parse_error(self):
        '''Check is query string is parsed correctly'''
        from object_service.utils import parse_query_string
        # Unbalanced parentheses should return an empty list
        empty = 'object:()'
        object_names, object_queries = parse_query_string(empty)
        self.assertEqual(object_names, [])

    def test_invalid_service(self):
        '''Any target service other than SIMBAD or NED is not accepted'''
        from object_service.utils import get_object_data
        service = 'BAR'
        result = get_object_data(['foo'], service)
        expected = {'Error':'Unable to get object data',
                    'Error Info':'Do not have method to get object data for this service: {0}'.format(service)}

        self.assertEqual(result, expected)

    @httpretty.activate   
    def test_failed_object_data_retrieval(self):
        from object_service.utils import get_object_translations
        def exceptionCallback(request, uri, headers):
            raise ReadTimeout('Connection timed out.')
        QUERY_URL = self.app.config.get('OBJECTS_SIMBAD_TAP_URL')
        httpretty.register_uri(
            httpretty.POST, QUERY_URL,
            body=exceptionCallback)
        result = get_object_translations(['a'],['simbad'])
        self.assertEqual(result, {'simbad': {'a': '0'}})

if __name__ == '__main__':
    unittest.main()
