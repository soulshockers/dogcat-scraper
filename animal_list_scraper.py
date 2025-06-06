"""
Animal List Scraper

This script crawls a paginated adoption listing page (dogs or cats) on dogcat.com.ua,
extracts basic information (pet_id, profile URL, name, sex, age, and thumbnail photo URL)
for each animal card, and writes the results to a CSV file.

Features:
- Handles pagination by following “Next” links until no more pages remain.
- Uses requests + BeautifulSoup for HTML parsing.
- Skips any animal entry missing a required field (pet_id, link, name, sex, age, or photo_url).
- Avoids duplicate entries by deduplicating on profile URL.

Expected output CSV format:
    pet_id,link,name,sex,age,photo_url
    1728,https://dogcat.com.ua/pet/piksel,Піксель,Хлопчик,1 місяць,https://dogcat.com.ua/fm/pixel/photo.jpg
    ...

Command-line arguments:
    base_url       Starting URL to scrape (e.g., https://dogcat.com.ua/adoption?animal=2).
    -o, --output   Path to the output CSV file (default: ./data/cats/data.csv).

Example usage:
    python animal_list_scraper.py \
        "https://dogcat.com.ua/adoption?animal=2" \
        -o ./data/cats/data.csv
"""

import argparse
import csv
import logging
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def setup_logging():
    """
    Configures logging to write both to a rotating log file and to console.
    Log files are saved in a `logs` directory next to the script.
    """
    script_path = Path(__file__).resolve()
    script_name = script_path.stem
    logs_dir = script_path.parent / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"{script_name}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='a'),
            logging.StreamHandler()
        ]
    )


def extract_animal_data(base_url):
    """
    Crawls the paginated animal listing starting from `base_url`, extracting
    pet_id, link, name, sex, age, and photo_url from each animal card.

    Args:
        base_url (str): URL to the first listing page to begin scraping from.

    Returns:
        list[dict]: List of unique animal entries with required fields.
    """
    animal_data = {}  # Dictionary keyed by profile URL to deduplicate
    session = requests.Session()
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.124 Safari/537.36'
        )
    }

    current_url = base_url

    while current_url:
        try:
            response = session.get(current_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            cards = soup.select('div.animalCard')  # Select all animal cards on the page

            for card in cards:
                # Attempt to extract pet_id from onclick attribute
                pet_id = None
                adopt_btn = card.select_one('button[onclick*="setPopupData"]')
                if adopt_btn:
                    onclick_str = adopt_btn.get('onclick', '')
                    match = re.search(r'setPopupData\((\d+)', onclick_str)
                    if match:
                        pet_id = match.group(1)

                # Extract profile link
                link_tag = card.select_one('a.animalCard__link')
                link = link_tag['href'] if link_tag and link_tag.get('href') else None

                # Extract pet name
                name_tag = card.select_one('h5')
                name = name_tag.get_text(strip=True) if name_tag else None

                # Extract sex and age from <p> tag
                sex, age = "", ""
                p_tag = card.select_one('p')
                if p_tag:
                    parts = [part.strip() for part in p_tag.get_text(strip=True).split(',')]
                    if parts:
                        sex = parts[0]
                        if len(parts) > 1:
                            age = parts[1]

                # Extract photo thumbnail URL
                img_tag = card.select_one('img.animalCard__photo')
                photo_url = img_tag['data-src'] if img_tag and img_tag.get('data-src') else None

                # Skip entries with missing required fields
                if not all([pet_id, link, name, sex, age, photo_url]):
                    logger.warning(
                        f"Skipping animal due to missing data: pet_id={pet_id}, link={link}, "
                        f"name={name}, sex={sex}, age={age}, photo_url={photo_url}"
                    )
                    continue

                # Deduplicate based on profile URL
                if link in animal_data:
                    continue

                animal_data[link] = {
                    'pet_id': pet_id,
                    'link': link,
                    'name': name,
                    'sex': sex,
                    'age': age,
                    'photo_url': photo_url
                }

            # Look for the "Next" page button
            next_button = soup.select_one('a.next:not(.disabled)')
            current_url = next_button['href'] if next_button and next_button.get('href') else None
            logger.info(f"Processed page: {current_url or '(no more pages)'}")

        except requests.RequestException as e:
            logger.error(f"Error fetching page {current_url}: {e}")
            break
        except Exception as e:
            logger.error(f"Error parsing page {current_url}: {e}")
            break

    session.close()
    return list(animal_data.values())


def main():
    """
    Entry point of the script. Parses arguments, initiates scraping, and writes results to CSV.
    """
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Scrape a paginated site for animal data and save to CSV."
    )
    parser.add_argument(
        'base_url',
        help="The base URL to start scraping from (e.g., https://dogcat.com.ua/adoption?animal=2)"
    )
    parser.add_argument(
        '-o', '--output',
        default='./data/cats/data.csv',
        help="Path to the output CSV file (default: ./data/cats/data.csv)"
    )
    args = parser.parse_args()

    logger.info(f"Starting to scrape animal data from: {args.base_url}")
    data = extract_animal_data(args.base_url)

    if not data:
        logger.warning("No animal data found. Exiting.")
        return

    # Ensure the output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        # Write extracted data to CSV
        with open(args.output, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['pet_id', 'link', 'name', 'sex', 'age', 'photo_url'])
            for item in data:
                writer.writerow([
                    item['pet_id'],
                    item['link'],
                    item['name'],
                    item['sex'],
                    item['age'],
                    item['photo_url']
                ])
        logger.info(f"Successfully wrote {len(data)} entries to {args.output}")
    except IOError as e:
        logger.error(f"Error writing to CSV file {args.output}: {e}")


if __name__ == "__main__":
    main()
