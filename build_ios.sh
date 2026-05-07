#!/bin/bash

# MoneyTracker PWA - iOS Build Script
# Требуется macOS с установленными Xcode и Node.js

echo "========================================"
echo "MoneyTracker PWA - iOS Build Script"
echo "========================================"
echo ""

# Проверяем macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "ERROR: This script requires macOS!"
    echo "iOS development can only be done on macOS."
    exit 1
fi

# Проверяем наличие Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found!"
    echo "Please install Node.js 18 or higher from https://nodejs.org"
    exit 1
fi

# Проверяем наличие Xcode
if ! command -v xcodebuild &> /dev/null; then
    echo "ERROR: Xcode not found!"
    echo "Please install Xcode from the App Store"
    exit 1
fi

# Проверяем наличие CocoaPods
if ! command -v pod &> /dev/null; then
    echo "Installing CocoaPods..."
    sudo gem install cocoapods
fi

# Создаем директорию для мобильной сборки
mkdir -p mobile_build
cd mobile_build

# Инициализируем npm проект если еще нет
if [ ! -f "package.json" ]; then
    echo "Initializing npm project..."
    npm init -y
fi

# Устанавливаем зависимости
echo "Installing dependencies..."
npm install @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android

# Создаем директорию www и копируем веб-файлы
echo "Creating web assets..."
rm -rf www
mkdir -p www
cp -R ../web/* www/

# Инициализируем Capacitor если еще нет
if [ ! -f "capacitor.config.json" ]; then
    echo "Initializing Capacitor..."
    npx cap init MoneyTracker com.moneytracker.app --web-dir www
fi

# Добавляем iOS платформу
echo "Adding iOS platform..."
npx cap add ios

# Синхронизируем
echo "Syncing Capacitor..."
npx cap sync

# Устанавливаем CocoaPods
echo "Installing CocoaPods dependencies..."
cd ios/App
pod install
cd ../..

echo ""
echo "========================================"
echo "iOS project created successfully!"
echo "========================================"
echo ""
echo "To build IPA:"
echo "1. Open Xcode: open ios/App/App.xcworkspace"
echo "2. Select your team in Signing & Capabilities"
echo "3. Product - Archive"
echo "4. Distribute App - Ad Hoc or App Store"
echo ""
echo "Or use command line:"
echo "  cd ios/App"
echo "  xcodebuild -workspace App.xcworkspace -scheme App -configuration Release -sdk iphoneos -archivePath App.xcarchive archive"
echo ""

# Открываем Xcode
echo "Opening Xcode..."
open ios/App/App.xcworkspace

echo ""
echo "Note: To publish to App Store, you need:"
echo "- Apple Developer Program membership ($99/year)"
echo "- App Store Connect account"
echo "- Valid provisioning profile and signing certificate"