from __future__ import absolute_import
from werkzeug.serving import run_simple
from .views import ObjectSearch
from .views import QuerySearch
from .views import ClassicObjectSearch
from flask_restful import Api
from flask_discoverer import Discoverer
from adsmutils import ADSFlask


def create_app():
    """
    Create the application and return it to the user
    :return: flask.Flask application
    """

    app = ADSFlask(__name__, static_folder=None)
    app.url_map.strict_slashes = False

    api = Api(app)
    api.add_resource(ObjectSearch, '/', '/<string:objects>', '/<string:objects>/<string:source>')
    api.add_resource(QuerySearch, '/query')
    api.add_resource(ClassicObjectSearch, '/nedsrv')

    discoverer = Discoverer(app)

    return app

if __name__ == "__main__":
    run_simple('0.0.0.0', 5555, create_app(), use_reloader=True, use_debugger=False)
