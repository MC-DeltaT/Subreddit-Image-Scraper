import importlib
import json
import logging
import os
import requests
import sys
import uuid

import exit_signal_handler
import utility
import web_image_extractor



_logger = logging.getLogger()


_current_directory = os.path.dirname(os.path.realpath(__file__))
_config_path = os.path.join(sys.argv[1], "handler_config.json")
_config_schema_path = os.path.join(_current_directory, "handler_config_schema.json")
_state_path = os.path.join(sys.argv[1], "state.json")
_state_schema_path = os.path.join(_current_directory, "state_schema.json")


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

_logger.debug("Loading state schema from file")
try:
	_state_schema = utility.load_json(_state_schema_path)
except json.JSONDecodeError as e:
	_logger.error("JSON decode failed: {}".format(repr(e)))
	sys.exit(1)
except FileNotFoundError:
	_logger.error("State schema file not found")
	sys.exit(1)

_logger.info("Loading state from file")
try:
	_state = utility.load_json(_state_path)
except json.JSONDecodeError as e:
	_logger.error("JSON decode failed: {}".format(repr(e)))
	sys.exit(1)
except FileNotFoundError:
	_logger.info("State file not found")
	_state = dict()
	_state["latest_handled_times"] = dict()
	
_errors = utility.validate_json(_state, _state_schema)
if len(_errors) > 0:
	for _e in _errors:
		_logger.error(_e)
	sys.exit(1)


_image_extensions = { "image/jpeg": ".jpg",
				      "image/png": ".png" }


def _save_image(data, file_extension):
	while True:
		file_path = os.path.join(_config["output_directory"], uuid.uuid4().hex + file_extension)
		_logger.debug("Writing image to {}".format(file_path))

		try:
			file = open(file_path, "xb")
			file.write(data)
		except FileExistsError:
			_logger.warning("Image file open failed: file already exists")
			_logger.info("Retrying with new filename")
			continue
		file.close()
		break


''' Attempts to download the image at the given URL.
	Returns a tuple of the image data and the file extension.'''
def _download_image(url):
	_logger.debug("Requesting {}".format(url))
	res = requests.get(url, timeout = 4)
	res.raise_for_status()
	
	content_type = res.headers["content-type"]
	file_extension = _image_extensions.get(content_type)
	if file_extension is None:
		raise NotImplementedError("Unupported content type {}".format(content_type))

	return (res.content, file_extension)


def _time_filter(post, subreddit_name):
	if hasattr(post, "created_utc"):
		latest_handled_time = _state["latest_handled_times"].get(subreddit_name)
		if latest_handled_time is not None:
			if post.created_utc <= latest_handled_time:
				_logger.debug("Post handled by previous scrape")
				return False
	else:
		_logger.debug("Post has no creation time")
		return False
	
	return True


def _global_filter(post, subreddit_name):
	if hasattr(post, "stickied"):
		if post.stickied:
			_logger.debug("Post is a sticky")
			return False
	
	if hasattr(post, "url"):
		if not web_image_extractor.is_supported(post.url):
			_logger.debug("Post link not supported")
			return False
	else:
		_logger.debug("Post has no link")
		return False
		
	return True
	
	
def _subreddit_filter(post, subreddit_name):
	filter_path = _config["post_filters"].get(subreddit_name)
	if filter_path is not None:
		filter_dir, filter_name = os.path.split(filter_path)
		filter_name = os.path.splitext(filter_name)[0]
		if filter_dir not in sys.path:
			sys.path.append(filter_dir)
		
		_logger.debug("Running custom filter")
		return importlib.import_module(filter_name).filter(post, subreddit_name)
		
	return True
	
	
def _update_state(post, subreddit_name):
	_logger.debug("Updating state")
	_state["latest_handled_times"][subreddit_name] = post.created_utc
	
	_logger.debug("Storing state to file")
	file = open(_state_path, "w")
	json.dump(_state, file, indent = "\t")
	file.close()
	_logger.debug("State store complete")
	
	

# Handles a post given to us by main.py.
def handle(post, subreddit_name):
	if not _time_filter(post, subreddit_name):
		_logger.debug("Time filter not passed")
		_logger.debug("Skipping post")
		return
	
	update_state = True
	try:
		if not _global_filter(post, subreddit_name):
			_logger.debug("Global post filter not passed")
			_logger.debug("Skipping post")
			return
		if not _subreddit_filter(post, subreddit_name):
			_logger.debug("Subreddit-specific post filter not passed")
			_logger.debug("Skipping post")
			return
		
		while True:
			try:
				image_url = web_image_extractor.resolve(post.url)
				data, file_extension = _download_image(image_url)
				break
			# Exception we raise if the post links to an unsupported image type.
			except NotImplementedError as e:
				_logger.warning("Image download failed: {}".format(repr(e)))
				_logger.debug("Skipping post")
				return
			# Connection couldn't be made for some reason.
			except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
				''' Unfortunately there's not really any way to isolate exactly what went wrong.
					Most probable cause is our internet is disconnected. '''
			
				_logger.warning("Image download failed: {}".format(repr(e)))
				if utility.check_internet_connection():
					_logger.warning("Site unavailable")
					_logger.debug("Skipping post")
					return
				else:
					utility.wait_for_internet_connection()
			# Server returned an unsuccessful status code (>= 400).
			except requests.exceptions.HTTPError as e:
				_logger.warning("Image download failed: HTTP status {}".format(e.response.status_code))
				_logger.debug("Skipping post")
				return
			# Some other error from the requests module we aren't expecting nor able to handle.
			except requests.exceptions.RequestException as e:
				_logger.warning("Image download failed: {}".format(repr(e)))
				_logger.debug("Skipping post")
				return
		
		# If the image is written to the file, then the state file must also be updated before the application can exit.
		exit_signal_handler.block_signals()
		_save_image(data, file_extension)
	except Exception as e:
		_logger.warning("Intercepted unhandled exception")
		_logger.debug("Not updating state")
	
		# Don't want to update the state if some unhandled exception occurs, as we don't know what the condition the application is in.
		update_state = False
		
		raise e
	finally:
		''' State always gets updated once the post passes the time filter, whether or not the post gets skipped due to something else.
			Only other time the state doesn't get updated is if the handling fails with some unhandled exception, as mentioned above. '''
		if update_state:
			_update_state(post, subreddit_name)
		
		# Signals are always unblocked here for the event that they are previously blocked and then an unhandled exception occurs.
		exit_signal_handler.unblock_signals()
