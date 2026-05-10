from datetime import datetime
from flask_login import UserMixin
from . import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    clients = db.relationship('Client', backref='owner', lazy=True)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.full_name}', '{self.email}')"

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(100), unique=True, nullable=False) # HWID or UUID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    hwid = db.Column(db.String(100), nullable=True)
    version = db.Column(db.String(20), nullable=False)
    last_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Active') # Active, Offline, Banned
    license_expiry = db.Column(db.DateTime, nullable=True) # None means Lifetime
    
    def __repr__(self):
        return f"Client('{self.client_id}', '{self.version}', '{self.last_seen}')"

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    admin_username = db.Column(db.String(100))
    action = db.Column(db.String(200))
    client_id = db.Column(db.String(100))
    details = db.Column(db.Text)

class ServerSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_version = db.Column(db.String(20), default="1.0.4")
    stable_version = db.Column(db.String(20), default="1.0.3")
    priority_version = db.Column(db.String(20), default="stable") # 'stable' or 'latest'
    force_update = db.Column(db.Boolean, default=False)
    download_url = db.Column(db.String(200), default="/download")
    
    # Audit Log for Updates
    last_upload_size = db.Column(db.BigInteger)
    last_upload_hash = db.Column(db.String(100))
    last_upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_upload_notes = db.Column(db.Text)
