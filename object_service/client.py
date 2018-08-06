from flask import current_app

client = lambda: Client(current_app.config).session


class Client:
    """
    The Client class is a thin wrapper around adsmutils ADSFlask client; Use it as a centralized
    place to set application specific parameters, such as the oauth2
    authorization header
    """
    def __init__(self, config):
        """
        Constructor
        :param client_config: configuration dictionary of the client
        """

        self.session = current_app.client # Use HTTP pool provided by adsmutils ADSFlask
        self.token = config.get('OBJECTS_API_TOKEN')
        if self.token:
            self.session.headers.update(
                {'Authorization': 'Bearer %s' % self.token}
            )
