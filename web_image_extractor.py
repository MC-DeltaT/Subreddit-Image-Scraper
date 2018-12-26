'''
	web_image_extractor.py

	This module provides functionality to uniformly access images from links to images on common image hosting sites/domains.

	Currently supported sites/domains:
		i.redd.it (link is directly to image file)
		i.imgur.com (link is directly to image file)
'''



import urllib

	

# Handles an i.redd.it URL.
def _i_redd_it_handler(url):
	# URL is directly to image file.
	return url

# Handles an i.imgur.com URL.
def _i_imgur_com_handler(url):
	# URL is directly to image file.
	return url
	
	
# Mapping from URL domains to specific domain handlers.
_url_handlers = { "i.redd.it":   _i_redd_it_handler,
				  "i.imgur.com": _i_imgur_com_handler }

	
''' Resolves the given image link to a URL to the image itself.
	ValueError if url is invalid or not to a supported image hosting domain.
	If the resolution requires addition network requests, exceptions may be raised as per the requests module. '''
def resolve(url):
	domain = urllib.parse.urlparse(url).hostname
	
	if domain is None:
		raise ValueError("URL does not have a domain")
	
	url_handler = _url_handlers.get(domain)
	
	if url_handler is None:
		raise ValueError("URL domain not supported")
	else:
		return url_handler(url)

		
# Returns True if url is valid and is to a supported image domain, otherwise returns False.
def is_supported(url):
	try:
		domain = urllib.parse.urlparse(url).hostname
	except ValueError:
		# URL specifies an invalid port number.
		return False
	
	return domain in _url_handlers
