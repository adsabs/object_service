from __future__ import print_function
import sys
import os
from flask_testing import TestCase
from object_service import app

class TestQueryStringParsing(TestCase):

    '''Check if the query parser works as expected'''

    def create_app(self):
        '''Create the wsgi application'''
        _app = app.create_app()
        return _app

    def test_query_parsing(self):
        '''Test parsing of query strings'''
        from object_service.utils import parse_query_string as parse
        test_cases = {
            'object:Bla':[['Bla'],['object:Bla']],
            'object:"Small Magellanic Cloud"':[['Small Magellanic Cloud'],['object:"Small Magellanic Cloud"']],
            'object:"Bla OR Something"':[['Bla OR Something'],['object:"Bla OR Something"']],
            'object:(Bla OR Something)':[['Bla', 'Something'],['object:(Bla OR Something)']],
            'object:(("*Foo +Ba" OR SMC) AND Andromeda)':[['*Foo +Ba', 'SMC', 'Andromeda'],['object:(("*Foo +Ba" OR SMC) AND Andromeda)']],
            'object:((("*Foo +Ba" OR SMC) AND Andromeda) OR "Something Else")':[['*Foo +Ba', 'SMC', 'Andromeda', 'Something Else'], ['object:((("*Foo +Ba" OR SMC) AND Andromeda) OR "Something Else")']],
            'mod1:bar object:Bla mod2:foo':[['Bla'],['object:Bla']],
            'mod1:bar object:(Bla OR Something) mod2:foo':[['Bla', 'Something'],['object:(Bla OR Something)']],
            'bibstem:"A&A" object:(("*Foo +Ba" OR SMC) AND Andromeda) year:2015':[['*Foo +Ba', 'SMC', 'Andromeda'],['object:(("*Foo +Ba" OR SMC) AND Andromeda)']],
            'bibstem:A&A object:(("*Foo +Ba" OR SMC) AND Andromeda) year:2015':[['*Foo +Ba', 'SMC', 'Andromeda'],['object:(("*Foo +Ba" OR SMC) AND Andromeda)']],
            'object:Foo object:Bar':[['Foo', 'Bar'],['object:Foo','object:Bar']],
            'object:Foo OR object:Bar':[['Foo', 'Bar'],['object:Foo','object:Bar']],
            'object:("Foo Bar" OR Something)':[['Foo Bar', 'Something'],['object:("Foo Bar" OR Something)']],
            'mod1:bar object:(Bla OR Something) mod2:foo object:(X OR Y)':[['Bla', 'Something', 'X', 'Y'],['object:(Bla OR Something)', 'object:(X OR Y)']],
            'citations(reviews(popular(object:("M 1" OR M81) OR =abs:Andromeda))) year:2010 property:refereed': [['M 1', 'M81'],['object:("M 1" OR M81)']],
            }

        for qstring, expected in test_cases.items():
            object_names, object_queries = parse(qstring)
            self.assertEqual(object_names, expected[0])
            self.assertEqual(object_queries, expected[1])
    
    def test_query_translation(self):
        '''Test creation of translated query'''
        from object_service.utils import translate_query as translate
        from object_service.utils import parse_query_string as parse
        
        # mapping of object names to SIMBAD and NED identifiers
        
        obj2id = {
            'simbad': {'X':'123', 'Y':'456', 'Z':'789'},
            'ned':    {'X':'XXX', 'Y':'YYY', 'Z':'0'},
        }
        
        test_cases = {
            'object:X':'((=abs:X OR simbid:123 OR nedid:XXX) database:astronomy)',
            'object:(X OR Y)':'((=abs:(X OR Y) OR simbid:(123 OR 456) OR nedid:(XXX OR YYY)) database:astronomy)',
            'citations(object:(X OR Y) OR fulltext:X) -foo:bar object:Z':'citations(((=abs:(X OR Y) OR simbid:(123 OR 456) OR nedid:(XXX OR YYY)) database:astronomy) OR fulltext:X) -foo:bar ((=abs:Z OR simbid:789 OR nedid:0) database:astronomy)'
        }
        
        for qstring, expected in test_cases.items():
            object_names, object_queries = parse(qstring)
            result = translate(qstring, object_queries, ['simbad', 'ned'], object_names, obj2id)
            print(qstring)
            print(result)
            self.assertEqual(result, expected)
