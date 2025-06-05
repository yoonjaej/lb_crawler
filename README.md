# Lemonbase Web Crawler

This project contains Selenium-based web crawlers for extracting review and 1:1 meeting data from [Lemonbase](https://lemonbase.com/login). It supports robust, resumable crawling and outputs structured data for further analysis.

## Project Structure

- `review_crawler.py` — Crawler for extracting shared review content.
- `one_on_one_crawler.py` — Crawler for extracting 1:1 meeting conversations.
- `requirements.txt` — Python dependencies.
- `one_on_one_sessions/` — Output JSON files for each 1:1 session (git-ignored).
- `shared_reviews/` — Output text files for each shared review (git-ignored).
- `1_1_urls.txt` — List of 1:1 session URLs to crawl (git-ignored).
- `review_urls.txt` — List of review URLs to crawl (git-ignored).
- `test_sessions/` — Output for test runs (git-ignored).
- `.gitignore` — Excludes output, credentials, and environment files from git.

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
   - Create a `.env` file and set your Lemonbase credentials:
     ```env
     LEMONBASE_EMAIL=your_email@example.com
     LEMONBASE_PASSWORD=your_password
     ```
   - If not set, the crawlers will prompt for credentials interactively.

## Usage

### 1. Review Crawler
Extracts shared review content and saves each to a text file in `shared_reviews/`.

- **Crawl all reviews:**
  ```bash
  python review_crawler.py
  ```
  - Crawls all paginated review URLs, saves them to `review_urls.txt`, and extracts shared review content.

- **Test single review extraction:**
  ```bash
  python review_crawler.py test-single
  ```
  - Extracts and prints content for a single shared review URL (for debugging).

### 2. 1:1 Meeting Crawler
Extracts all conversations from each meeting in every 1:1 session listed in `1_1_urls.txt`.

- **Crawl all 1:1 sessions:**
  ```bash
  python one_on_one_crawler.py
  ```
  - For each URL in `1_1_urls.txt`, iterates over all meetings, extracts all conversation blocks, and saves results as JSON in `one_on_one_sessions/`.
  - Skips sessions already crawled (output file exists).

- **Generate 1:1 session URLs:**
  ```bash
  python one_on_one_crawler.py crawl-urls
  ```
  - (If implemented) Crawls the Lemonbase 1:1 page and saves all session URLs to `1_1_urls.txt`.

- **Test single session extraction:**
  ```bash
  python one_on_one_crawler.py test-single
  ```
  - Extracts and prints conversations for a single session URL (for debugging).

## Output Structure

- **Shared Reviews:**
  - `shared_reviews/shared-review-<id>.txt` — Contains headline and review blocks for each shared review.
- **1:1 Sessions:**
  - `one_on_one_sessions/session_<id>.json` — List of meetings, each with extracted conversations:
    ```json
    [
      {
        "meeting_date": "2024년 6월 6일 (금)",
        "conversations": [
          { "block_index": 0, "child_index": 0, "text": "...", "avatar_url": "..." },
          ...
        ]
      },
      ...
    ]
    ```

## Development Notes
- Ensure you have Chrome and ChromeDriver installed and compatible with your Chrome version.
- All credentials and output files are git-ignored for security and cleanliness.
- The crawlers are robust to interruptions and will skip already-crawled sessions/reviews on rerun.
- You can extend the crawlers by modifying `review_crawler.py` or `one_on_one_crawler.py` as needed.

---

For questions or contributions, please open an issue or pull request on [GitHub](https://github.com/yoonjaej/lb_crawler). 