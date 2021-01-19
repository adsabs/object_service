from __future__ import absolute_import
from builtins import map
from builtins import str
from . import luqum
from .luqum.parser import parser
from .luqum.utils import LuceneTreeTransformer
from .NED import get_ned_data
from .SIMBAD import get_simbad_data
from .client import client
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle
from flask import current_app, request

class IncorrectPositionFormatError(Exception):
    pass

class ObjectQueryExtractor(LuceneTreeTransformer):
    def visit_search_field(self, node, parents):
        if isinstance(node, luqum.tree.SearchField):
            if node.name != 'object':
                return node
            else:
                self.revisit = False
                self.object_nodes.append(str(node))
        if isinstance(node.expr, luqum.tree.FieldGroup) or isinstance(node.expr, luqum.tree.Group):
            # We need the following if statement for the case object:("M 81")
            if isinstance(node.expr.expr, luqum.tree.Phrase) or isinstance(node.expr.expr, luqum.tree.Word):
                self.object_names.append(node.expr.expr.value.replace('"','').strip())
            # otherwise it is object:("M 81" OR M1)
            else:
                for o in node.expr.expr.operands:
                    if isinstance(o, luqum.tree.Phrase) or isinstance(o, luqum.tree.Word):
                        self.object_names.append(o.value.replace('"','').strip())
                    else:
                        self.revisit = True
                        self.visit_search_field(o, parents)
        elif isinstance(node.expr, luqum.tree.Word):
            self.object_names.append(node.expr.value)
        elif isinstance(node.expr, luqum.tree.Phrase):
            self.object_names.append(node.expr.value.replace('"','').strip())
        else:
            # This section is to capture contents for recursive calls
            if isinstance(node.expr, luqum.tree.Phrase) or isinstance(node.expr, luqum.tree.Word):
                self.object_names.append(node.expr.expr.value.replace('"','').strip())
            # otherwise it is object:("M 81" OR M1)
            else:
                for o in node.expr.operands:
                    if isinstance(o, luqum.tree.Phrase) or isinstance(o, luqum.tree.Word):
                        self.object_names.append(o.value.replace('"','').strip())
                    else:
                        self.revisit = True
                        self.visit_search_field(o, parents)
        return node

def isBalanced(s):
    """
    Checks if a string has balanced parentheses. This method can be easily extended to
    include braces, curly brackets etc by adding the opening/closing equivalents
    in the obvious places.
    """
    expr = ''.join([x for x in s if x in '()'])
    if len(expr)%2!=0:
        return False
    opening=set('(')
    match=set([ ('(',')') ])
    stack=[]
    for char in expr:
        if char in opening:
            stack.append(char)
        else:
            if len(stack)==0:
                return False
            lastOpen=stack.pop()
    # This part only becomes relevant if other entities (like braces) are allowed
    #        if (lastOpen, char) not in match:
    #            return False
    return len(stack)==0

def parse_query_string(query_string):
    # We only accept Solr queries with balanced parentheses
    balanced = isBalanced(query_string)
    if not balanced:
        current_app.logger.error('Unbalanced parentheses found in Solr query: %s'%query_string)
        return [], []
    # The query string is valid from the parenthese point-of-view
    # First create the query tree
    try:
        query_tree = parser.parse(query_string)
    except Exception as err:
        current_app.logger.error('Parsing query string blew up: %s'%str(err))
        return [], []
    # Instantiate the object that will be used to traverse the tree
    # and extract the nodes associated with object: query modifiers
    extractor = ObjectQueryExtractor()
    # Running the extractor will populate two lists
    # initialize the extractor
    extractor.object_nodes = []
    extractor.object_names = []
    # run the extractor
    extractions = extractor.visit(query_tree)

    return [on for on in extractor.object_names if on.strip()], extractor.object_nodes

def get_object_data(identifiers, service):
    if service == 'simbad':
        object_data = get_simbad_data(identifiers, 'objects')
    elif service == 'ned':
        object_data = get_ned_data(identifiers, 'objects')
    else:
        object_data = {'Error':'Unable to get object data',
                       'Error Info':'Do not have method to get object data for this service: {0}'.format(service)}
    return object_data

def get_object_translations(onames, trgts):
    # initialize with empty map
    idmap = {}
    for trgt in trgts:
        idmap[trgt] = {}
        for oname in onames:
            idmap[trgt][oname] = "0"
    # now get the object translations for the targets specified
    for trgt in trgts:
        for oname in onames:
            result = get_object_data([oname], trgt)
            if 'Error' in result or 'data' not in result:
                # An error was returned!
                current_app.logger.error('Failed to find data for {0} object {1}!: {2}'.format(trgt.upper(), oname, result.get('Error Info','NA')))
                continue
            try:
                # We need to have a 'try' here in case a service returns an empty 'data' attribute
                idmap[trgt][oname] =[e.get('id',0) for e in result['data'].values()][0]
            except:
                continue

    return idmap

