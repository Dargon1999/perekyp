from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from .config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    from .routes import main_routes
    app.register_blueprint(main_routes)

    # Logging Configuration
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        try:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/perekyp.log', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
        except Exception as e:
            app.logger.warning(f"Could not setup file logging: {e}")

        app.logger.setLevel(logging.INFO)
        app.logger.info('Perekyp startup')

    with app.app_context():
        # Run migrations before creating tables (or after, depending on logic)
        # db.create_all() will create tables if they don't exist.
        # We need to run migrations for existing tables.
        try:
            db.create_all()
            migrate_db(app)
        except Exception as e:
            app.logger.error(f"Database initialization/migration failed: {e}")

    return app

def migrate_db(app):
    """
    Checks for missing columns and adds them if necessary.
    This acts as a lightweight migration system.
    """
    from sqlalchemy import text, inspect
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # 1. Check Client table
        if inspector.has_table("client"):
            columns = [c['name'] for c in inspector.get_columns("client")]
            
            # Check for 'username'
            if "username" not in columns:
                app.logger.info("Migrating: Adding username to client")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE client ADD COLUMN username VARCHAR(100)"))
                    conn.commit()
            
            # Check for 'status'
            if "status" not in columns:
                app.logger.info("Migrating: Adding status to client")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE client ADD COLUMN status VARCHAR(20) DEFAULT 'Active'"))
                    conn.commit()

            # Check for 'user_id'
            if "user_id" not in columns:
                app.logger.info("Migrating: Adding user_id to client")
                with db.engine.connect() as conn:
                    # SQLite limitation: Adding FK is hard. Just add column for now.
                    # Ideally we would recreate table, but that risks data loss.
                    # We'll just add the column.
                    conn.execute(text("ALTER TABLE client ADD COLUMN user_id INTEGER"))
                    conn.commit()

        # 2. Check ServerSettings table
        if inspector.has_table("server_settings"):
            columns = [c['name'] for c in inspector.get_columns("server_settings")]
            # Add any future columns here if needed
            pass

