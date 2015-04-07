
Change the hard-coded path "DATA_DIR" in getgeousers.py and gettweets.py to your output data directory

- Gather user IDs:
```bash
> python getgeousers.py auth.cfg
```

- Download all tweets for the given user IDs:
```bash
> python gettweets.py auth.cfg path_to_user_ids_csv
```

`auth.cfg` (or alike) should contain:
```
[auth]
CONSUMER_KEY = *consumer key*
CONSUMER_SECRET = *consumer secret*
ACCESS_TOKEN = *access token*
ACCESS_TOKEN_SECRET = *access token secret*
```