def translate_query(solr_query, oqueries, trgts, onames, translations):
    # The goal is to translate the original Solr query with the embedded
    # "object:" queries into a Solr query with actual Solr fields
    # (nedid:, simbid:) and to include an "=abs:" query to simulate the
    # "ADS Objects" search from ADS Classic. The following will be the general patterns
    # a. single object name:
    #      object:Andromeda    --> (simbid:translations['simbid'].get("Andromeda","0") OR nedid:translations['nedid'].get("Andromeda","0") OR =abs:"Andromeda") database:astronomy
    # b. object name as phrase
    #      object:"Large Magellanic Cloud"  --> same idea as under a.
    # c. object query as expression
    #      object:(Boolean expression) like object:(("51 Peg b" OR 16CygB) AND Osiris) -->
    #      (simbid:(boolean expression of simbid translations) OR nedid:(boolean expression of nedid translations) OR =abs:(original boolean)) database:astronomy
    # The approach is then
    # For each of the N object query components O_i (i=1,...,N) parsed out of the original Solr query S, create their translated equivalent
    # T_i (i=1,...,N) and do a replacement S.replace(O_i, T_i)
    for oquery in oqueries:
        query_components = [oquery.replace('object:','=abs:')]
        simbad_query = oquery.replace('object:','simbid:')
        ned_query    = oquery.replace('object:','nedid:')
        for oname in onames:
            if solr_query.find(oquery) == -1:
                continue
            simbad_query = simbad_query.replace(oname, translations['simbad'].get(oname,"0"))
            ned_query = ned_query.replace(oname, translations['ned'].get(oname,"0"))
        if "simbad" in trgts:
            query_components.append(simbad_query)
        if "ned" in trgts:
            query_components.append(ned_query)
        translated_query = "(({0}) database:astronomy)".format(" OR ".join(query_components))
        solr_query = solr_query.replace(oquery, "(({0}) database:astronomy)".format(" OR ".join(query_components)))
    return solr_query

def is_number(n):
    try:
        float(n)   # Type-casting the string to `float`.
                   # If string is not a valid `float`,
                   # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True

def parse_position_string(pstring):
    # In the case of a cone search, we will have received a query of the form
    #   object:"<position>(:<radius>)"
    # (where the search radius is optional)
    search_radius = ''
    if pstring.find(':') > -1:
        position, radius = pstring.split(':')
        radius = radius.rstrip().replace("''",'"')
    else:
        position = pstring.strip()
        radius = ''

    if is_number(radius):
        # A single integer or float was specified: unit is "degrees"
        search_radius = Angle('{0} degrees'.format(radius.strip()))
    elif radius.endswith("'") or radius.endswith('"'):
        # The radius ends with a single or double quote: arcsec or arcmin
        search_radius = Angle(radius)
    elif radius.count(' ') in [1,2]:
        # Sexagesimal format is assumed: (degree, arcmin, arcsec)
        try:
            c = tuple(map(int, radius.split()))
            search_radius = Angle(c, unit=u.deg)
        except:
            pass
    else:
        search_radius = ''
    # Check if we have a search radius
    if not search_radius:
        # If not, take the default value
        search_radius = Angle('{0} degrees'.format(current_app.config.get('OBJECTS_DEFAULT_RADIUS')))
    # Now try to parse the position string using astropy
    coords = None
    if position.count(" ") == 5:
        # We have a position: 05 23 34.6 -69 45 22
        coords = SkyCoord(position, unit=(u.hourangle, u.deg))
    elif position.count(" ") == 1:
        ra, dec = position.split()
        if is_number(ra) and is_number(dec):
            # We have a position: 80.894167 -69.756111
            coords = SkyCoord(float(ra), float(dec), frame='icrs', unit='deg')
        else:
            # Assume that we have: 05h23m34.6s -69d45m22s
            try:
                coords = SkyCoord(ra, dec, frame='icrs')
            except:
                pass
    # If we don't have a valid position by now, raise an exception
    if not coords:
        raise IncorrectPositionFormatError

    return coords, search_radius

def verify_query(identifiers, field):
    # Safeguard for guarantee that SIMBAD and NED identifiers found are
    # indeed in Solr index
    query = '{0}:({1})'.format(field, " OR ".join(identifiers))
    params = {'wt': 'json', 'q': query, 'fl': 'id',
              'rows': 10}
    response = current_app.client.get(current_app.config['OBJECTS_SOLRQUERY_URL'], params=query)
    if response.status_code != 200:
        return {"Error": "Unable to get results!",
                "Error Info": "Solr response: %s" % str(response.text),
                "Status Code": response.status_code}
    resp = response.json()
    try:
        docs = resp['response']['docs']
    except:
        docs = []
    # return True (we found docs) or False (no docs found)
    return len(docs) > 0
