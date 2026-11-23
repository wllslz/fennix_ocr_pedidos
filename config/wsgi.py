import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

if os.environ.get("VERCEL") == "1":
    from django.core.management import call_command
    if not os.path.exists("/tmp/db.sqlite3"):
        call_command("migrate", interactive=False, verbosity=0)

app = application
