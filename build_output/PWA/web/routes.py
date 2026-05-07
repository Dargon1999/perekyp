from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app, send_file
from . import db, socketio
from .models import User, Client, ServerSettings
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import hashlib

main_routes = Blueprint('main', __name__)

# --- Update Server Logic ---
UPDATE_FOLDER = "updates"
UPDATE_FILENAME = "MoneyTracker.exe"
UPDATER_FILENAME = "updater.exe"

def get_server_settings():
    try:
        settings = ServerSettings.query.first()
        if not settings:
            settings = ServerSettings(current_version="1.0.0")
            db.session.add(settings)
            db.session.commit()
        # Auto-update version in DB if it's outdated
        elif settings.current_version in ["7.1.1", "7.1.2", "7.0.0", "7.2.0", "7.2.1", "9.0.0", "9.0.1", "9.3.0"]:
            settings.current_version = "1.0.0"
            db.session.commit()
        return settings
    except Exception as e:
        current_app.logger.error(f"DB Error in get_server_settings: {e}")
        # Return a dummy object if DB is read-only or fails
        # We need an object with attributes: current_version, force_update
        class DummySettings:
            current_version = "1.0.0"
            force_update = False
        return DummySettings()

@main_routes.route('/update_info', methods=['GET'])
def update_info():
    settings = get_server_settings()
    base_url = request.url_root.rstrip('/')
    
    # Calculate metadata on the fly for the response
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    update_dir = os.path.join(base_dir, UPDATE_FOLDER)
    file_path = os.path.join(update_dir, UPDATE_FILENAME)
    
    signature = None
    file_size = 0
    pub_date = None
    
    try:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            pub_date = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            h = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            signature = h.hexdigest()
    except Exception as e:
        current_app.logger.error(f"Metadata calculation failed: {e}")
    
    # Use calculated metadata if available, otherwise fallback to DB
    final_signature = signature or settings.last_upload_hash
    final_size = file_size or settings.last_upload_size
    final_date = pub_date or (settings.last_upload_date.isoformat() if settings.last_upload_date else None)
    final_notes = settings.last_upload_notes or "Update highly recommended for stability and new features."
    
    return jsonify({
        "version": settings.current_version,
        "force_update": settings.force_update,
        "download_url": f"{base_url}/download",
        "signature": final_signature,
        "size": final_size,
        "publish_date": final_date,
        "notes": final_notes
    })

@main_routes.route('/download')
def download_update():
    # Allow downloading either the main app or the updater
    filename = request.args.get('file', UPDATE_FILENAME)
    if filename not in [UPDATE_FILENAME, UPDATER_FILENAME]:
        filename = UPDATE_FILENAME
        
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    update_dir = os.path.join(base_dir, UPDATE_FOLDER)
    file_path = os.path.join(update_dir, filename)
    
    current_app.logger.info(f"Serving update file: {filename}")
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        # Fallback: check if it's inside 'web' folder
        fallback_path = os.path.join(current_app.root_path, UPDATE_FOLDER, filename)
        if os.path.exists(fallback_path):
             return send_file(fallback_path, as_attachment=True)
             
        current_app.logger.error(f"File {filename} not found at {file_path} or {fallback_path}")
        return jsonify({"error": f"File {filename} not found."}), 404

@main_routes.route('/api/force_update', methods=['POST'])
def force_update():
    # Allow access with session cookie OR secret header
    is_admin = current_user.is_authenticated
    if not is_admin:
        secret = request.headers.get('X-Admin-Key')
        if secret == 'dargon_admin_secret_2024':
            is_admin = True
    
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    settings = get_server_settings()
    data = request.json
    if data and 'force' in data:
        settings.force_update = bool(data['force'])
    else:
        settings.force_update = not settings.force_update
        
    db.session.commit()
    return jsonify({"status": "ok", "force_update": settings.force_update})

@main_routes.route('/api/set_version', methods=['POST'])
@login_required
def set_version():
    data = request.json
    version = data.get('version')
    if version:
        settings = get_server_settings()
        settings.current_version = version
        db.session.commit()
        return jsonify({"status": "ok", "version": settings.current_version})
    return jsonify({"error": "Missing version"}), 400

