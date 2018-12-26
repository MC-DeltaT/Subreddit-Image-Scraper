import datetime
import json
import logging
import os
import signal
import sys
import threading



def time_limit_exit():
	logger.info("Time limit reached")
	logger.debug("Sending SIGTERM")
	os.kill(os.getpid(), signal.SIGTERM)


try:
	if len(sys.argv) < 3:
		print("Too few command line arguments")
		sys.exit(2)
	elif len(sys.argv) > 3:
		print("Too many command line arguments")
		sys.exit(2)

	logging.basicConfig(filename = sys.argv[2], filemode = "w", format = "[%(asctime)s %(filename)s:%(lineno)s, %(funcName)s] %(levelname)s: %(message)s")
	logger = logging.getLogger()
	logger.setLevel(logging.NOTSET)


	import utility

	current_directory = os.path.dirname(os.path.realpath(__file__))
	config_path = os.path.join(sys.argv[1], "general_config.json")
	config_schema_path = os.path.join(current_directory, "general_config_schema.json")

	logger.debug("Loading configuration schema from file")
	try:
		config_schema = utility.load_json(config_schema_path)
	except json.JSONDecodeError as e:
		logger.error("JSON decode failed: {}".format(repr(e)))
		sys.exit(1)
	except FileNotFoundError:
		logger.error("Configuration schema file not found")
		sys.exit(1)

	logger.info("Loading configuration from file")
	try:
		config = utility.load_json(config_path)
	except json.JSONDecodeError as e:
		logger.error("JSON decode failed: {}".format(repr(e)))
		sys.exit(1)
	except FileNotFoundError:
		logger.error("Configuration file not found")
		sys.exit(1)
	
	errors = utility.validate_json(config, config_schema)
	if len(errors) > 0:
		for e in errors:
			logger.error(e)
		sys.exit(1)
	

	import post_grabber
	import post_handler
	

	# Set up a SIGTERM to be sent to limit the application to the configured maximum run time.
	logger.info("Scrape is limited to {} seconds ({})".format(config["time_limit"],
														(datetime.datetime.now() + datetime.timedelta(seconds = config["time_limit"])).strftime("%Y/%m/%d %H:%M:%S")))
	exit_timer = threading.Timer(config["time_limit"], time_limit_exit)
	exit_timer.start()


	try:
		post_listings = post_grabber.grab()

		for subreddit_name, posts in post_listings.items():
			logger.info('Handling posts in subreddit "{}"'.format(subreddit_name))
			
			for post in posts:
				post_handler.handle(post, subreddit_name)

		logger.info("Scrape completed")
	finally:
		exit_timer.cancel()
except Exception as e:
	logger.critical("Unhandled exception: {}".format(repr(e)), exc_info = True)
finally:
	logger.info("Exiting")
	logging.shutdown()