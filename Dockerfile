FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    gcc \
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