@main_routes.route('/api/upload_update', methods=['POST'])
def upload_update():
    """Secure API for uploading a new version with metadata auto-generation."""
    try:
        # Authorization check (Admin key or Session)
        is_admin = current_user.is_authenticated
        if not is_admin:
            secret = request.headers.get('X-Admin-Key')
            if secret == 'dargon_admin_secret_2024':
                is_admin = True
                
        if not is_admin:
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['file']
        version = request.form.get('version')
        notes = request.form.get('notes', 'New update available')
        force = request.form.get('force', 'false').lower() == 'true'
        
        if file.filename == '' or not version:
            return jsonify({"error": "Missing file or version"}), 400
            
        # 1. Save File
        cwd = os.getcwd()
        update_dir = os.path.join(cwd, UPDATE_FOLDER)
        os.makedirs(update_dir, exist_ok=True)
        
        save_path = os.path.join(update_dir, UPDATE_FILENAME)
        file.save(save_path)
        
        # 2. Auto-generate Metadata
        h = hashlib.sha256()
        file_size = os.path.getsize(save_path)
        with open(save_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        signature = h.hexdigest()
        
        # 3. Update DB Settings
        settings = get_server_settings()
        settings.current_version = version
        settings.force_update = force
        settings.last_upload_size = file_size
        settings.last_upload_hash = signature
        settings.last_upload_date = datetime.utcnow()
        settings.last_upload_notes = notes
        
        db.session.commit()
        
        current_app.logger.info(f"New version {version} uploaded. Size: {file_size}, Hash: {signature}")
        
        return jsonify({
            "status": "ok", 
            "version": version, 
            "hash": signature,
            "size": file_size,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"Upload failed: {e}")
        return jsonify({"error": str(e)}), 500

@main_routes.route('/client_checkin', methods=['POST'])
def client_checkin():
    data = request.json
    client_id = data.get('client_id')
    version = data.get('version')
    username = data.get('username', 'Unknown')
    
    # Debug logging
    print(f"[Checkin] Received: ID={client_id}, Ver={version}, User={username}")
    
    if client_id:
        client = Client.query.filter_by(client_id=client_id).first()
        user = User.query.filter_by(username=username).first()
        
        if client:
            client.version = version
            client.username = username
            client.last_seen = datetime.utcnow()
            client.ip_address = request.remote_addr
            client.status = data.get('status', 'Active')
            if user:
                client.owner = user
        else:
            client = Client(client_id=client_id, version=version, username=username, ip_address=request.remote_addr, status=data.get('status', 'Active'))
            if user:
                client.owner = user
            db.session.add(client)
        
        try:
            db.session.commit()
            print(f"[Checkin] Success: Client {client_id} updated to version {version}")
            
            # Broadcast to all connected clients via WebSocket
            socketio.emit('client_update', {
                "client_id": client.client_id,
                "username": client.username,
                "version": client.version,
                "last_seen": client.last_seen.isoformat(),
                "ip": client.ip_address,
                "status": client.status
            })
            
        except Exception as e:
            print(f"[Checkin] DB Error: {e}")
            db.session.rollback()
            return jsonify({"error": "Database error"}), 500
            
        return jsonify({"status": "ok", "message": "Check-in successful"})
    return jsonify({"error": "Missing client_id"}), 400

# --- Web Dashboard Logic ---

@main_routes.route("/")
@main_routes.route("/home")
def home():
    return render_template('home.html')

@main_routes.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('main.register'))
            
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Аккаунт создан! Теперь вы можете войти', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('register.html')

@main_routes.route('/api/update-resource', methods=['POST'])
def update_resource():
    """REST API to update a resource from a source (path or URL)."""
    # Authorization
    is_admin = current_user.is_authenticated
    if not is_admin:
        secret = request.headers.get('X-Admin-Key')
        if secret == 'dargon_admin_secret_2024':
            is_admin = True
    
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    source = data.get('source')
    filename = data.get('filename', UPDATE_FILENAME)
    
    if not source:
        return jsonify({"error": "Parameter 'source' is required"}), 400

    try:
        # If source is a URL, download it
        if source.startswith(('http://', 'https://')):
            resp = requests.get(source, timeout=30, stream=True)
            if resp.status_code != 200:
                return jsonify({"error": f"Failed to download from source: {resp.status_code}"}), 409
            
            cwd = os.getcwd()
            update_dir = os.path.join(cwd, UPDATE_FOLDER)
            os.makedirs(update_dir, exist_ok=True)
            save_path = os.path.join(update_dir, filename)
            
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return jsonify({"status": "success", "message": f"Resource updated from URL to {filename}"}), 200
            
        # If source is a local path (on the server side)
        elif os.path.exists(source):
            cwd = os.getcwd()
            update_dir = os.path.join(cwd, UPDATE_FOLDER)
            os.makedirs(update_dir, exist_ok=True)
            save_path = os.path.join(update_dir, filename)
            
            shutil.copy2(source, save_path)
            return jsonify({"status": "success", "message": f"Resource updated from local path to {filename}"}), 200
        else:
            return jsonify({"error": f"Source path not found: {source}"}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error in update-resource: {e}")
        return jsonify({"error": str(e)}), 500

@main_routes.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            
    return render_template('login.html')

@main_routes.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main_routes.route("/dashboard")
@login_required
def dashboard():
    clients = Client.query.order_by(Client.last_seen.desc()).all()
    settings = get_server_settings()
    return render_template('dashboard.html', clients=clients, settings=settings)

@main_routes.route("/sync")
@login_required
def sync():
    return render_template('sync.html')

@main_routes.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow()})

@main_routes.route('/api/clients')
def api_clients():
    # Allow access with session cookie OR secret header
    is_admin = current_user.is_authenticated
    is_gui_client = False
    
    if not is_admin:
        secret = request.headers.get('X-Admin-Key')
        if secret == 'dargon_admin_secret_2024': # Hardcoded secret for GUI client
            is_gui_client = True
            is_admin = True
    
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    if is_gui_client:
        # GUI client gets everything
        clients = Client.query.order_by(Client.last_seen.desc()).all()
    else:
        # Web Dashboard User - Show ALL clients to authenticated users (Admin view)
        # Consistent with dashboard() route which shows all clients
        clients = Client.query.order_by(Client.last_seen.desc()).all()

    data = [{
        "client_id": c.client_id,
        "username": c.username,
        "version": c.version,
        "last_seen": c.last_seen.isoformat(),
        "ip": c.ip_address,
        "status": c.status
    } for c in clients]
    return jsonify(data)
