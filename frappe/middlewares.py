# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
import os
from werkzeug.exceptions import NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.wrappers import Request
from frappe.utils import get_site_name, cstr
from PIL import Image
from datetime import datetime
from tempfile import TemporaryFile
from mimetypes import guess_type

#@todo: handle missing query params, defaults, requests with only height or only weight
#@todo: handle animated GIFs : currently animated GIFs get converted to single frame, test more types
#@todo: move resizing code
#@todo: add scale, quality, optimize options
def get_resized_image(environ, filename):
	query_params = Request(environ).args
	query_param_keys = query_params
	height = query_params.get('height', default=1080, type=int)
	width = query_params.get('width', default=1920, type=int)
	image = Image.open(filename)
	img_format = image.format
	size = width, height
	image.thumbnail(size, Image.LANCZOS)
	temp_file = TemporaryFile()
	image.save(temp_file, format=img_format)
	temp_file.seek(0)
	return temp_file

class StaticDataMiddleware(SharedDataMiddleware):
	def __call__(self, environ, start_response):
		self.environ = environ
		return super(StaticDataMiddleware, self).__call__(environ, start_response)

	def _opener(self, filename):
		mimetype = guess_type(filename)[0]
		is_image = mimetype.startswith("image/")
		if is_image:
			opened_file = get_resized_image(self.environ, filename)
		else:
			opened_file = open(filename, 'rb')
		return lambda: (
            opened_file,
            datetime.utcfromtimestamp(os.path.getmtime(filename)),
            int(os.path.getsize(filename)) #filesize not accurate
        )

	def get_directory_loader(self, directory):
		def loader(path):
			site = get_site_name(frappe.app._site or self.environ.get('HTTP_HOST'))
			path = os.path.join(directory, site, 'public', 'files', cstr(path))
			if os.path.isfile(path):
				return os.path.basename(path), self._opener(path)
			else:
				raise NotFound
				# return None, None

		return loader
