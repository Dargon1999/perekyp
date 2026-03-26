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
import firebase_admin
from firebase_admin import credentials, firestore, storage

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Firebase Admin
try:
    firebase_admin.initialize_app(options={
        'storageBucket': 'perekyprp.firebasestorage.app'
    })
    fs = firestore.client()
    bucket = storage.bucket()
except Exception as e:
    logging.error(f"Firebase Init Error: {e}")

app = Flask(__name__, 
            template_folder=BASE_DIR, 
            static_folder=BASE_DIR, 
            static_url_path='')
# Configure Database
if os.environ.get('FUNCTION_NAME') or os.environ.get('K_SERVICE'):
    # In Cloud Functions, SQLite must be in /tmp
    DB_PATH = '/tmp/admin.db'
else:
    DB_PATH = os.path.join(BASE_DIR, "admin.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'dev-key-moneytracker-pro-2026' 
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_CSRF_PROTECT'] = False 
# Configure Uploads
# For Cloud Functions, we must use /tmp for writable operations
if os.environ.get('FUNCTION_NAME') or os.environ.get('K_SERVICE'):
    UPLOAD_ROOT = '/tmp'
else:
    UPLOAD_ROOT = os.path.join(BASE_DIR, 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_ROOT
app.config['BACKUP_FOLDER'] = os.path.join(UPLOAD_ROOT, 'backups')
app.config['TRASH_FOLDER'] = os.path.join(UPLOAD_ROOT, 'trash')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # Increased to 500MB

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'msg': 'Файл слишком велик (макс. 500MB)'}), 413

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled Exception: {str(e)}")
    return jsonify({'msg': 'Внутренняя ошибка сервера', 'error': str(e)}), 500

