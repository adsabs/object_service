from views import ObjectSearch, PositionSearch, QuerySearch
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
    api.add_resource(PositionSearch, '/pos/<string:pstring>')
    api.add_resource(QuerySearch, '/query')

    discoverer = Discoverer(app)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False)
