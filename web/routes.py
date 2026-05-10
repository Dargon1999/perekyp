from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app, send_file
from . import db, socketio
from .models import User, Client, ServerSettings, AdminLog
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import hashlib
import requests
import shutil
import secrets

main_routes = Blueprint('main', __name__)

# Global command queue for clients (client_id -> [commands])
PENDING_COMMANDS = {}

# Firestore Config for License Management
FIREBASE_API_KEY = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
FIREBASE_PROJECT_ID = "generatormail-e478c"
FIREBASE_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

def log_admin_action(action, client_id, details=""):
    try:
        log = AdminLog(
            admin_username=current_user.username if current_user.is_authenticated else "System",
            action=action,
            client_id=client_id,
            details=details
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log admin action: {e}")

# --- Update Server Logic ---
UPDATE_FOLDER = "updates"
UPDATE_FILENAME = "MoneyTracker.exe"
UPDATER_FILENAME = "updater.exe"

def get_server_settings():
    try:
        settings = ServerSettings.query.first()
        if not settings:
            settings = ServerSettings(current_version="1.0.4")
            db.session.add(settings)
            db.session.commit()
        return settings
    except Exception as e:
        current_app.logger.error(f"DB Error in get_server_settings: {e}")
        # Return a dummy object if DB is read-only or fails
        class DummySettings:
            current_version = "1.0.4"
            force_update = False
            last_upload_hash = None
            last_upload_size = 0
            last_upload_date = datetime.utcnow()
            last_upload_notes = "Update highly recommended."
        return DummySettings()

@main_routes.route('/update_info', methods=['GET'])
def update_info():
    """
    Returns update metadata. Supports priority versioning (stable vs latest).
    """
    settings = get_server_settings()
    base_url = request.url_root.rstrip('/')
    
    # Determine which version to serve based on priority
    # If priority is 'stable', we serve stable_version
    # If priority is 'latest', we serve current_version
    target_version = settings.stable_version if settings.priority_version == 'stable' else settings.current_version
    
    # Use metadata from DB (populated during upload)
    final_signature = settings.last_upload_hash
    final_size = settings.last_upload_size
    final_date = settings.last_upload_date.isoformat() if settings.last_upload_date else None
    final_notes = settings.last_upload_notes or "Update highly recommended for stability and new features."
    
    return jsonify({
        "version": target_version,
        "force_update": settings.force_update,
        "download_url": f"{base_url}/download",
        "signature": final_signature,
        "size": final_size,
        "publish_date": final_date,
        "notes": final_notes,
        "priority": settings.priority_version
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

@main_routes.route('/api/force_hotfix', methods=['POST'])
@login_required
def force_hotfix():
    """
    Forces an update for clients even if their version matches.
    Useful for distributing fixes within the same version number.
    """
    try:
        settings = get_server_settings()
        
        # 1. Recalculate hash of the current update file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        update_dir = os.path.join(base_dir, UPDATE_FOLDER)
        file_path = os.path.join(update_dir, UPDATE_FILENAME)
        
        if os.path.exists(file_path):
             h = hashlib.sha256()
             with open(file_path, 'rb') as f:
                 for chunk in iter(lambda: f.read(8192), b''):
                     h.update(chunk)
             new_hash = h.hexdigest()
             file_size = os.path.getsize(file_path)
             
             settings.last_upload_hash = new_hash
             settings.last_upload_size = file_size
             settings.last_upload_date = datetime.utcnow()
             
             db.session.commit()
             log_admin_action("Force Hotfix", "All", f"Manifest updated. Hash: {new_hash[:8]}...")
             return jsonify({"status": "ok", "msg": "Хотфикс успешно запущен. Манифест обновлен на основе текущего файла."})
        else:
             return jsonify({"error": "Файл обновления не найден на сервере. Сначала загрузите .exe"}), 404
             
    except Exception as e:
        current_app.logger.error(f"Hotfix error: {e}")
        return jsonify({"error": str(e)}), 500

@main_routes.route('/api/force_update', methods=['POST'])
@login_required
def force_update():
    settings = get_server_settings()
    data = request.json
    if data and 'force' in data:
        settings.force_update = bool(data['force'])
    else:
        settings.force_update = not settings.force_update
        
    db.session.commit()
    log_admin_action("Toggle Force Update", "All", f"Enabled: {settings.force_update}")
    return jsonify({"status": "ok", "force_update": settings.force_update})

@main_routes.route("/api/set_version", methods=['POST'])
@login_required
def set_version():
    data = request.json
    if not data:
        return jsonify({"error": "Missing data"}), 400
        
    version = data.get('version')
    stable_version = data.get('stable_version')
    priority = data.get('priority') # 'stable' or 'latest'
    
    settings = get_server_settings()
    if version:
        settings.current_version = version
    if stable_version:
        settings.stable_version = stable_version
    if priority in ['stable', 'latest']:
        settings.priority_version = priority
        
    db.session.commit()
    return jsonify({
        "status": "ok", 
        "current_version": settings.current_version,
        "stable_version": settings.stable_version,
        "priority": settings.priority_version
    })

@main_routes.route('/api/upload_update', methods=['POST'])
@login_required
def upload_update():
    """Secure API for uploading a new version with metadata auto-generation."""
    try:
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

@main_routes.route("/client_checkin", methods=["POST"])
@main_routes.route("/api/client/checkin", methods=["POST"])
def client_checkin():
    data = request.json
    client_id = data.get('client_id')
    version = data.get('version')
    # Always prioritize 'username' as the login and 'name' as the display name
    received_login = data.get('username') or data.get('login') or 'Unknown'
    received_name = data.get('name') or data.get('profile_name') or 'Unknown'
    hwid = data.get('hwid') or data.get('client_id') or 'Unknown'
    ip_address = request.remote_addr

    # Debug logging
    print(f"[Checkin] Received: ID={client_id}, Ver={version}, Login={received_login}, Profile={received_name}")

    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400
    
    try:
        # Check database for client
        client = Client.query.filter_by(client_id=client_id).first()
        # Find user by LOGIN (username)
        user = User.query.filter_by(username=received_login).first()
        
        if client:
            # Update last seen and IP always
            client.last_seen = datetime.utcnow()
            client.ip_address = ip_address
            client.version = version
            client.username = received_login
            client.name = received_name
            client.hwid = hwid
            
            # Check if banned
            if client.status == 'Banned':
                db.session.commit() # Save the updated last_seen even if banned
                current_app.logger.warning(f"[Checkin] REJECTED: Banned client {client_id}")
                return jsonify({
                    "status": "banned", 
                    "message": "Ваш доступ заблокирован администратором. Пожалуйста, свяжитесь с поддержкой для выяснения причин."
                }), 403

            # Check if license expired
            if client.license_expiry and client.license_expiry < datetime.utcnow():
                db.session.commit()
                current_app.logger.info(f"[Checkin] License expired for client {client_id}")
                return jsonify({
                    "status": "expired",
                    "message": f"Срок действия вашей лицензии истек {client.license_expiry.strftime('%d.%m.%Y %H:%M')}. Пожалуйста, продлите подписку."
                }), 402

            # Only update status to Active if it's not Banned
            client.status = 'Active'
            
            if user:
                client.owner = user
        else:
            # Create new client record
            client = Client(
                client_id=client_id, 
                version=version, 
                username=received_login, 
                name=received_name,
                hwid=hwid,
                ip_address=ip_address, 
                status='Active',
                license_expiry=datetime.utcnow() + timedelta(days=7) # Default 7 days for new clients
            )
            if user: 
                client.owner = user
            db.session.add(client)
        
        db.session.commit()
        
        # Mapping logic for response/broadcast
        owner_login = client.owner.username if client.owner else None
        owner_full_name = client.owner.full_name if client.owner else None
        
        # LOGIN column: Use registered username if available, otherwise what client sent
        display_login = owner_login or client.username or "Unknown"
        
        # NAME column: Use registered full name if available, otherwise client profile name
        display_name = owner_full_name or client.name
        if not display_name or display_name == "Unknown":
            display_name = display_login # Fallback to login if name is missing

        # Broadcast to all connected clients via WebSocket (Admin panel update)
        socketio.emit('client_update', {
            "id": client.id,
            "client_id": client.client_id,
            "username": display_login,
            "name": display_name,
            "hwid": client.hwid,
            "version": client.version,
            "last_seen": client.last_seen.isoformat(),
            "ip": client.ip_address,
            "status": client.status,
            "license_expiry": client.license_expiry.isoformat() if client.license_expiry else None
        })

        return jsonify({
            "status": "ok",
            "message": "Checkin successful",
            "commands": commands,
            "license_expiry": client.license_expiry.isoformat() if client.license_expiry else None,
            "server_time": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Checkin] Error: {e}")
        return jsonify({"error": str(e)}), 500

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
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validation
        if not username or len(username) < 3:
            flash('Логин должен быть не менее 3 символов', 'danger')
            return redirect(url_for('main.register'))
            
        if not full_name:
            flash('Имя обязательно для заполнения', 'danger')
            return redirect(url_for('main.register'))

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя (логин) уже занято', 'danger')
            return redirect(url_for('main.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('main.register'))
            
        hashed_password = generate_password_hash(password)
        user = User(username=username, full_name=full_name, email=email, password=hashed_password)
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

@main_routes.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        
        # Validation
        if not full_name:
            flash('Имя обязательно для заполнения', 'danger')
            return redirect(url_for('main.profile'))
            
        if not email:
            flash('Email обязателен для заполнения', 'danger')
            return redirect(url_for('main.profile'))

        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Этот Email уже используется другим пользователем', 'danger')
            return redirect(url_for('main.profile'))

        current_user.full_name = full_name
        current_user.email = email
        db.session.commit()
        flash('Профиль успешно обновлен!', 'success')
        return redirect(url_for('main.profile'))
        
    return render_template('profile.html', user=current_user)

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
    admin_logs = AdminLog.query.order_by(AdminLog.timestamp.desc()).limit(20).all()
    return render_template('dashboard.html', clients=clients, settings=settings, now_utc=datetime.utcnow, admin_logs=admin_logs)

@main_routes.route("/sync")
@login_required
def sync():
    return render_template('sync.html')

@main_routes.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow()})

@main_routes.route("/api/clients")
@login_required
def api_clients():
    # Admin session required via @login_required
    current_app.logger.info("[API] /api/clients requested")
    try:
        # Optimization: Sort by ID ASC to keep positions stable
        limit = request.args.get('limit', 200, type=int)
        clients = Client.query.order_by(Client.id.asc()).limit(limit).all()
        
        # Determine who is REALLY online (last seen within 3 minutes)
        now = datetime.utcnow()
        online_threshold = timedelta(minutes=3)

        result = []
        needs_commit = False
        
        for c in clients:
            try:
                is_online = (now - c.last_seen) < online_threshold if c.last_seen else False
                
                # Update status to Offline if threshold passed, but don't commit yet
                if not is_online and c.status == 'Active':
                    c.status = 'Offline'
                    needs_commit = True

                # Mapping logic for Login (username) and Name (full_name/profile_name)
                owner_login = c.owner.username if c.owner else None
                owner_full_name = c.owner.full_name if c.owner else None
                
                # LOGIN column: registered login or client-sent username
                display_login = owner_login or c.username or "Unknown"
                
                # NAME column: registered full name or client-sent profile name
                display_name = owner_full_name or c.name
                if not display_name or display_name == "Unknown":
                    display_name = display_login # Fallback

                result.append({
                    "id": c.id,
                    "client_id": c.client_id,
                    "username": display_login,
                    "name": display_name,
                    "hwid": c.hwid or "—",
                    "version": c.version or "1.0.0",
                    "last_seen": c.last_seen.isoformat() if c.last_seen else None,
                    "ip": c.ip_address or "0.0.0.0",
                    "status": c.status,
                    "is_online": is_online,
                    "license_expiry": c.license_expiry.isoformat() if c.license_expiry else None
                })
            except Exception as e:
                current_app.logger.error(f"[API] Error serializing client: {e}")
                continue
        
        if needs_commit:
            try:
                db.session.commit()
            except:
                db.session.rollback()
                
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"[API] Global error in api_clients: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@main_routes.route('/api/cleanup/ram', methods=['POST'])
@login_required
def api_cleanup_ram():
    try:
        # Add to pending commands for ALL clients
        clients = Client.query.filter(Client.status != 'Banned').all()
        for c in clients:
            if c.client_id not in PENDING_COMMANDS:
                PENDING_COMMANDS[c.client_id] = []
            if 'cleanup_ram' not in PENDING_COMMANDS[c.client_id]:
                PENDING_COMMANDS[c.client_id].append('cleanup_ram')
        
        # Also emit via socket for real-time dashboard feedback
        socketio.emit('client_command', {'command': 'cleanup_ram'})
        log_admin_action("Cleanup RAM", "All", "Sent to all active clients")
        return jsonify({"status": "ok", "msg": f"Команда на очистку ОЗУ поставлена в очередь для {len(clients)} клиентов"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

@main_routes.route('/api/cleanup/temp', methods=['POST'])
@login_required
def api_cleanup_temp():
    try:
        # Add to pending commands for ALL clients
        clients = Client.query.filter(Client.status != 'Banned').all()
        for c in clients:
            if c.client_id not in PENDING_COMMANDS:
                PENDING_COMMANDS[c.client_id] = []
            if 'cleanup_temp' not in PENDING_COMMANDS[c.client_id]:
                PENDING_COMMANDS[c.client_id].append('cleanup_temp')
                
        # Also emit via socket
        socketio.emit('client_command', {'command': 'cleanup_temp'})
        log_admin_action("Cleanup Temp", "All", "Sent to all active clients")
        return jsonify({"status": "ok", "msg": f"Команда на очистку временных файлов поставлена в очередь для {len(clients)} клиентов"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# --- Client Management Actions ---

@main_routes.route('/api/client/extend', methods=['POST'])
@login_required
def client_extend():
    data = request.json
    client_id = data.get('client_id')
    days = data.get('days')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
        
    if days is None:
        # Lifetime
        client.license_expiry = None
        action_msg = "Set to Lifetime"
    else:
        # Extend from current expiry or now
        current_expiry = client.license_expiry or datetime.utcnow()
        if current_expiry < datetime.utcnow():
            current_expiry = datetime.utcnow()
        client.license_expiry = current_expiry + timedelta(days=int(days))
        action_msg = f"Extended by {days} days"
        
    db.session.commit()
    log_admin_action("Extend License", client_id, action_msg)
    return jsonify({"status": "ok", "license_expiry": client.license_expiry.isoformat() if client.license_expiry else None})

@main_routes.route('/api/client/revoke', methods=['POST'])
@login_required
def client_revoke():
    data = request.json
    client_id = data.get('client_id')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
        
    client.license_expiry = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    log_admin_action("Revoke License", client_id)
    return jsonify({"status": "ok"})

@main_routes.route('/api/client/ban', methods=['POST'])
@login_required
def client_ban():
    data = request.json
    client_id = data.get('client_id')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
        
    client.status = 'Banned'
    db.session.commit()
    log_admin_action("Ban Client", client_id)
    return jsonify({"status": "ok"})

@main_routes.route('/api/client/unban', methods=['POST'])
@login_required
def client_unban():
    data = request.json
    client_id = data.get('client_id')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
        
    client.status = 'Active'
    db.session.commit()
    log_admin_action("Unban Client", client_id)
    return jsonify({"status": "ok"})

@main_routes.route('/api/client/reset_hwid', methods=['POST'])
@login_required
def client_reset_hwid():
    data = request.json
    client_id = data.get('client_id')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
        
    old_hwid = client.hwid
    client.hwid = None
    db.session.commit()
    log_admin_action("Reset HWID", client_id, f"Old HWID: {old_hwid}")
    return jsonify({"status": "ok"})

@main_routes.route('/api/client/disconnect', methods=['POST'])
@login_required
def client_disconnect():
    data = request.json
    client_id = data.get('client_id')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
        
    client.status = 'Offline'
    db.session.commit()
    log_admin_action("Disconnect Client", client_id)
    # Ideally we'd send a websocket message to the client to force close
    socketio.emit('force_disconnect', {"client_id": client_id})
    return jsonify({"status": "ok"})

# --- Firestore License Key Management (Point 4) ---

@main_routes.route("/api/licenses")
@login_required
def api_licenses_list():
    current_app.logger.info("[API] Fetching licenses from Firestore")
    try:
        # Using a longer timeout and verified Session
        url = f"{FIREBASE_BASE_URL}/keys?key={FIREBASE_API_KEY}&pageSize=100"
        with requests.Session() as session:
            resp = session.get(url, timeout=15)
        
        if resp.status_code != 200:
            current_app.logger.error(f"[API] Firestore error: {resp.status_code} - {resp.text}")
            return jsonify({"error": f"Firebase error: {resp.status_code}"}), resp.status_code
            
        data = resp.json()
        documents = data.get("documents", [])
        current_app.logger.info(f"[API] Found {len(documents)} documents in Firestore")
        
        licenses_data = []
        for doc in documents:
            try:
                name_path = doc.get("name", "")
                key_val = name_path.split("/")[-1]
                if not key_val: continue
                
                fields = doc.get("fields", {})
                
                # Manual extraction to be as fast as possible
                is_active = fields.get("is_active", {}).get("booleanValue", True)
                hwid = fields.get("hwid", {}).get("stringValue", "-")
                login_name = fields.get("login", {}).get("stringValue", "-")
                expires_at = fields.get("expires_at", {}).get("stringValue")
                duration = fields.get("duration_days", {}).get("integerValue")
                created = fields.get("created_at", {}).get("timestampValue")

                licenses_data.append({
                    "key": key_val,
                    "is_active": is_active,
                    "hwid": hwid,
                    "login": login_name,
                    "expires_at": expires_at,
                    "duration_days": duration,
                    "created_at": created
                })
            except Exception as doc_err:
                current_app.logger.error(f"[API] Skip document {doc.get('name', 'unknown')}: {doc_err}")
                continue
            
        return jsonify(licenses_data)
    except Exception as e:
        current_app.logger.error(f"[API] Global error in api_licenses_list: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during license fetch"}), 500

@main_routes.route("/api/licenses/create", methods=['POST'])
@login_required
def api_license_create():
    data = request.json
    days = data.get('days', 7)
    count = data.get('count', 1)
    
    # Validation
    try:
        count = int(count)
        if count > 50: count = 50
    except:
        count = 1

    created_keys = []
    try:
        # Use session for multiple requests
        with requests.Session() as session:
            for _ in range(count):
                key_str = '-'.join([secrets.token_hex(2).upper() for _ in range(4)])
                
                # Default duration to int
                try:
                    duration_val = int(days)
                except:
                    duration_val = 7

                doc_data = {
                    "fields": {
                        "duration_days": {"integerValue": duration_val},
                        "is_active": {"booleanValue": True},
                        "hwid": {"stringValue": "-"},
                        "login": {"stringValue": "-"},
                        "rebind_count": {"integerValue": 0},
                        "created_at": {"timestampValue": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
                    }
                }
                
                url = f"{FIREBASE_BASE_URL}/keys?documentId={key_str}&key={FIREBASE_API_KEY}"
                resp = session.post(url, json=doc_data, timeout=10)
                
                if resp.status_code == 200:
                    created_keys.append(key_str)
                    log_admin_action("Create License", key_str, f"Duration: {days} days")
                else:
                    current_app.logger.error(f"[API] Firebase Create Error ({resp.status_code}): {resp.text}")
        
        return jsonify({"status": "ok", "created_keys": created_keys})
    except Exception as e:
        current_app.logger.error(f"[API] Global error in api_license_create: {e}")
        return jsonify({"error": str(e)}), 500

@main_routes.route("/api/licenses/delete", methods=['POST'])
@login_required
def api_license_delete():
    data = request.json
    keys = data.get('keys', [])
    
    deleted_keys = []
    errors = []
    
    for key in keys:
        try:
            url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}"
            resp = requests.delete(url, timeout=10)
            if resp.status_code == 200:
                deleted_keys.append(key)
                log_admin_action("Delete License", key)
            else:
                errors.append({"key": key, "error": resp.text})
        except Exception as e:
            errors.append({"key": key, "error": str(e)})
            
    return jsonify({"status": "ok", "deleted_keys": deleted_keys, "errors": errors})

@main_routes.route("/api/licenses/ban", methods=['POST'])
@login_required
def api_license_ban():
    data = request.json
    key = data.get('key')
    active = data.get('active', False)
    
    try:
        url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}&updateMask.fieldPaths=is_active"
        patch_data = {"fields": {"is_active": {"booleanValue": active}}}
        resp = requests.patch(url, json=patch_data, timeout=10)
        
        if resp.status_code == 200:
            log_admin_action("Ban/Unban License", key, f"Status: {'Active' if active else 'Banned'}")
            return jsonify({"status": "ok"})
        return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_routes.route("/api/licenses/extend", methods=['POST'])
@login_required
def api_license_extend():
    data = request.json
    if not data:
        return jsonify({"error": "Missing request body"}), 400
        
    key = data.get('key')
    days = data.get('days') # None for Lifetime
    
    if not key:
        return jsonify({"error": "Missing license key"}), 400
    
    try:
        new_expire = ""
        if days is None:
            new_expire = "Lifetime"
        else:
            # First get current data
            get_url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}"
            get_resp = requests.get(get_url, timeout=10)
            if get_resp.status_code != 200:
                current_app.logger.error(f"License {key} not found: {get_resp.text}")
                return jsonify({"error": "License not found"}), 404
            
            fields = get_resp.json().get("fields", {})
            expires_at_str = fields.get("expires_at", {}).get("stringValue")
            
            if expires_at_str and expires_at_str != "Lifetime":
                try:
                    # Clean Z suffix
                    dt = datetime.fromisoformat(expires_at_str.replace('Z', ''))
                    new_dt = dt + timedelta(days=int(days))
                    new_expire = new_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except:
                    new_expire = (datetime.utcnow() + timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                new_expire = (datetime.utcnow() + timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}&updateMask.fieldPaths=expires_at"
        patch_data = {"fields": {"expires_at": {"stringValue": new_expire}}}
        resp = requests.patch(url, json=patch_data, timeout=10)
        
        if resp.status_code == 200:
            log_admin_action("Extend License", key, f"New Expiry: {new_expire}")
            return jsonify({"status": "ok", "new_expiry": new_expire})
        
        # Log firebase error details
        current_app.logger.error(f"Firebase patch error: {resp.text}")
        return jsonify({"error": f"Firebase error {resp.status_code}"}), resp.status_code
    except Exception as e:
        current_app.logger.error(f"Global error in api_license_extend: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

