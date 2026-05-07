#!/usr/bin/env python3
"""
Скрипт для production сборки и запуска MoneyTracker PWA
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Проверка установленных зависимостей"""
    print("Проверка зависимостей...")
    try:
        import flask
        import flask_login
        print("[OK] Flask установлен")
    except ImportError:
        print("[ERROR] Flask не установлен")
        print("  Установите: pip install flask flask-login flask-sqlalchemy flask-socketio")
        return False
    return True

def create_directories():
    """Создание необходимых директорий"""
    dirs = [
        'web/static/icons',
        'web/static/css',
        'web/static/js',
        'instance',
        'logs'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"[OK] Создана директория: {dir_path}")

def generate_icons():
    """Генерация иконок PWA"""
    print("\nГенерация иконок PWA...")
    if os.path.exists('generate_pwa_icons.py'):
        try:
            subprocess.run([sys.executable, 'generate_pwa_icons.py'], check=True)
            print("[OK] Иконки сгенерированы")
        except subprocess.CalledProcessError:
            print("[ERROR] Ошибка генерации иконок")
            return False
    else:
        print("[ERROR] Скрипт генерации иконок не найден")
        return False
    return True

def setup_database():
    """Настройка базы данных"""
    print("\nНастройка базы данных...")
    try:
        # Импортируем и создаем таблицы
        from web import create_app, db
        app = create_app()
        with app.app_context():
            db.create_all()
            print("[OK] База данных настроена")
    except Exception as e:
        print(f"[ERROR] Ошибка настройки базы данных: {e}")
        return False
    return True

def create_systemd_service():
    """Создание systemd service файла (для Linux)"""
    service_content = """[Unit]
Description=MoneyTracker PWA Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/moneytracker
Environment="PATH=/opt/moneytracker/venv/bin"
ExecStart=/opt/moneytracker/venv/bin/python run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path('moneytracker.service')
    service_path.write_text(service_content)
    print(f"[OK] Создан systemd service файл: {service_path}")
    print("  Для установки: sudo cp moneytracker.service /etc/systemd/system/")
    print("  Для запуска: sudo systemctl start moneytracker")
    print("  Для авто-запуска: sudo systemctl enable moneytracker")

def create_dockerfile():
    """Создание Dockerfile для контейнеризации"""
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Генерация иконок
RUN python generate_pwa_icons.py

# Создание директорий
RUN mkdir -p instance logs web/static/icons

# Настройка переменных окружения
ENV FLASK_APP=run_server.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Открытие порта
EXPOSE 5000

# Запуск приложения
CMD ["python", "run_server.py"]
"""
    
    dockerfile_path = Path('Dockerfile')
    dockerfile_path.write_text(dockerfile_content)
    print(f"[OK] Создан Dockerfile: {dockerfile_path}")

def create_docker_compose():
    """Создание docker-compose.yml"""
    compose_content = """version: '3.8'

services:
  moneytracker:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY:-change-this-secret-key}
    volumes:
      - ./instance:/app/instance
      - ./logs:/app/logs
    restart: unless-stopped
    
  # Опционально: PostgreSQL вместо SQLite
  # postgres:
  #   image: postgres:15
  #   environment:
  #     - POSTGRES_DB=moneytracker
  #     - POSTGRES_USER=moneytracker
  #     - POSTGRES_PASSWORD=${DB_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

volumes:
  postgres_data:
"""
    
    compose_path = Path('docker-compose.yml')
    compose_path.write_text(compose_content)
    print(f"[OK] Создан docker-compose.yml: {compose_path}")