# Create folders if not in cloud environment
if not (os.environ.get('FUNCTION_NAME') or os.environ.get('K_SERVICE')):
    for folder in [app.config['UPLOAD_FOLDER'], app.config['BACKUP_FOLDER'], app.config['TRASH_FOLDER'], 
                  os.path.join(app.config['UPLOAD_FOLDER'], 'images'),
                  os.path.join(app.config['UPLOAD_FOLDER'], 'previews'),
                  os.path.join(app.config['UPLOAD_FOLDER'], 'software')]:
        os.makedirs(folder, exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"], storage_uri="memory://")

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

class ImageMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(50), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_hero = db.Column(db.Boolean, default=False)
    is_bg = db.Column(db.Boolean, default=False)
    # New fields
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    priority = db.Column(db.Integer, default=0)
    hash = db.Column(db.String(64), unique=True) # SHA-256 hash

# Initialize database and admin user
with app.app_context():
    try:
        db.create_all()
        # Add missing columns for ImageMetadata if they don't exist (simple migration)
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                # SQLite-specific migration
                columns = [c[1] for c in conn.execute(text("PRAGMA table_info(image_metadata)")).fetchall()]
                if 'name' not in columns:
                    conn.execute(text("ALTER TABLE image_metadata ADD COLUMN name VARCHAR(255)"))
                if 'description' not in columns:
                    conn.execute(text("ALTER TABLE image_metadata ADD COLUMN description TEXT"))
                if 'priority' not in columns:
                    conn.execute(text("ALTER TABLE image_metadata ADD COLUMN priority INTEGER DEFAULT 0"))
                if 'hash' not in columns:
                    conn.execute(text("ALTER TABLE image_metadata ADD COLUMN hash VARCHAR(64) UNIQUE"))
                conn.commit()
        except Exception as e:
            logging.warning(f"Migration warning: {e}")

        if not Admin.query.filter_by(username='BossDargon').first():
            hashed_pw = bcrypt.generate_password_hash('Sanya0811').decode('utf-8')
            new_admin = Admin(username='BossDargon', password_hash=hashed_pw)
            db.session.add(new_admin)
            db.session.commit()
            logging.info("Database initialized and default admin 'BossDargon' created.")
    except Exception as e:
        logging.error(f"CRITICAL: Database initialization failed: {e}")

# Logging and Helpers
if os.environ.get('FUNCTION_NAME') or os.environ.get('K_SERVICE'):
    # In Cloud Functions, log to stdout/stderr
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(filename='admin_activity.log', level=logging.INFO)

def log_action(action):
    try:
        ip = request.remote_addr
        # Log to Firestore
        fs.collection('admin_logs').add({
            'timestamp': firestore.SERVER_TIMESTAMP,
            'ip': ip,
            'action': action
        })
        # Legacy DB log (keep for now to avoid breaking existing DB logic)
        log = AdminLog(ip=ip, action=action)
        db.session.add(log)
        db.session.commit()
        logging.info(f"{datetime.utcnow()} | IP: {ip} | Action: {action}")
    except Exception as e:
        logging.error(f"Logging failed: {e}")

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Update static folder path
STATIC_DIR = os.path.join(BASE_DIR, 'public')

# Routes
@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/admin')
@app.route('/admin.html')
def admin_page():
    return send_from_directory(STATIC_DIR, 'admin.html')

@app.route('/dashboard')
@app.route('/dashboard.html')
@jwt_required(optional=True)
def dashboard_page():
    # Проверка JWT для защиты на сервере
        # identity = get_jwt_identity()
        # if not identity and window_protocol() != 'file:':
        #     return redirect('/admin')
        return send_from_directory(STATIC_DIR, 'dashboard.html')

def window_protocol():
    # Вспомогательная функция для определения протокола (эмуляция для Flask)
    return request.headers.get('X-Forwarded-Proto', 'http')

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    try:
        data = request.json
        if not data:
            return jsonify({'msg': 'Отсутствуют данные JSON'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        logging.info(f"Login attempt for user: {username}")
        
        # Жестко заданные учетные данные: BossDargon / Sanya0811
        if username == "BossDargon" and password == "Sanya0811":
            access_token = create_access_token(identity=username)
            log_action(f"Successful login (hardcoded): {username}")
            resp = jsonify({'msg': 'Login successful', 'redirect': '/dashboard'})
            set_access_cookies(resp, access_token)
            return resp
        
        log_action(f"Failed login attempt (invalid credentials): {username}")
        return jsonify({'msg': 'Неверный логин или пароль'}), 401
    except Exception as e:
        logging.error(f"Login API Error: {str(e)}")
        return jsonify({'msg': f'Ошибка сервера: {str(e)}'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    resp = jsonify({'msg': 'Logged out'})
    unset_jwt_cookies(resp)
    return resp

@app.route('/config.json', methods=['GET'])
def get_config():
    try:
        # 1. Try Firestore first
        config_doc = fs.collection('settings').document('site_config').get()
        if config_doc.exists:
            return jsonify(config_doc.to_dict())
        
        # 2. Fallback to local file if Firestore is empty
        config_path = update_config_path('config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
    except Exception as e:
        logging.error(f"Config load error: {e}")
    return jsonify({"error": "Config not found"}), 404

@app.route('/api/images', methods=['GET'])
@jwt_required()
def get_images():
    try:
        images_ref = fs.collection('images').order_by('priority', direction=firestore.Query.DESCENDING).order_by('upload_date', direction=firestore.Query.DESCENDING)
        images = images_ref.get()
        
        results = []
        for img in images:
            data = img.to_dict()
            data['id'] = img.id
            # Ensure URL is present
            if 'url' not in data:
                # If URL missing, try to get from bucket
                blob = bucket.blob(f"images/{data['filename']}")
                if blob.exists():
                    blob.make_public()
                    data['url'] = blob.public_url
            results.append(data)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Get images error: {e}")
        return jsonify([]), 500

@app.route('/api/upload/image', methods=['POST'])
@jwt_required()
def upload_image():
    if 'file' not in request.files:
        return jsonify({'msg': 'Файл не выбран'}), 400
    
    files = request.files.getlist('file')
    results = []
    allowed_formats = ['JPEG', 'PNG', 'WEBP']
    
    for file in files:
        if file.filename == '':
            continue
            
        try:
            # 1. Validation via PIL
            img = Image.open(file)
            if img.format not in allowed_formats:
                return jsonify({'msg': f'Формат {img.format} не поддерживается'}), 400
                
            # 2. Temporary save for processing
            original_filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{original_filename}")
            file.seek(0)
            file.save(temp_path)
            
            # 3. Calculate hash
            file_hash = calculate_sha256(temp_path)
            
            # 4. Check duplicates in Firestore
            existing = fs.collection('images').where('hash', '==', file_hash).limit(1).get()
            if existing:
                os.remove(temp_path)
                data = existing[0].to_dict()
                data['id'] = existing[0].id
                data['msg'] = 'Файл уже существует (дубликат)'
                results.append(data)
                continue

            # 5. Process and Optimize
            unique_prefix = hashlib.md5(f"{datetime.now()}{original_filename}".encode()).hexdigest()[:8]
            filename = f"{unique_prefix}_{original_filename}"
            
            # Optimize image
            img = Image.open(temp_path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((1920, 1920))
            img.save(temp_path, optimize=True, quality=85)
            
            # 6. Upload to Firebase Storage
            blob = bucket.blob(f"images/{filename}")
            blob.upload_from_filename(temp_path, content_type=f"image/{img.format.lower()}")
            blob.make_public()
            image_url = blob.public_url
            
            # Create preview
            preview_temp = os.path.join(app.config['UPLOAD_FOLDER'], f"prev_{filename}")
            img.thumbnail((400, 400))
            img.save(preview_temp)
            
            prev_blob = bucket.blob(f"previews/{filename}")
            prev_blob.upload_from_filename(preview_temp, content_type=f"image/{img.format.lower()}")
            prev_blob.make_public()
            preview_url = prev_blob.public_url
            
            # 7. Save to Firestore
            img_data = {
                'filename': filename,
                'original_name': original_filename,
                'name': original_filename,
                'mimetype': f"image/{img.format.lower()}",
                'size': os.path.getsize(temp_path),
                'hash': file_hash,
                'url': image_url,
                'preview': preview_url,
                'upload_date': firestore.SERVER_TIMESTAMP,
                'priority': 0,
                'is_hero': False,
                'is_bg': False
            }
            
            doc_ref = fs.collection('images').document()
            doc_ref.set(img_data)
            img_data['id'] = doc_ref.id
            
            # Cleanup
            os.remove(temp_path)
            os.remove(preview_temp)
            
            log_action(f"Uploaded image to Firebase: {filename}")
            results.append(img_data)
            
        except Exception as e:
            logging.error(f"Image upload error: {e}")
            if os.path.exists(temp_path): os.remove(temp_path)
            return jsonify({'msg': f'Ошибка при обработке {file.filename}: {str(e)}'}), 500
            
    return jsonify({'msg': f'Успешно загружено {len(results)} файлов', 'files': results})

@app.route('/api/update/image-metadata/<string:image_id>', methods=['POST'])
@jwt_required()
def update_image_metadata(image_id):
    try:
        data = request.json
        doc_ref = fs.collection('images').document(image_id)
        
        updates = {}
        if 'name' in data: updates['name'] = data['name']
        if 'description' in data: updates['description'] = data['description']
        if 'priority' in data: updates['priority'] = int(data.get('priority', 0))
        
        if updates:
            doc_ref.update(updates)
            
        log_action(f"Updated metadata for image {image_id}")
        return jsonify({'msg': 'Метаданные обновлены'})
    except Exception as e:
        logging.error(f"Metadata update error: {e}")
        return jsonify({'msg': 'Ошибка обновления'}), 500

@app.route('/api/delete/image/<string:image_id>', methods=['DELETE'])
@jwt_required()
def delete_image(image_id):
    try:
        doc_ref = fs.collection('images').document(image_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'msg': 'Изображение не найдено'}), 404
            
        img_data = doc.to_dict()
        filename = img_data.get('filename')
        
        # 1. Delete from Storage
        try:
            bucket.blob(f"images/{filename}").delete()
            bucket.blob(f"previews/{filename}").delete()
        except Exception as e:
            logging.warning(f"Storage delete warning: {e}")

        # 2. Delete from Firestore
        doc_ref.delete()
        
        log_action(f"Deleted image {filename} from Firebase")
        return jsonify({'msg': 'Изображение удалено'})
    except Exception as e:
        logging.error(f"Delete error: {e}")
        return jsonify({'msg': 'Ошибка удаления'}), 500

@app.route('/api/update/hero', methods=['POST'])
@jwt_required()
def update_hero():
    try:
        data = request.json
        image_id = data.get('image_id')
        placement_type = data.get('type') # 'hero' or 'bg'
        
        if not image_id or not placement_type:
            return jsonify({'msg': 'Missing data'}), 400
            
        # 1. Get image data from Firestore
        img_doc = fs.collection('images').document(str(image_id)).get()
        if not img_doc.exists:
            return jsonify({'msg': 'Image not found'}), 404
            
        img_data = img_doc.to_dict()
        image_url = img_data.get('url')
        
        # 2. Update config in Firestore
        config_ref = fs.collection('settings').document('site_config')
        config_doc = config_ref.get()
        config = config_doc.to_dict() if config_doc.exists else {}
        
        if 'placements' not in config:
            config['placements'] = {}
            
        config['placements'][placement_type] = image_url
        config_ref.set(config)
        
        # 3. Update legacy flags in images collection (optional but keeps data consistent)
        # First reset others
        batch = fs.batch()
        if placement_type == 'hero':
            old_heros = fs.collection('images').where('is_hero', '==', True).get()
            for doc in old_heros: batch.update(doc.reference, {'is_hero': False})
            batch.update(img_doc.reference, {'is_hero': True})
        elif placement_type == 'bg':
            old_bgs = fs.collection('images').where('is_bg', '==', True).get()
            for doc in old_bgs: batch.update(doc.reference, {'is_bg': False})
            batch.update(img_doc.reference, {'is_bg': True})
        batch.commit()

        log_action(f"Updated {placement_type} image to {image_id}")
        return jsonify({'msg': f'Изображение установлено как {placement_type}'})
    except Exception as e:
        logging.error(f"Hero update error: {e}")
        return jsonify({'msg': 'Ошибка обновления'}), 500

# Update config.json path in functions
def update_config_path(filename):
    return os.path.join(BASE_DIR, filename)

@app.route('/api/download/screenshots')
@jwt_required()
def download_screenshots():
    try:
        config_path = update_config_path('config.json')
        if not os.path.exists(config_path):
            return jsonify({'msg': 'Конфигурация не найдена'}), 404
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        screenshots = config.get('screenshots', [])
        if not screenshots:
            return jsonify({'msg': 'Скриншоты не настроены'}), 400
            
        # Create a temporary ZIP file
        zip_filename = f"screenshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, s in enumerate(screenshots):
                if not s.get('url'): continue
                
                # Extract filename from URL (e.g., /uploads/images/abc.jpg)
                url_path = s['url'].replace('/uploads/images/', '')
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', url_path)
                
                if os.path.exists(file_path):
                    # Add to zip with a clean name
                    ext = os.path.splitext(file_path)[1]
                    zipf.write(file_path, f"screenshot_{i+1}{ext}")
        
        # Log action and send file
        log_action(f"Generated screenshots archive: {zip_filename}")
        
        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                logging.error(f"Error removing temporary zip: {e}")
            return response

        return send_from_directory(app.config['UPLOAD_FOLDER'], zip_filename, as_attachment=True)
        
    except Exception as e:
        logging.error(f"Error generating zip: {e}")
        return jsonify({'msg': f'Ошибка генерации архива: {str(e)}'}), 500

from flask import after_this_request

@app.route('/api/update/config', methods=['POST'])
@jwt_required()
def update_config():
    data = request.json
    if not data:
        return jsonify({'msg': 'Empty data'}), 400
    
    try:
        # 1. Update Firestore
        fs.collection('settings').document('site_config').set(data)
        
        # 2. Local backup (keep for now)
        config_path = update_config_path('config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        log_action("Updated Site Configuration (Firestore)")
        return jsonify({'msg': 'Конфигурация обновлена и синхронизирована с Firestore'})
    except Exception as e:
        logging.error(f"Config update error: {e}")
        return jsonify({'msg': 'Ошибка сохранения', 'error': str(e)}), 500

@app.route('/api/update/software', methods=['POST'])
@jwt_required()
def update_software():
    if 'file' not in request.files:
        return jsonify({'msg': 'Файл не выбран'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'msg': 'Имя файла пустое'}), 400

    config_version = request.form.get('version')
    original_filename = secure_filename(file.filename)
    
    if not (original_filename.lower().endswith('.zip') or original_filename.lower().endswith('.exe')):
        return jsonify({'msg': 'Только ZIP или EXE файлы'}), 400

    try:
        # 1. Temporary save
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_sw_{original_filename}")
        file.save(temp_path)
        
        file_size = os.path.getsize(temp_path)
        if file_size > app.config['MAX_CONTENT_LENGTH']:
            os.remove(temp_path)
            return jsonify({'msg': f'Файл слишком велик (макс 500MB)'}), 413

        checksum = calculate_sha256(temp_path)
        
        # 2. Upload to Firebase Storage
        filename = "MoneyTracker.exe" # Strict naming as requested previously
        blob = bucket.blob(f"software/{filename}")
        blob.upload_from_filename(temp_path)
        blob.make_public()
        download_url = blob.public_url
        
        os.remove(temp_path)

        # 3. Update Firestore Config
        config_ref = fs.collection('settings').document('site_config')
        config_doc = config_ref.get()
        config = config_doc.to_dict() if config_doc.exists else {}
        
        # Backup old config in Firestore
        if config_doc.exists:
            fs.collection('config_backups').add({
                'timestamp': firestore.SERVER_TIMESTAMP,
                'data': config
            })

        # Update metadata
        if config_version:
            config['version'] = config_version
        
        config['software_hash'] = checksum
        config['download_url'] = download_url
        config['file_size'] = f"{file_size / (1024*1024):.1f} MB"
        
        config_ref.set(config)
        
        log_action(f"Software published to Firebase: {filename} (v{config.get('version')})")
        return jsonify({
            'msg': f'EXE v{config.get("version")} загружен и опубликован на Firebase',
            'hash': checksum,
            'url': download_url,
            'version': config.get('version')
        })
        
    except Exception as e:
        logging.error(f"Software upload error: {e}")
        return jsonify({'msg': 'Ошибка при публикации', 'log': str(e)}), 500

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

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'js'), filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'css'), filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# End of Routes

# Firebase Functions Export
try:
    from firebase_functions import https_fn
    @https_fn.on_request()
    def api(req: https_fn.Request) -> https_fn.Response:
        return https_fn.as_wsgi(app)(req)
except ImportError:
    pass

if __name__ == '__main__':
    app.run(port=5000, debug=True)
