web: python manage.py migrate && gunicorn --bind 0.0.0.0:$PORT --worker-class daphne.server.Server nexus_project.asgi:application
