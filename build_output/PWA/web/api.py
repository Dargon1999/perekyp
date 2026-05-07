from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user
from . import db
import json
import os
import tempfile
from datetime import datetime

api_routes = Blueprint('api', __name__, url_prefix='/api')

# Путь к файлу данных
def get_data_file_path():
    """Получить путь к файлу данных пользователя"""
    if current_user.is_authenticated:
        # Для авторизованных пользователей - персональный файл
        return os.path.join('instance', f'user_{current_user.id}_data.json')
    return None

@api_routes.route('/data/export', methods=['GET'])
@login_required
def export_data():
    """Экспорт всех данных пользователя в JSON файл"""
    data_file = get_data_file_path()
    
    if not data_file or not os.path.exists(data_file):
        # Если файла нет, возвращаем пустую структуру
        data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
            "username": current_user.username,
            "data": {}
        }
    else:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    # Создаем временный файл для скачивания
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(data, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()
    
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'moneytracker_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        mimetype='application/json'
    )

@api_routes.route('/data/import', methods=['POST'])
@login_required
def import_data():
    """Импорт данных из JSON файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'Неверный формат файла. Используйте JSON'}), 400
    
    try:
        # Читаем содержимое файла
        content = file.read().decode('utf-8')
        imported_data = json.loads(content)
        
        # Валидация структуры
        if not isinstance(imported_data, dict):
            return jsonify({'error': 'Неверная структура данных'}), 400
        
        # Сохраняем данные
        data_file = get_data_file_path()
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        
        # Можно слить с существующими данными или перезаписать
        merge_mode = request.form.get('merge', 'false') == 'true'
        
        if merge_mode and os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            # Простое слияние (можно улучшить логику)
            if 'data' in imported_data and 'data' in existing_data:
                existing_data['data'].update(imported_data['data'])
                imported_data = existing_data
        
        # Обновляем метаданные
        imported_data['last_import'] = datetime.utcnow().isoformat()
        imported_data['user_id'] = current_user.id
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(imported_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Данные успешно импортированы',
            'records_count': len(str(imported_data))
        })
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Неверный JSON файл'}), 400
    except Exception as e:
        return jsonify({'error': f'Ошибка импорта: {str(e)}'}), 500

@api_routes.route('/data/sync', methods=['POST'])
@login_required
def sync_data():
    """Синхронизация данных с сервером"""
    try:
        client_data = request.get_json()
        
        if not client_data:
            return jsonify({'error': 'Нет данных для синхронизации'}), 400
        
        data_file = get_data_file_path()
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        
        # Сохраняем данные с меткой времени
        sync_data = {
            "version": "1.0",
            "sync_date": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
            "username": current_user.username,
            "client_timestamp": client_data.get('timestamp'),
            "data": client_data.get('data', {})
        }
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(sync_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Данные синхронизированы',
            'server_timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка синхронизации: {str(e)}'}), 500

@api_routes.route('/data/get', methods=['GET'])
@login_required
def get_data():
    """Получить данные с сервера"""
    data_file = get_data_file_path()
    
    if not data_file or not os.path.exists(data_file):
        return jsonify({
            'success': True,
            'data': {},
            'message': 'Данных нет'
        })
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': data.get('data', {}),
            'last_sync': data.get('sync_date'),
            'version': data.get('version')
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка чтения: {str(e)}'}), 500

@api_routes.route('/data/status', methods=['GET'])
@login_required
def data_status():
    """Статус данных пользователя"""
    data_file = get_data_file_path()
    
    status = {
        'has_data': False,
        'last_modified': None,
        'file_size': 0,
        'can_sync': True
    }
    
    if data_file and os.path.exists(data_file):
        status['has_data'] = True
        status['last_modified'] = datetime.fromtimestamp(
            os.path.getmtime(data_file)
        ).isoformat()
        status['file_size'] = os.path.getsize(data_file)
    
    return jsonify(status)