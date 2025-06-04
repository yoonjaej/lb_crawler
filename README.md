# Lemonbase Web Crawler

This project is a Selenium-based web crawler that logs into [Lemonbase](https://lemonbase.com/login) and is ready for extensible data extraction.

## Setup

1. **Clone the repository**
2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your Lemonbase credentials:
     ```bash
     cp .env.example .env
     # Edit .env and set LEMONBASE_EMAIL and LEMONBASE_PASSWORD
     ```

## Usage

Run the crawler:
```bash
python crawler.py
```

## Extending the Crawler
- Add your crawling logic after the login step in `crawler.py`.
- Use Selenium or BeautifulSoup for data extraction as needed.

## Notes
- Ensure you have Chrome and ChromeDriver installed and compatible with your Chrome version.
- Credentials are loaded securely from the `.env` file. 