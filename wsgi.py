from gevent import monkey
monkey.patch_all()

import logging
import sys

# Setup Logging for Render
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("WSGI")

logger.info("--- Gunicorn WSGI Startup Init ---")

try:
    from web import create_app, socketio
    logger.info("Successfully imported web module")
    
    app = create_app()
    logger.info("Successfully created Flask app instance")
    
    # Render's Gunicorn will look for 'app' in 'wsgi:app'
    # But for SocketIO to work with Gunicorn correctly,
    # it's better if gunicorn manages it via eventlet
    # The 'app' variable is what gunicorn will bind to.
    
except Exception as e:
    logger.critical(f"CRITICAL ERROR during app startup: {e}")
    import traceback
    logger.critical(traceback.format_exc())
    raise
