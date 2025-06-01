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
    animal_data = {}
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

            cards = soup.select('div.animalCard')

            for card in cards:
                pet_id = None
                adopt_btn = card.select_one('button[onclick*="setPopupData"]')
                if adopt_btn:
                    onclick_str = adopt_btn.get('onclick', '')
                    match = re.search(r'setPopupData\((\d+)', onclick_str)
                    if match:
                        pet_id = match.group(1)

                link_tag = card.select_one('a.animalCard__link')
                link = link_tag['href'] if link_tag and link_tag.get('href') else None

                name_tag = card.select_one('h5')
                name = name_tag.get_text(strip=True) if name_tag else None

                sex, age = "", ""
                p_tag = card.select_one('p')
                if p_tag:
                    parts = [part.strip() for part in p_tag.get_text(strip=True).split(',')]
                    if parts:
                        sex = parts[0]
                        if len(parts) > 1:
                            age = parts[1]

                img_tag = card.select_one('img.animalCard__photo')
                photo_url = img_tag['data-src'] if img_tag and img_tag.get('data-src') else None

                if not all([pet_id, link, name, sex, age, photo_url]):
                    logger.warning(
                        f"Skipping animal due to missing data: pet_id={pet_id}, link={link}, "
                        f"name={name}, sex={sex}, age={age}, photo_url={photo_url}"
                    )
                    continue

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

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
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
