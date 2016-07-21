# necessary import
import os
# Configs specific to this ervice
OBJECTS_SECRET_KEY = 'this should be changed'
# URL to access the SIMBAB TAP interface
OBJECTS_SIMBAD_TAP_URL = 'http://simbad.u-strasbg.fr/simbad/sim-tap/sync'
# Time-out in seconds for SIMBAD TAP service requests
OBJECTS_SIMBAD_TIMEOUT = 1
# Cache time-out in seconds (one day = 86400, one week = 604800)
OBJECTS_CACHE_TIMEOUT = 604800
# Default radius for cone search
OBJECTS_DEFAULT_RADIUS = 0.1
# Maximum number of records to return from cone search
OBJECTS_SIMBAD_MAX_REC = 10000
# In what environment are we?
ENVIRONMENT = os.getenv('ENVIRONMENT', 'staging').lower()
# Config for logging
OBJECTS_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(levelname)s\t%(process)d '
                      '[%(asctime)s]:\t%(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S',
        }
    },
    'handlers': {
        'file': {
            'formatter': 'default',
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/tmp/object_service.app.{}.log'.format(ENVIRONMENT),
        },
        'console': {
            'formatter': 'default',
            'level': 'INFO',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
# General config settings
API_URL = 'https://api.adsabs.harvard.edu'
OBJECTS_SOLRQUERY_URL = '%s/v1/search/query' % API_URL
# Define caching type
CACHE_TYPE = 'simple'
# Define the autodiscovery endpoint
DISCOVERER_PUBLISH_ENDPOINT = '/resources'
# Advertise its own route within DISCOVERER_PUBLISH_ENDPOINT
DISCOVERER_SELF_PUBLISH = False
