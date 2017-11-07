import os
from flask import Flask
from views import ObjectSearch, PositionSearch, QuerySearch
from flask_restful import Api
from flask_discoverer import Discoverer
from flask_cache import Cache
import logging.config


def create_app():
    """
    Create the application and return it to the user
    :return: flask.Flask application
    """

    app = Flask(__name__, static_folder=None)
    app.url_map.strict_slashes = False

    load_config(app)

    logging.config.dictConfig(
        app.config['OBJECTS_LOGGING']
    )

    app.cache = Cache(app) 

    api = Api(app)
    api.add_resource(ObjectSearch, '/', '/<string:objects>', '/<string:objects>/<string:source>')
    api.add_resource(PositionSearch, '/pos/<string:pstring>')
    api.add_resource(QuerySearch, '/query')

    discoverer = Discoverer(app)

    return app


def load_config(app):
    """
    Loads configuration in the following order:
        1. config.py
        2. local_config.py (ignore failures)
    :param app: flask.Flask application instance
    :return: None
    """

    app.config.from_pyfile('config.py')

    try:
        app.config.from_pyfile('local_config.py')
    except IOError:
        app.logger.warning("Could not load local_config.py")

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False)
