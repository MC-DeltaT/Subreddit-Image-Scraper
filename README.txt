Subreddit Image Scraper
by Reece Jones


Contents:
	Purpose
	Usage
	Requirements
	Python dependencies
	Files in project
	Configuration
	Persistent state
	Post filtering
	Image support


Purpose:
	This application gets new posts from subreddits and saves the posts' linked images.
	It is designed to be a scheduled task, such as by cron.


Usage:
	<python_command> main.py <config_dir> <log_path>
	
	<python_command> - the command that invokes Python, e.g. python3.
	<config_dir> - path to a directory that contains the configuration and state files.
	<log_path> - path to the log file that will be written to.


Requirements:
	Python 3, at least version 3.5 - tested on versions 3.5 and 3.7.
	Linux - tested and built for Linux, should work on other Unix-like systems, and mostly works on Windows (signal handling doesn't fully work).


Python dependencies:
	jsonschema
	praw (and prawcore)
	requests


Files in project:
	exit_signal_handler.py			- signal handling.
	general_config_schema.json		- JSON schema for general config file.
	grabber_config_schema.json		- JSON schema for post grabber config file.
	handler_config_schema.json		- JSON schema for post handler config file.
	main.py							- main module.
	post_grabber.py					- acquires posts from Reddit.
	post_handler.py					- filters posts and downloads images.
	README.txt						- this readme file.
	state_schema.json				- JSON schema for the state file.
	utility.py						- miscellaneous program utilities.
	web_image_extractor.py			- resolves image hosting site links to image URLs.


Configuration:
	The application's configuration is split into three files, which are user-provided and required for the application to work. Data in them is
	stored in the JSON format. The files are expected to be located within the directory specified by the <config_dir> command line argument, and are
	as follows:
		general_config.json:
			General program configuration. Required properties are:
				time_limit - a number specifying a cap to the application's execution time, in seconds.
		grabber_config.json:
			Configuration pertaining to the acquiring of posts from Reddit. Required properties are:
				client_id - a string specifying the client ID for the account which is to be used to itneract with the Reddit API.
				client_secret - a string specifying the client secret for the account which is to be used to itneract with the Reddit API.
				user agent - a string specifying the user agent for interacting with the Reddit API.
				post_limit - a number specifying the maximum number of new posts to get from each subreddit.
				subreddits - an array of strings specifying the names of the subreddits to get posts from.
		handler_config.json:
			Configuration pertaining to the handling of posts. Required properties are:
				output_directory - a string specifying the path of the directory to save the downloaded images to. If it is a relative path, it is
								   relative to <config_dir>.
				post_filters - an object mapping a subreddit name to a string specfying the path of a Python module to be used as a post filter for
							   that subreddit (see section "Post filtering" for more info). If a path is a relative path, it is relative to
							   <config_dir>.
	For a more formal description of the required data read the respective _schema.json files, which are used by the application to validate the
	configuration data.


Persistent state:
	The application stores its internal state to file, which, if provided on a next execution, allows it to skip posts already handled by a previous
	execution. The filename is state.json, and is searched for in the <config_dir> directory. The format is JSON. The required properties are:
		latest_handled_times - an object mapping a subreddit name to a number specifying the creation time as UNIX time of the latest post handled in
							   that subreddit.
	For a more formal description of the required data read state_schema.json, which is used by the application to validate the state data.
	If the state file is not found at startup of the application, it will be created. It will be assumed that no post has been previously handled. The
	application will then update its state to this file as usual.
	If the state file is found and is valid, then the application will use and update it as its state.
	Usually the user does not need to, and shouldn't, modify this file.


Post filtering:
	The application filters out posts to skip unwanted/unprocessable ones. By default, it skips posts that have already been handled, stickied posts,
	and posts with no link.
	Additional custom filters that are only applied to posts from a specific subreddit can be configured by the user. These are in the form of a
	Python source file with a function named "filter". This function should accept the post as its first argument, and the subreddit's name as its
	second argument. It should return True if the post passes the filter or False if the post fails the filter.
	For specifying the filters to the application, see the handler_config.json specification in the "Configuration" section.


Image support:
	The supported domains for posts' links are currently i.redd.it and i.imgur.com. If a post's link is to an unsupported domain, it is skipped.
	The supported image types are currently JPEG and PNG. If a post links to an unsupported image type, it is skipped.
