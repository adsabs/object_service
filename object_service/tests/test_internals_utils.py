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

    def test_query_string_cleanup(self):
        '''Check is query string gets cleaned up correctly'''
        from object_service.utils import cleanup_query_string
        # First a query string that should not change
        query_string = "object:((LMC OR SMC) AND Andromeda) year:2015 property:refereed"
        result = cleanup_query_string(query_string)
        self.assertEqual(result, query_string)        
        # Now one that needs cleanup
        embedded_string = "trending(citations(object:((LMC OR SMC) AND Andromeda) year:2015 property:refereed))"
        result = cleanup_query_string(embedded_string)
        self.assertEqual(result, query_string)

    def test_parse_query_string(self):
        '''Check is query string is parsed correctly'''
        from object_service.utils import get_objects_from_query_string
        # Unbalanced parentheses should return an empty list
        unbalanced = 'trending(references(citations(object:(Andromeda OR LMC AND M1)))'
        result = get_objects_from_query_string(unbalanced)
        self.assertEqual(result, [])

    def test_solr_query_translation(self):
        '''Check if original Solr query gets translated correctly'''
        from object_service.utils import translate_query
        # Original query
        solr_query = "bibstem:A&A object:((Andromeda OR SMC) AND LMC) year:2015"
        # Objects parsed from query
        identifiers= ['Andromeda', 'SMC', 'LMC']
        # SIMBAD data (translation from object name to SIMBAD identifier)
        name2simbid = {u'SMC': '3253618', u'LMC': '3133169', u'Andromeda': '1575544'}
        # Translate the query
        translated_query = translate_query(solr_query, identifiers, name2simbid, 'simbid:')
        # What are we expecting to get back?
        expected = "bibstem:A&A simbid:((1575544 OR 3253618) AND 3133169) year:2015"
        # Did we get that back?
        self.assertEqual(translated_query, expected)
        # Do something similar for NED
        name2nedid = {'SMC': 'Small_Magellanic_Cloud', 'LMC': 'Large_Magellanic_Cloud', 'Andromeda': '0'}
        translated_query = translate_query(solr_query, identifiers, name2nedid, 'nedid:')
        expected = "bibstem:A&A nedid:((0 OR Small_Magellanic_Cloud) AND Large_Magellanic_Cloud) year:2015"
        self.assertEqual(translated_query, expected)
if __name__ == '__main__':
    unittest.main()
