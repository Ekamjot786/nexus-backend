web: python manage.py migrate && python -c "import nexus_project.asgi; print('ASGI import OK')" && exec daphne -b 0.0.0.0 -p $PORT nexus_project.asgi:application
