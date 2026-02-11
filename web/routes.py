from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app, send_file
from . import db, socketio
from .models import User, Client, ServerSettings
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import hashlib
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
            settings = ServerSettings(current_version="7.2.1")
            db.session.add(settings)
            db.session.commit()
        # Auto-update version in DB if it's outdated
        elif settings.current_version in ["7.1.1", "7.1.2", "7.0.0", "7.2.0"]:
            settings.current_version = "7.2.1"
            db.session.commit()
        return settings
    except Exception as e:
        print(f"DB Error in get_server_settings: {e}")
        # Return a dummy object if DB is read-only or fails
        # We need an object with attributes: current_version, force_update
        class DummySettings:
            current_version = "7.2.1"
            force_update = False
        return DummySettings()

@main_routes.route('/update_info', methods=['GET'])
def update_info():
    settings = get_server_settings()
    base_url = request.url_root.rstrip('/')
    
    # Calculate signature if update file exists
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    update_dir = os.path.join(base_dir, UPDATE_FOLDER)
    file_path = os.path.join(update_dir, UPDATE_FILENAME)
    signature = None
    try:
        if os.path.exists(file_path):
            h = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            signature = h.hexdigest()
    except Exception as e:
        print(f"ERROR: Failed to compute signature: {e}")
        signature = None
    
    response = {
        "version": settings.current_version,
        "force_update": settings.force_update,
        "download_url": f"{base_url}/download",
        "notes": "Update available",
        "signature": signature
    }
    return jsonify(response)

@main_routes.route('/download')
def download_update():
    # Allow downloading either the main app or the updater
    filename = request.args.get('file', UPDATE_FILENAME)
    if filename not in [UPDATE_FILENAME, UPDATER_FILENAME]:
        filename = UPDATE_FILENAME
        
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    update_dir = os.path.join(base_dir, UPDATE_FOLDER)
    file_path = os.path.join(update_dir, filename)
    
    print(f"DEBUG: Trying to serve {filename} from {file_path}")
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        # Fallback: check if it's inside 'web' folder
        fallback_path = os.path.join(current_app.root_path, UPDATE_FOLDER, filename)
        if os.path.exists(fallback_path):
             return send_file(fallback_path, as_attachment=True)
             
        print(f"ERROR: File {filename} not found at {file_path} or {fallback_path}")
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
    try:
        # Allow access with session cookie OR secret header
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
        is_updater = request.form.get('is_updater', 'false').lower() == 'true'
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        if file:
            # Simplified path logic
            cwd = os.getcwd()
            update_dir = os.path.join(cwd, UPDATE_FOLDER)
            os.makedirs(update_dir, exist_ok=True)
            
            filename = UPDATER_FILENAME if is_updater else UPDATE_FILENAME
            save_path = os.path.join(update_dir, filename)
            
            print(f"DEBUG: Saving {'updater' if is_updater else 'main exe'} to {save_path} (CWD: {cwd})")
            file.save(save_path)
            
            # Update DB only for main app version
            if not is_updater and version:
                settings = get_server_settings()
                settings.current_version = version
                db.session.commit()
                return jsonify({"status": "ok", "version": version, "path": save_path})
            
            return jsonify({"status": "ok", "type": "updater" if is_updater else "main", "path": save_path})
        
        return jsonify({"error": "Missing file"}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

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
