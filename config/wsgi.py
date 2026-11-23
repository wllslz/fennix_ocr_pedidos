import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
_django_app = get_wsgi_application()

if os.environ.get("VERCEL") == "1":
    from django.core.management import call_command
    if not os.path.exists("/tmp/db.sqlite3"):
        call_command("migrate", interactive=False, verbosity=0)

def application(environ, start_response):
    if environ.get("PATH_INFO") == "/config/wsgi.py":
        environ["PATH_INFO"] = "/"
    return _django_app(environ, start_response)

app = application
