#! /usr/bin/env python
#-------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 1. Feb 2015
# Copyright:
# License:
#-------------------------------------------------------------------------------

import ConfigParser
import csv
import traceback
import sys
from os.path import isfile

import numpy as np

import tweepy

from login import login

# DATA_DIR = "../data/twitter/"
DATA_DIR_CSV = "../data/twitter/CSV/" # trimmed tweets
DATA_DIR_JSON = "../data/twitter/JSON/" # raw tweets

ALPHA = 0.5 # min percentage of area tweets
MIN_TWEETS = 50
MAX_TWEETS = 0 # No maximum limit

GEO_AREA = [-122.5893, 37.1719, -121.6862, 38.0196] # San Francisco bay area
# bbox = [west, south, east, north]
# California: -124.48,32.53,-114.13,42.01
# SF bay area: -122.5893,37.1719,-121.6862,38.0196
# SF city: -122.614895,37.63983,-122.28178,37.929844
# Oakland: -122.355881,37.632226,-122.114672,37.885368

#-------------------------------------------------------------------------------
# Helper functions

import ssl
from functools import wraps

def sslwrap(func): # patch bug in tweepy
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar

ssl.wrap_socket = sslwrap(ssl.wrap_socket)

def get_trace():
    return ''.join(traceback.format_exception(*sys.exc_info()))

def in_area(c, area):
    lng, lat = c
    return (lng >= GEO_AREA[0] and lng < GEO_AREA[2]
        and lat >= GEO_AREA[1] and lat < GEO_AREA[3])

#-------------------------------------------------------------------------------

def get_all_tweets(api, user_id):
    """
    User specific tweet crawler. It returns up to ~3200 tweets for a given user ID.

    Args:
        api (tweepy.API)
        user_id (str): The Twitter user ID.

    Returns:
        out_tweets: a list of tweets as CSV rows of the form
            "user_id,id,created_at,text,lng,lat"
        all_tweets: a list of raw JSON objects (tweets).
    """
    all_tweets = []

    savepath = DATA_DIR_CSV + "%s_tweets.csv" % user_id
    if isfile(savepath):
        print "Skipping user %s: CSV data already present in %s." % (user_id, savepath)
        return None

    print "Processing user", user_id

    new_tweets = api.user_timeline(user_id=user_id, count=200)
    geo_tweets = [t for t in new_tweets if (t.geo or t.coordinates)]
    all_tweets.extend(geo_tweets)

    oldest = all_tweets[-1].id - 1 # oldest tweet id

    while len(new_tweets) > 0:
    	new_tweets = api.user_timeline(
            user_id=user_id, count=200, max_id=oldest)
        geo_tweets = [t for t in new_tweets if (t.geo or t.coordinates)]
    	all_tweets.extend(geo_tweets)

        if len(geo_tweets) == 0:
            break
    	oldest = all_tweets[-1].id - 1
        print "...%s tweets downloaded so far" % (len(all_tweets))

    if len(all_tweets) < MIN_TWEETS:
        print "Skipping user %s: less than %s tweets (%s)" % (user_id, MIN_TWEETS, len(all_tweets))
        return None
    elif MAX_TWEETS > 0 and len(all_tweets) > MAX_TWEETS:
        print "Skipping user %s: more than %s tweets (%s)" % (user_id, MAX_TWEETS, len(all_tweets))
        return None

    coord = lambda t: t.coordinates["coordinates"] if t.coordinates else t.geo
    # filter relevant information
    out_tweets = [
        [user_id,
        tweet.id_str,
        tweet.created_at,
        tweet.text.encode("utf-8"),
        coord(tweet)[0] + np.random.randint(-5, 6) / 1e8,
        coord(tweet)[1] + np.random.randint(-5, 6) / 1e8]
        for tweet in all_tweets]

    # calculate percentage of tweets within the geo area
    area_tweets = [1 for t in out_tweets if in_area([t[4], t[5]], GEO_AREA)]
    # 1/2 of the tweets should be within the area
    if float(len(area_tweets)) / len(all_tweets) < ALPHA:
        print "Skipping user %s: too many tweets far from location" % (user_id)
        return None
    else:
        print "User %s: %s tweets downloaded" % (user_id, len(all_tweets))

    return out_tweets, all_tweets

def save_tweets(uid, tweets, raw_tweets=None):
    savepath = DATA_DIR_CSV + "%s_tweets.csv" % uid

    if raw_tweets:
        savepath_raw = DATA_DIR_JSON + "%s_ALL_tweets.json" % uid
        with open(savepath_raw, 'wb') as f:
            f.write(str(raw_tweets))

    with open(savepath, 'wb') as f:
		writer = csv.writer(f)
		writer.writerow(["user_id","id","created_at","text","lng","lat"])
		writer.writerows(tweets)
    print "Saved tweets of %s in: %s" % (uid, savepath)

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        fn = sys.argv[1] # authentication file
        usersfile = sys.argv[2] # users file
    except IndexError:
        print "Arguments missing"
        sys.exit(0)

    config = ConfigParser.RawConfigParser()
    config.read(fn)

    with open(usersfile, "r") as uf:
        # users that where already spotted at the geo area
        userids = uf.read().split(",")

    try:
        auth = login(config)
        api = tweepy.API(auth,
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True)

        print "Iterating through %s users" % (len(userids))
        for i, uid in enumerate(userids):
            if len(uid) == 0: continue
            try:
                print "(%s of %s)" % (i + 1, len(userids)),
                tweets, raw_tweets = get_all_tweets(api, uid)
            except tweepy.TweepError, e:
                print >> sys.stderr, 'Encountered Exception:', e
                if isinstance(e[0][0], dict) and e[0][0]["code"] == 34:
                    print "User ID %s does not exist" % (uid)
                    continue
                if "JSON" in e:
                    continue
                if e[0] == "Connection aborted.":
                    sys.exit(0)
                print get_trace()
            if not tweets: continue
            # pass 'raw_tweets' as third argument to also save raw JSON tweets
            save_tweets(uid, tweets)

    except KeyboardInterrupt:
        print "KeyboardInterrupt"
        sys.stdout = old_stdout
