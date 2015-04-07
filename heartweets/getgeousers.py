#! /usr/bin/env python
#-------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 1. Feb 2015
# Copyright:
# License:
#-------------------------------------------------------------------------------

import ConfigParser
import threading
import time
from datetime import datetime
import traceback
from requests.packages.urllib3.exceptions import ProtocolError
import os, sys

import tweepy

from login import login
import gettweets as gtw

DATA_DIR = "../data/twitter/" # relative to this file path

#-------------------------------------------------------------------------------
# Helper functions

def get_trace():
    return "".join(traceback.format_exception(*sys.exc_info()))

#-------------------------------------------------------------------------------

geo_users = [] # users with tweet geo locations enabled

class Listener(tweepy.StreamListener):
    def __init__(self, savepath, parallel=False):
        tweepy.StreamListener.__init__(self)
        self.i = 0
        self.nusers = 0
        self.savepath = savepath
        self.notification = "Saved to file:"
        self.parallel = parallel

    def save_user_info(self, user_id):
        tweets = gtw.get_all_tweets(api, user_id)
        if tweets:
            fmt_tweets, raw_tweets = tweets
            gtw.save_tweets(user_id, fmt_tweets, raw_tweets) # pass raw_tweets to save them

    def on_status(self, status):
        global geo_users
        try:
            user_id = status.author.id_str

            if (status.geo or status.coordinates) and user_id not in geo_users:
                geo_users.append(user_id)
                self.nusers += 1
                if self.parallel:
                    th = threading.Thread(
                        target=self.save_user_info, args=[user_id])
                    # th.daemon = True
                    th.start()
                    th.join()

            self.i += 1

            if self.i % 100 == 0:
                self.i = 0
                self.save()

        except tweepy.TweepError, e:
            print >> sys.stderr, 'Encountered Exception:', e, get_trace()
            pass

        return True

    def on_error(self, status_code):
        print 'Encountered error with status code:', status_code
        return True

    def save(self):
        global geo_users

        with open(self.savepath, 'a') as outfile:
            userstring = ",".join(list(geo_users))
            if self.i > 100:
                userstring = "," + userstring
            outfile.write(userstring)

        print self.notification, self.savepath
        self.notification = "Updated:"
        geo_users = []

def gather_users(parallel=False):
    """
    Twitter stream listener for users within a given bounding box.
    """
    try:
        # save file for storing the user list
        usersdir = os.path.join(DATA_DIR, "users/")
        if not os.path.exists(usersdir): # make sure users dir exists
            os.makedirs(usersdir)

        ts = time.time()
        st = datetime.fromtimestamp(ts).strftime('%Y-%m-%d--%H-%M-%S')
        savepath = os.path.join(usersdir, "users-" + st + ".csv")

        connection_retry = 0
        while True:
            listener = Listener(savepath, parallel=parallel)
            streaming_api = tweepy.streaming.Stream(
                auth, listener, timeout=60)
            # San Francisco
            try:
                streaming_api.filter(locations=[-122.75, 36.8, -121.75, 37.8])
                connection_retry = 0
            except ProtocolError:
                print "Connection failed. Retrying..."
                if connection_retry <= 5:
                    connection_retry += 1
                    pass
                else:
                    break
        else:
            print "Disconnecting..."
            streaming_api.disconnect
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
    finally:
        listener.save()
        print "-"*25
        print listener.nusers, "user-ID's gathered"

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    from optparse import OptionParser

    usage = "./%prog [options] authfile\n\authfile -- the path to the authentication file."
    parser = OptionParser(usage=usage)
    parser.add_option("-p",
        dest="isParallel",
        action="store_true",
        default=False,
        help="parallely get tweets from each found user")
    parser.add_option("-d",
        dest="datadir",
        type="string",
        help="specify the path for the output data directory")

    (options, args) = parser.parse_args()

    try:
        fn = args[0] # authentication file
    except IndexError:
        parser.error("Authentication file not specified.")
        parser.print_help()

    config = ConfigParser.RawConfigParser()
    fn = os.path.join(os.getcwd(), fn) # get absolute path
    config.read(fn)
    auth = login(config)

    api = tweepy.API(auth,
        wait_on_rate_limit=True,
        wait_on_rate_limit_notify=True)

    if options.datadir:
        DATA_DIR = options.datadir

    # main function
    gather_users(parallel=options.isParallel)
