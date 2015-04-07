import tweepy

def login(config):
    """The config file contains:

    [auth]
    CONSUMER_KEY = ...
    CONSUMER_SECRET = ...
    ACCESS_TOKEN = ...
    ACCESS_TOKEN_SECRET = ...
    """
    CONSUMER_KEY = config.get('auth','CONSUMER_KEY')
    CONSUMER_SECRET = config.get('auth','CONSUMER_SECRET')
    ACCESS_TOKEN = config.get('auth','ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = config.get('auth','ACCESS_TOKEN_SECRET')

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    return auth
