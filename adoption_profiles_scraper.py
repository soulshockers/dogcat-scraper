"""
Asynchronous Pet Adoption Profile Extractor

This script reads a CSV file of pet adoption profile URLs (with pet IDs),
fetches each profile page asynchronously using aiohttp + asyncio, and extracts
detailed information (name, age, gender, photos, videos, about, history) via
BeautifulSoup. The collected profiles are written to a JSON file.

Features:
- Concurrent HTTP requests controlled by a semaphore (configurable concurrency level).
- Robust error handling and logging for failed fetches or missing data.
- Parses “About” and “History” sections, plus both image and video URLs.
- Supports command-line configuration of input CSV, output JSON, and concurrency.

Expected CSV format:
    pet_id,link
    1728,https://dogcat.com.ua/pet/piksel
    1727,https://dogcat.com.ua/pet/cimba
    ...

Command-line arguments:
    csv_path           Path to the input CSV file (required).
    -o, --output       Path to the output JSON file
                       (default: ./data/cats/adoption_profiles.json).
    -n, --concurrency  Number of simultaneous requests (default: 10).

Example usage:
    python adoption_profiles_scraper.py \
        ./data/cats/data.csv \
        -o ./data/cats/adoption_profiles.json \
        -n 20
"""

import argparse
import asyncio
import csv
import json
import logging
import os
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup

logger = None  # Will be initialized in setup_logging()


def setup_logging():
    """
    Configure logging to write to a rotating log file in a 'logs' subdirectory
    and also echo messages to the console. Log filename is based on script name.
    """
    global logger
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
            logging.FileHandler(log_file, encoding='utf-8', mode='a'),  # append mode
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)


def parse_age_gender(text):
    """
    Parse a comma-separated age and gender string into separate fields.

    Args:
        text (str): A string like "1 місяць, Хлопчик".

    Returns:
        tuple: (age, gender) or (None, None) if text is empty.
    """
    if not text:
        return None, None
    parts = [p.strip() for p in text.split(',')]
    age = parts[0] if len(parts) > 0 else None
    gender = parts[1] if len(parts) > 1 else None
    return age, gender


def extract_adoption_profile(html):
    """
    Extract detailed adoption profile information from a profile page's HTML.

    Args:
        html (str): Raw HTML content of an adoption profile page.

    Returns:
        dict or None: Dictionary containing profile fields (name, age, gender,
                      photos, videos, about, history) or None if profile not found.
    """
    soup = BeautifulSoup(html, 'html.parser')
    profile = soup.find('div', class_='adoptionProfilePage')
    if not profile:
        return None

    info = {}

    # Extract the pet's name
    name_tag = profile.select_one('.profile-head h3')
    info['name'] = name_tag.text.strip() if name_tag else None

    # Extract and split age and gender
    age_gender_tag = profile.select_one('.profile-head .body-secondary')
    age_gender_text = age_gender_tag.text.strip() if age_gender_tag else None
    age, gender = parse_age_gender(age_gender_text)
    info['age'] = age
    info['gender'] = gender

    # Collect image and video URLs from the slider
    photo_urls = []
    video_urls = []
    for slide in profile.select('.swiper.slider-profile .swiper-slide'):
        # Check if this slide is a video block
        video_block = slide.select_one('.videoBlock.img')
        if video_block:
            video_link = video_block.get('data-link')
            if video_link:
                video_urls.append(video_link)
        else:
            # Otherwise, extract image URL
            img_tag = slide.select_one('.img img')
            if img_tag:
                url = img_tag.get('data-src')
                if url:
                    photo_urls.append(url)
    info['photos'] = photo_urls
    info['videos'] = video_urls

    # Extract 'about' section (pet skills)
    about_section = profile.select_one('.profile-skills')
    about_texts = []
    if about_section:
        for span in about_section.select('.items .item span'):
            about_texts.append(span.text.strip())
    info['about'] = about_texts

    # Extract history text, removing newlines
    history_div = profile.find('div', class_='profile-history')
    history_text = None
    if history_div:
        p_tag = history_div.find('p', class_='body-secondary')
        if p_tag:
            history_text = p_tag.get_text(separator='\n').strip()
            history_text = history_text.replace('\n', '').replace('\r', '')
    info['history'] = history_text

    return info


