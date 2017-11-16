from views import ObjectSearch, PositionSearch, QuerySearch
from flask_restful import Api
from flask_discoverer import Discoverer
from flask_cache import Cache
from adsmutils import ADSFlask
# FIXME: temporary imports till mutils has been fixed
import os
import inspect
import object_service

def create_app():
    """
    Create the application and return it to the user
    :return: flask.Flask application
    """

    # FIXME: setting proj_home here is temporary till adsmutils has been fixed
    proj_home = os.path.dirname(inspect.getsourcefile(object_service))
    # after the fix: app = ADSFlask(__name__, static_folder=None)
    app = ADSFlask(__name__, static_folder=None, proj_home=proj_home)
    app.url_map.strict_slashes = False

    app.cache = Cache(app) 

    api = Api(app)
    api.add_resource(ObjectSearch, '/', '/<string:objects>', '/<string:objects>/<string:source>')
    api.add_resource(PositionSearch, '/pos/<string:pstring>')
    api.add_resource(QuerySearch, '/query')

    discoverer = Discoverer(app)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False)
