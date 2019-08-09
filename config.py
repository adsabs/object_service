# necessary import
import os
LOG_STDOUT = True
# Configs specific to this ervice
OBJECTS_API_TOKEN = 'this should be changed'
# URL to access the SIMBAB TAP interface
# default
OBJECTS_SIMBAD_TAP_URL = 'http://simbad.harvard.edu/simbad/sim-tap/sync'
# backup
OBJECTS_SIMBAD_TAP_URL_CDS = 'http://simbad.u-strasbg.fr/simbad/sim-tap/sync'
# Maximum search radius for SIMBAD (degrees)
OBJECTS_SIMBAD_MAX_RADIUS = 3
# Maximum number of objects for SIMBAD
OBJECTS_SIMBAD_MAX_NUMBER = 50
# URL to access the NED interface
OBJECTS_NED_URL = 'https://ned.ipac.caltech.edu/srs/ObjectLookup'
# URL to access NED objsearch
OBJECTS_NED_OBJSEARCH = 'https://ned.ipac.caltech.edu/cgi-bin/objsearch'
# Maximum search radius for NED (degrees)
OBJECTS_NED_MAX_RADIUS = 3
# Maximum number of objects for NED
OBJECTS_NED_MAX_NUMBER = 50
# Time-out in seconds for SIMBAD TAP service requests
OBJECTS_SIMBAD_TIMEOUT = 8
# Time-out in seconds for NED service requests
OBJECTS_NED_TIMEOUT = 10
# Cache time-out in seconds (one day = 86400, one week = 604800)
OBJECTS_CACHE_TIMEOUT = 604800
# Default radius for cone search (degrees)
OBJECTS_DEFAULT_RADIUS = 0.033333333
# Maximum number of records to send bibcodes back for
OBJECT_SOLR_MAX_HITS = 10000
# In what environment are we?
ENVIRONMENT = os.getenv('ENVIRONMENT', 'staging').lower()
# General config settings
API_URL = 'https://api.adsabs.harvard.edu'
# Where to send Solr queries
OBJECTS_SOLRQUERY_URL = '%s/v1/search/query' % API_URL
# Define caching type
CACHE_TYPE = 'simple'
# Define the autodiscovery endpoint
DISCOVERER_PUBLISH_ENDPOINT = '/resources'
# Advertise its own route within DISCOVERER_PUBLISH_ENDPOINT
DISCOVERER_SELF_PUBLISH = False
