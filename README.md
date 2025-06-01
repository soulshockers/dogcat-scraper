# dogcat-scraper

A Python asynchronous scraper to extract dog and cat adoption profiles from [dogcat.com.ua](https://dogcat.com.ua) — including profile details and photos.

---

## Features

- Scrapes adoption listings for dogs and cats.
- Extracts detailed adoption profiles asynchronously.
- Downloads profile photos concurrently.
- Saves outputs as CSV and JSON files.
- Easy to configure and run with bash or batch scripts.

---

## Prerequisites

- Python 3.8 or newer
- `pip` package manager
- Virtual environment recommended (`venv`)

---

## Setup

1. Clone this repository:

   ```bash
   git clone https://github.com/soulshockers/dogcat-scraper.git
   cd dogcat-scraper

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate       # Linux/macOS
   .\.venv\Scripts\activate.bat    # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### On Linux/macOS

Run the bash script:

```bash
./run_scraper.sh
```

### On Windows

Run the batch script:

```cmd
run_scraper.bat
```

---

## Scripts overview

| Script                          | Purpose                                        |
| ------------------------------- | ---------------------------------------------- |
| `animal_list_scraper.py`        | Scrapes list pages and outputs CSV files       |
| `adoption_profiles_scraper.py`  | Extracts detailed profiles asynchronously      |
| `adoption_photos_downloader.py` | Downloads adoption profile photos concurrently |

---

## Configuration

* Change animal type by modifying URL parameters:

  * `animal=1` for dogs
  * `animal=2` for cats
* Control concurrency with the `-n` option (default is 10)
* Output paths can be customized via command line options

---

## Logging

Logs are printed to the console and saved to rotating log files inside the `logs/` directory.

---

## Contributing

Contributions and issues are welcome! Please open a pull request or issue here on GitHub.

---

## License

This project is licensed under the MIT License.

---

## Contact

For questions, open an issue or contact the maintainer via GitHub.

---

> *Happy scraping!* 🐶🐱