async def fetch_profile(session, semaphore, pet_id, url, results, counters):
    """
    Asynchronously fetch and parse a single adoption profile.

    Args:
        session (aiohttp.ClientSession): The HTTP session to use.
        semaphore (asyncio.Semaphore): Semaphore to limit concurrency.
        pet_id (str): Unique ID of the pet from the CSV.
        url (str): URL of the pet's profile page.
        results (list): Shared list to append extracted profile data.
        counters (dict): Shared counters for success/fail metrics.
    """
    async with semaphore:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    info = extract_adoption_profile(html)
                    if info:
                        # Add the extracted fields to the results list
                        results.append({
                            'pet_id': pet_id,
                            'link': url,
                            'name': info.get('name'),
                            'age': info.get('age'),
                            'gender': info.get('gender'),
                            'photos': info.get('photos', []),
                            'videos': info.get('videos', []),
                            'about': info.get('about', []),
                            'history': info.get('history')
                        })
                        counters['success'] += 1
                        logger.info(f"  -> Extracted profile for {url}")
                    else:
                        counters['missing_info'] += 1
                        logger.warning(f"  -> Profile info not found for {url}")
                else:
                    counters['fail'] += 1
                    logger.error(f"  -> Failed to fetch {url}, status code: {resp.status}")
        except Exception as e:
            counters['fail'] += 1
            logger.error(f"  -> Error fetching {url}: {e}")


async def main_async(csv_path, output_path, concurrency):
    """
    Main asynchronous routine to read URLs from CSV, fetch profiles in parallel,
    and write the collected data to a JSON file.

    Args:
        csv_path (str): Path to the input CSV file containing pet_id and link columns.
        output_path (str): Path to the output JSON file.
        concurrency (int): Number of simultaneous fetch operations.
    """
    logger.info(f"Reading URLs from: {csv_path}")

    results = []
    counters = {'links': 0, 'success': 0, 'fail': 0, 'missing_info': 0}
    semaphore = asyncio.Semaphore(concurrency)

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.124 Safari/537.36'
        )
    }

    connector = aiohttp.TCPConnector(limit_per_host=concurrency)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = []
        # Open and iterate over CSV to enqueue fetch tasks
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                pet_id = row.get('pet_id')
                link = row.get('link')
                if not pet_id:
                    logger.warning("Skipping row with missing pet_id.")
                    continue
                if not link:
                    logger.warning("Skipping row with missing link.")
                    continue

                counters['links'] += 1
                logger.info(f"Fetching ({counters['links']}): {link}")
                tasks.append(
                    asyncio.create_task(
                        fetch_profile(session, semaphore, pet_id, link, results, counters)
                    )
                )

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Write the results list as JSON
    try:
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(results, jsonfile, ensure_ascii=False, indent=4)
        logger.info(f"Successfully wrote {len(results)} profiles to {output_path}")
    except IOError as e:
        logger.error(f"Error writing to JSON file {output_path}: {e}")

    # Log summary statistics
    logger.info("Summary:")
    logger.info(f"  Total URLs processed: {counters['links']}")
    logger.info(f"  Successful extractions: {counters['success']}")
    logger.info(f"  Missing profile info: {counters['missing_info']}")
    logger.info(f"  Failed fetches/errors: {counters['fail']}")


def main():
    """
    Entry point: parse CLI arguments, configure logging, and invoke the async runner.
    """
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Extract adoption profiles from URLs in CSV asynchronously."
    )
    parser.add_argument(
        'csv_path',
        help='Path to the input CSV file containing pet_id and link columns'
    )
    parser.add_argument(
        '-o', '--output',
        default='./data/cats/adoption_profiles.json',
        help='Path to the output JSON file (default: ./data/cats/adoption_profiles.json)'
    )
    parser.add_argument(
        '-n', '--concurrency',
        type=int,
        default=10,
        help='Number of simultaneous requests (default: 10)'
    )
    args = parser.parse_args()

    logger.info("Starting profile extraction process...")
    asyncio.run(main_async(args.csv_path, args.output, args.concurrency))


if __name__ == '__main__':
    main()
