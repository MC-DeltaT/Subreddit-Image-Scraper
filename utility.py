import json
import jsonschema
import logging
import requests
import socket
import time



_logger = logging.getLogger()


''' Checks if an internet connection is available by connecting to 8.8.8.8.
	Returns True if the connection succeeds.
	Returns False otherwise. '''
def check_internet_connection(timeout = 4):
	_logger.debug("Checking for an internet connection")
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(timeout)
		sock.connect(("8.8.8.8", 53))
		try:
			sock.close()
		except OSError:
			pass
			
		_logger.debug("Internet connection available")
		return True
	except OSError:
		_logger.debug("Internet connection not available")
		return False
		

''' Checks if Reddit (https://www.reddit.com) services are available.
	Returns True if the request is successfully made and the response status is < 400.
	Returns False if the request is successfully made and the response status is >= 500 and < 600.
	Raises exceptions as per a requests.get() call. '''
def check_reddit_availability():
	_logger.debug("Checking Reddit availability")
	res = requests.get("https://www.reddit.com", timeout = 4)
	
	if res.status_code < 400:
		_logger.debug("Reddit available")
		return True
	elif 500 <= res.status_code < 600:
		_logger.debug("Reddit unavailable")
		return False
	# 400 <= res.status_code < 500
	else:
		res.raise_for_status()


# Reads and parses a JSON file.
def load_json(path):
	file = open(path, "r")
	try:
		return json.load(file)
	finally:
		file.close()
		
		
''' Validates a JSON instance against a schema.
	Returns a list of error messages for each invalidity (empty list if no errors). '''
def validate_json(instance, schema):
	jsonschema.Draft4Validator.check_schema(schema)
	validator = jsonschema.Draft4Validator(schema)
	errors = sorted(validator.iter_errors(instance), key = lambda e : e.absolute_path)
	return list(map(lambda e : "JSON not valid by schema: at property {}: {}".format("/" + "/".join(map(str, e.absolute_path)), e.message), errors))


# Waits until an internet connection is available.
def wait_for_internet_connection(check_interval = 60):
	_logger.info("Waiting for an internet connection")
	while not check_internet_connection():
		_logger.debug("Sleeping for {} seconds".format(check_interval))
		time.sleep(check_interval)

		
''' Waits for Reddit (https://www.reddit.com) to be available.
	Raises exceptions as per a requests.get() call if a request fails. '''
def wait_for_reddit_available(check_interval = 600):
	_logger.info("Waiting for Reddit to be available")
	while True:
		try:
			while not check_reddit_availability():
				_logger.debug("Sleeping for {} seconds".format(check_interval))
				time.sleep(check_interval)
			break
		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
			_logger.debug("Reddit availability request failed: {}".format(repr(e)))
			if not check_internet_connection():
				wait_for_internet_connection()
