import requests
from flask import current_app, request

requests.packages.urllib3.disable_warnings()

client = lambda: Client(current_app.config)


class Client:
    """
    The Client class is a thin wrapper around requests; Use it as a centralized
    place to set application specific parameters, such as the oauth2
    authorization header
    """
    def __init__(self, config):
        """
        Constructor
        :param client_config: configuration dictionary of the client
        """

        self.session = requests.Session()

    def _sanitize(self, *args, **kwargs):
        headers = kwargs.get('headers', {})
        if 'Authorization' not in headers:
            headers['Authorization'] = current_app.config.get('SERVICE_TOKEN', request.headers.get('X-Forwarded-Authorization', request.headers.get('Authorization', None)))
        kwargs['headers'] = headers

    def get(self, *args, **kwargs):
        self._sanitize(*args, **kwargs)
        return self.session.get(*args, **kwargs)
    
    def post(self, *args, **kwargs):
        self._sanitize(*args, **kwargs)
        return self.session.post(*args, **kwargs)