def create_nginx_config():
    """Создание конфигурации Nginx"""
    nginx_config = """server {
    listen 80;
    server_name your-domain.com;  # Замените на ваш домен
    
    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # Замените на ваш домен
    
    # SSL сертификаты (получите через Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # PWA заголовки
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self';";
    
    # Статические файлы
    location /static/ {
        alias /opt/moneytracker/web/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Кэширование для PWA ресурсов
        location ~* \\.(?:css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Service Worker (не кэшировать)
    location /static/sw.js {
        alias /opt/moneytracker/web/static/sw.js;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
    
    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket поддержка
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Запрет доступа к скрытым файлам
    location ~ /\\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
"""
    
    nginx_path = Path('nginx.conf')
    nginx_path.write_text(nginx_config)
    print(f"[OK] Создана конфигурация Nginx: {nginx_path}")

def create_systemd_service():
    """Создание systemd service файла (для Linux)"""
    service_content = """[Unit]
Description=MoneyTracker PWA Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/moneytracker
Environment="PATH=/opt/moneytracker/venv/bin"
ExecStart=/opt/moneytracker/venv/bin/python run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path('moneytracker.service')
    service_path.write_text(service_content)
    print(f"[OK] Создан systemd service файл: {service_path}")
    print("  Для установки: sudo cp moneytracker.service /etc/systemd/system/")
    print("  Для запуска: sudo systemctl start moneytracker")
    print("  Для авто-запуска: sudo systemctl enable moneytracker")

def print_installation_instructions():
    """Вывод инструкций по установке"""
    print("\n" + "="*60)
    print("INSTRUCTIONS FOR INSTALLATION")
    print("="*60)
    
    print("\n1. LOCAL DEVELOPMENT:")
    print("   python run_server.py")
    print("   Откройте http://localhost:5000 в браузере")
    
    print("\n2. PRODUCTION DEPLOYMENT (Linux):")
    print("   # Установка зависимостей")
    print("   pip install -r requirements.txt")
    print("   ")
    print("   # Генерация иконок")
    print("   python generate_pwa_icons.py")
    print("   ")
    print("   # Запуск через systemd")
    print("   sudo cp moneytracker.service /etc/systemd/system/")
    print("   sudo systemctl daemon-reload")
    print("   sudo systemctl start moneytracker")
    print("   sudo systemctl enable moneytracker")
    
    print("\n3. DOCKER DEPLOYMENT:")
    print("   # Сборка и запуск")
    print("   docker-compose up -d")
    print("   ")
    print("   # Просмотр логов")
    print("   docker-compose logs -f")
    
    print("\n4. NGINX CONFIGURATION:")
    print("   # Копирование конфигурации")
    print("   sudo cp nginx.conf /etc/nginx/sites-available/moneytracker")
    print("   sudo ln -s /etc/nginx/sites-available/moneytracker /etc/nginx/sites-enabled/")
    print("   sudo nginx -t")
    print("   sudo systemctl reload nginx")
    
    print("\n5. SSL CERTIFICATE (Let's Encrypt):")
    print("   sudo apt install certbot python3-certbot-nginx")
    print("   sudo certbot --nginx -d your-domain.com")
    
    print("\n6. PWA INSTALLATION:")
    print("   iOS: Откройте в Safari -> Поделиться -> На экран Домой")
    print("   Android: Откройте в Chrome -> Установить приложение")
    
    print("\n" + "="*60)

def main():
    """Основная функция"""
    print("MoneyTracker PWA - Production Setup")
    print("="*40)
    
    # Проверка зависимостей
    if not check_requirements():
        print("\nУстановите зависимости и попробуйте снова")
        sys.exit(1)
    
    # Создание директорий
    create_directories()
    
    # Генерация иконок
    if not generate_icons():
        print("\nПродолжение без иконок...")
    
    # Настройка базы данных
    if not setup_database():
        print("\nОшибка настройки базы данных")
        sys.exit(1)
    
    # Создание конфигурационных файлов
    print("\nСоздание конфигурационных файлов...")
    create_systemd_service()
    create_dockerfile()
    create_docker_compose()
    create_nginx_config()
    
    # Вывод инструкций
    print_installation_instructions()
    
    print("\n[OK] Настройка завершена!")
    print("  Следуйте инструкциям выше для развертывания приложения")

if __name__ == '__main__':
    main()