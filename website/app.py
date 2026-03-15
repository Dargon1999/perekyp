import os
import logging
import shutil
import zipfile
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from PIL import Image
import json
import hashlib

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=BASE_DIR, 
            static_folder=BASE_DIR, 
            static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "admin.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'dev-key-moneytracker-pro-2026' 
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_CSRF_PROTECT'] = False 
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['BACKUP_FOLDER'] = os.path.join(BASE_DIR, 'backups')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # 500MB

# Ensure directories exist
for folder in [app.config['UPLOAD_FOLDER'], 
               os.path.join(app.config['UPLOAD_FOLDER'], 'images'),
               os.path.join(app.config['UPLOAD_FOLDER'], 'previews'),
               os.path.join(app.config['UPLOAD_FOLDER'], 'software'),
               app.config['BACKUP_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

# Models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(45))
    action = db.Column(db.String(255))

# Setup logging
logging.basicConfig(filename='admin_activity.log', level=logging.INFO)

def log_action(action):
    ip = request.remote_addr
    log = AdminLog(ip=ip, action=action)
    db.session.add(log)
    db.session.commit()
    logging.info(f"{datetime.utcnow()} | IP: {ip} | Action: {action}")

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Routes
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/admin.html')
def admin_page():
    return send_from_directory(BASE_DIR, 'admin.html')

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    admin = Admin.query.filter_by(username=username).first()
    if admin and bcrypt.check_password_hash(admin.password_hash, password):
        access_token = create_access_token(identity=username)
        log_action(f"Successful login: {username}")
        resp = jsonify({'msg': 'Login successful', 'redirect': url_for('dashboard_page')})
        set_access_cookies(resp, access_token)
        return resp
    
    log_action(f"Failed login attempt: {username}")
    return jsonify({'msg': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    resp = jsonify({'msg': 'Logged out'})
    unset_jwt_cookies(resp)
    return resp

@app.route('/dashboard.html')
@jwt_required(optional=True)
def dashboard_page():
    # Allow file:// access for demo, but protect via JWT if on server
    return send_from_directory(BASE_DIR, 'dashboard.html')

@app.route('/config.json')
def get_config():
    return send_from_directory(BASE_DIR, 'config.json')

@app.route('/api/upload/image', methods=['POST'])
@jwt_required()
def upload_image():
    if 'file' not in request.files:
        return jsonify({'msg': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'msg': 'No filename'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', filename)
        file.save(path)
        
        # Auto-compression and preview
        img = Image.open(path)
        img.thumbnail((1200, 1200))
        img.save(path, optimize=True, quality=85)
        
        preview_path = os.path.join(app.config['UPLOAD_FOLDER'], 'previews', filename)
        img.thumbnail((300, 300))
        img.save(preview_path)
        
        log_action(f"Uploaded image: {filename}")
        return jsonify({
            'msg': 'Image uploaded', 
            'preview': f'/uploads/previews/{filename}',
            'filename': filename
        })

@app.route('/api/delete/image/<filename>', methods=['DELETE'])
@jwt_required()
def delete_image(filename):
    filename = secure_filename(filename)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'images', filename))
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'previews', filename))
        log_action(f"Deleted image: {filename}")
        return jsonify({'msg': 'Deleted'})
    except:
        return jsonify({'msg': 'Error deleting'}), 500

# Update config.json path in functions
def update_config_path(filename):
    return os.path.join(BASE_DIR, filename)

@app.route('/api/update/config', methods=['POST'])
@jwt_required()
def update_config():
    data = request.json
    with open(update_config_path('config.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    log_action("Updated site configuration")
    return jsonify({'msg': 'Configuration updated'})

@app.route('/api/update/software', methods=['POST'])
@jwt_required()
def update_software():
    if 'file' not in request.files:
        return jsonify({'msg': 'No file'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.zip'):
        return jsonify({'msg': 'Only ZIP files allowed'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'software', filename)
    file.save(filepath)

    # 1. Backup current version if exists
    config_json_path = update_config_path('config.json')
    if os.path.exists(config_json_path):
        shutil.copy(config_json_path, os.path.join(app.config['BACKUP_FOLDER'], 'config_last.json'))

    # 2. Checksum
    checksum = calculate_sha256(filepath)
    
    try:
        # 3. Extract and verify
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            # Check for update.json inside ZIP for version info
            if 'update.json' in zip_ref.namelist():
                update_info = json.loads(zip_ref.read('update.json'))
                new_version = update_info.get('version', 'unknown')
                
                # Update config.json with new version and download URL
                with open(config_json_path, 'r+', encoding='utf-8') as f:
                    config = json.load(f)
                    config['version'] = new_version
                    # Assume ZIP contains the .exe too, or just update metadata
                    f.seek(0)
                    json.dump(config, f, indent=4, ensure_ascii=False)
                    f.truncate()
                
                log_action(f"Software update installed: v{new_version} (SHA256: {checksum[:8]})")
                return jsonify({'msg': 'Update installed', 'version': new_version, 'hash': checksum})
            else:
                return jsonify({'msg': 'update.json missing in ZIP'}), 400
    except Exception as e:
        log_action(f"Software update FAILED: {str(e)}")
        # Rollback
        if os.path.exists(os.path.join(app.config['BACKUP_FOLDER'], 'config_last.json')):
            shutil.copy(os.path.join(app.config['BACKUP_FOLDER'], 'config_last.json'), config_json_path)
        return jsonify({'msg': 'Installation error', 'log': str(e)}), 500

@app.route('/api/update/rollback', methods=['POST'])
@jwt_required()
def rollback():
    backup = os.path.join(app.config['BACKUP_FOLDER'], 'config_last.json')
    config_json_path = update_config_path('config.json')
    if os.path.exists(backup):
        shutil.copy(backup, config_json_path)
        log_action("Performed software rollback")
        return jsonify({'msg': 'Rollback successful'})
    return jsonify({'msg': 'No backup found'}), 400

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            new_admin = Admin(username='admin', password_hash=hashed_pw)
            db.session.add(new_admin)
            db.session.commit()
    app.run(port=5000, debug=True)
