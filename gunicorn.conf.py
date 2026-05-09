# Gunicorn Configuration for Render
import multiprocessing
import os

# Worker settings
worker_class = 'eventlet' # Must match wsgi.py monkey_patch
workers = 1 # One worker is usually enough for SocketIO on free tier
timeout = 120 # Higher timeout for startup

# Log to stdout for Render
accesslog = '-'
errorlog = '-'

# Bind to 0.0.0.0:$PORT
port = os.environ.get('PORT', '10000')
bind = f'0.0.0.0:{port}'
