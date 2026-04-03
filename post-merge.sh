#!/bin/sh
# Copy this file to .git/hooks/post-merge on PythonAnywhere and chmod +x it
# It touches the WSGI file to trigger an app reload after every git pull
touch /var/www/yourusername_pythonanywhere_com_wsgi.py  # ← update with your username
