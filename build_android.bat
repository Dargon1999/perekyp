@echo off
echo ========================================
echo MoneyTracker PWA - Android Build Script
echo ========================================
echo.

REM Проверяем наличие Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Please install Node.js 18 or higher from https://nodejs.org
    pause
    exit /b 1
)

REM Проверяем наличие Java JDK
java -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Java JDK not found!
    echo Please install Java JDK 17 or higher
    pause
    exit /b 1
)

REM Проверяем наличие Android SDK
if not defined ANDROID_HOME (
    echo WARNING: ANDROID_HOME not set
    echo Please set ANDROID_HOME to your Android SDK path
)

REM Создаем директорию для мобильной сборки
if not exist "mobile_build" mkdir mobile_build
cd mobile_build

REM Инициализируем npm проект
echo Initializing npm project...
call npm init -y

REM Устанавливаем зависимости
echo Installing dependencies...
call npm install @capacitor/core @capacitor/cli @capacitor/android @capacitor/ios

REM Создаем директорию www и копируем веб-файлы
echo Creating web assets...
if exist "www" rmdir /s /q www
mkdir www
xcopy /E /I /Y "..\web\*" "www\"

REM Инициализируем Capacitor
echo Initializing Capacitor...
call npx cap init MoneyTracker com.moneytracker.app --web-dir www

REM Добавляем платформы
echo Adding Android platform...
call npx cap add android

echo Adding iOS platform...
call npx cap add ios

REM Синхронизируем
echo Syncing Capacitor...
call npx cap sync

echo.
echo ========================================
echo Android project created successfully!
echo ========================================
echo.
echo To build APK:
echo 1. Open Android Studio
echo 2. Open folder: mobile_build\android
echo 3. Build -^> Generate Signed Bundle/APK
echo 4. Select APK and follow wizard
echo.
echo Or use command line:
echo   cd mobile_build\android
echo   gradlew assembleRelease
echo.
echo Output: mobile_build\android\app\build\outputs\apk\release\app-release.apk
echo.

REM Открываем Android Studio если установлен
if exist "%ProgramFiles%\Android\Android Studio\bin\studio64.exe" (
    echo Opening Android Studio...
    start "" "%ProgramFiles%\Android\Android Studio\bin\studio64.exe" "mobile_build\android"
) else if exist "%LOCALAPPDATA%\Android\Sdk\..\Android Studio\bin\studio64.exe" (
    echo Opening Android Studio...
    start "" "%LOCALAPPDATA%\Android\Sdk\..\Android Studio\bin\studio64.exe" "mobile_build\android"
)

pause