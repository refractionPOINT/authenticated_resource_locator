from setuptools import setup

__version__ = "1.0.0"
__author__ = "Maxime Lamothe-Brassard ( Refraction Point, Inc )"
__author_email__ = "maxime@refractionpoint.com"
__license__ = "Apache v2"
__copyright__ = "Copyright (c) 2019 Refraction Point, Inc"

setup( name = 'arl',
       version = __version__,
       description = 'Authenticated Resource Locator',
       url = 'https://limacharlie.io',
       author = __author__,
       author_email = __author_email__,
       license = __license__,
       packages = [ 'arl' ],
       zip_safe = True,
       install_requires = [ 'google-cloud-storage', 'requests', 'gevent' ],
       long_description = 'Authenticated Resource Locator to specify succintly a remote resource to get using many protocols.'
)
