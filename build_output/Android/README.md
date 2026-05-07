# MoneyTracker Android APK

## Способ 1: Использование PWA Builder (Онлайн)

1. Перейдите на https://www.pwabuilder.com/
2. Введите URL вашего сервера (например: https://yourdomain.com)
3. Нажмите "Package for stores"
4. Выберите "Android"
5. Скачайте APK

## Способ 2: Использование Bubblewrap (Командная строка)

### Установка:
```bash
npm install -g @aspect-build/aspect-cli
npm install -g @nickvdh/nicern
```

### Создание APK:
```bash
twa-manifest-parser ./twa-manifest.json | bubblewrap init
bubblewrap build
```

## Способ 3: Использование Capacitor

### Установка:
```bash
npm install @capacitor/core @capacitor/cli
npm install @capacitor/android
```

### Настройка:
```javascript
// capacitor.config.json
{
  "appId": "com.moneytracker.app",
  "appName": "MoneyTracker",
  "webDir": "www",
  "server": {
    "url": "http://YOUR_SERVER:5000",
    "cleartext": true
  }
}
```

### Сборка:
```bash
npx cap add android
npx cap sync
npx cap open android
```

Затем в Android Studio: Build → Generate Signed Bundle/APK

## Способ 4: Готовое решение APK

1. Установите APK Builder: https://play.google.com/store/apps/details?id=com.theapkbuilder.app
2. Введите URL вашего PWA
3. Сгенерируйте APK

## Установка APK на телефон

### Через USB:
1. Подключите телефон к ПК
2. Включите "Отладку по USB" в настройках разработчика
3. Скопируйте APK на телефон
4. Установите APK

### Через облако:
1. Загрузите APK в Google Drive
2. Откройте на телефоне
3. Установите APK

## Требования

- Сервер должен быть доступен по HTTP/HTTPS
- Для публикации в Google Play нужна подпись APK
