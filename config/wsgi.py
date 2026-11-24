import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
_django_app = get_wsgi_application()

def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    if not path or path == "/config/wsgi.py":
        environ["PATH_INFO"] = "/"
    return _django_app(environ, start_response)

app = application
