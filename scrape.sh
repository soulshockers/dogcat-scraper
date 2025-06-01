#!/bin/bash

set -e

source .venv/bin/activate

echo "Extracting dog data CSV..."
python3 animal_list_scraper.py "https://dogcat.com.ua/adoption?animal=1" -o data/dogs/data.csv

echo "Extracting cat data CSV..."
python3 animal_list_scraper.py "https://dogcat.com.ua/adoption?animal=2" -o data/cats/data.csv

echo "Extracting dog adoption profiles..."
python3 adoption_profiles_scraper.py data/dogs/data.csv -o data/dogs/adoption_profiles.json -n 10

echo "Extracting cat adoption profiles..."
python3 adoption_profiles_scraper.py data/cats/data.csv -o data/cats/adoption_profiles.json -n 10

echo "Downloading dog photos..."
python3 adoption_photos_downloader.py data/dogs/adoption_profiles.json -n 10

echo "Downloading cat photos..."
python3 adoption_photos_downloader.py data/cats/adoption_profiles.json -n 10
