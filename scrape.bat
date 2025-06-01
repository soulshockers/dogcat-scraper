@echo off
REM Stop on error after each step
setlocal enabledelayedexpansion

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found in .venv folder.
    exit /b 1
)

call .\.venv\Scripts\activate.bat

echo Extracting dog data CSV...
python animal_list_scraper.py "https://dogcat.com.ua/adoption?animal=1" -o .\data\dogs\data.csv
if errorlevel 1 exit /b 1

echo Extracting cat data CSV...
python animal_list_scraper.py "https://dogcat.com.ua/adoption?animal=2" -o .\data\cats\data.csv
if errorlevel 1 exit /b 1

echo Extracting dog adoption profiles...
python adoption_profiles_scraper.py .\data\dogs\data.csv -o .\data\dogs\adoption_profiles.json -n 10
if errorlevel 1 exit /b 1

echo Extracting cat adoption profiles...
python adoption_profiles_scraper.py .\data\cats\data.csv -o .\data\cats\adoption_profiles.json -n 10
if errorlevel 1 exit /b 1

echo Downloading dog photos...
python adoption_photos_downloader.py .\data\dogs\adoption_profiles.json -n 10
if errorlevel 1 exit /b 1

echo Downloading cat photos...
python adoption_photos_downloader.py .\data\cats\adoption_profiles.json -n 10
if errorlevel 1 exit /b 1

echo All tasks completed successfully.
pause
