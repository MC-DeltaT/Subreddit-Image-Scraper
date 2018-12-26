import json
import logging
import os
import praw
import prawcore
import sys
import time

import utility



_logger = logging.getLogger()


_current_directory = os.path.dirname(os.path.realpath(__file__))
_config_path = os.path.join(sys.argv[1], "grabber_config.json")
_config_schema_path = os.path.join(_current_directory, "grabber_config_schema.json")

_logger.debug("Loading configuration schema from file")
try:
	_config_schema = utility.load_json(_config_schema_path)
except json.JSONDecodeError as e:
	_logger.error("JSON decode failed: {}".format(repr(e)))
	sys.exit(1)
except FileNotFoundError:
	_logger.error("Configuration schema file not found")
	sys.exit(1)

_logger.info("Loading configuration from file")
try:
	_config = utility.load_json(_config_path)
except json.JSONDecodeError as e:
	_logger.error("JSON decode failed: {}".format(repr(e)))
	sys.exit(1)
except FileNotFoundError:
	_logger.error("Configuration file not found")
	sys.exit(1)

_errors = utility.validate_json(_config, _config_schema)
if len(_errors) > 0:
	for _e in _errors:
		_logger.error(_e)
	sys.exit(1)


_reddit = praw.Reddit(client_id = _config["client_id"], client_secret = _config["client_secret"], user_agent = _config["user_agent"])


def grab():
	# Maps subreddit names to their list of new posts.
	post_listings = dict()

	for subreddit_name in _config["subreddits"]:
		_logger.info('Grabbing posts from subreddit "{}"'.format(subreddit_name))
		
		subreddit = _reddit.subreddit(subreddit_name)
		
		while True:
			try:
				_logger.debug("Requesting new posts")
				post_listings[subreddit_name] = []
				i = 0
				for post in subreddit.new(limit = _config["post_limit"]):
					# Posts are requested from Reddit 100 at a time, and need to rate limit each request.
					if i == 100:
						_logger.debug("Rate limiting")
						time.sleep(2)
						i = 0
					post_listings[subreddit_name].append(post)
					i += 1
				break
			# Failed to make a request to Reddit.
			except prawcore.exceptions.RequestException as e:
				_logger.warning("New post listings request failed: {}".format(repr(e)))
				if utility.check_internet_connection():
					utility.wait_for_reddit_available()
				else:
					utility.wait_for_internet_connection()
			# Unsuccessful HTTP status (>= 400 and < 600).
			except prawcore.exceptions.ResponseException as e:
				status = e.response.status_code
				_logger.warning("New post listings request failed: HTTP status {}".format(repr(status)))
				# Internal server error, service unavailable, or gateway timeout.
				if status in (500, 503, 504):
					utility.wait_for_reddit_available()
				# Other 4xx or 5xx errors; treated as unexpected and unrecoverable at this time.
				else:
					_logger.info("Skipping subreddit")
					break
			
		# Crude rate limit for Reddit API.
		_logger.debug("Rate limiting")
		time.sleep(2)

		
	for subreddit_name, posts in post_listings.items():
		''' Sort the posts by creation time, oldest to newest.
			Need to be sorted so that the post handler can work correctly (specifically, filtering out of previously handled posts).
			Reddit sometimes gives us unordered listings, even though we are supposed to be sorting by "new"! '''
		posts.sort(key = lambda p : p.created_utc)
		
	_logger.info("Post grabbing complete")
	return post_listings
