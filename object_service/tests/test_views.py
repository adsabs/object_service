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

    def test_empty_post_request(self):
        '''test ObjectSearch view - empty request'''
        from object_service.views import ObjectSearch

        ObjSrch = ObjectSearch()
        # First do empty post request
        result = ObjSrch.post()
        expected = ({'Error Info': 'No identifiers/objects found in POST body', 'Error': 'Unable to get results!'}, 200)
        self.assertEqual(result, expected)
