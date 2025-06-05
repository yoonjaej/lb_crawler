"""
Lemonbase Review Crawler

- Logs into Lemonbase using credentials from environment variables.
- Crawls all review URLs from the paginated review list.
- For each review, follows any redirects and checks if the final page is a shared-review page.
- Extracts review texts from shared-review pages and saves each to a separate file in shared_reviews/.
- Includes a test mode for crawling a single shared-review URL for debugging.
"""

import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from urllib.parse import urljoin
import time
import tempfile
from glob import glob
import getpass

# Load credentials from environment variables only
def prompt_for_credentials():
    print('LEMONBASE_EMAIL and/or LEMONBASE_PASSWORD not set. Please enter your credentials:')
    email = input('Lemonbase Email: ').strip()
    password = getpass.getpass('Lemonbase Password: ')
    os.environ['LEMONBASE_EMAIL'] = email
    os.environ['LEMONBASE_PASSWORD'] = password
    return email, password

load_dotenv()
EMAIL = os.getenv('LEMONBASE_EMAIL')
PASSWORD = os.getenv('LEMONBASE_PASSWORD')
if not EMAIL or not PASSWORD:
    EMAIL, PASSWORD = prompt_for_credentials()

LOGIN_URL = 'https://lemonbase.com/login'
REVIEWS_URL = 'https://lemonbase.com/app/reviews?page=1'
BASE_URL = 'https://lemonbase.com'

def login(driver):
    """
    Log in to Lemonbase using the provided Selenium driver.
    Waits for the login page to load, enters credentials, and submits the form.
    """
    driver.get(LOGIN_URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'email'))
    )
    email_input = driver.find_element(By.ID, 'email')
    password_input = driver.find_element(By.ID, 'password')
    email_input.clear()
    email_input.send_keys(EMAIL)
    password_input.clear()
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)
    WebDriverWait(driver, 10).until(
        EC.url_changes(LOGIN_URL)
    )
    print('Login successful!')

def crawl_review_urls(driver):
    """
    Crawl all paginated review list pages and extract review URLs.
    Returns a list of absolute review URLs.
    """
    driver.get(REVIEWS_URL)
    review_links = []
    while True:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.ant-table-row'))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, 'tr.ant-table-row')
        for row in rows:
            tds = row.find_elements(By.CSS_SELECTOR, 'td')
            if len(tds) > 1:
                a_tag = tds[1].find_element(By.TAG_NAME, 'a')
                href = a_tag.get_attribute('href')
                if href:
                    # Ensure absolute URL
                    review_links.append(href if href.startswith('http') else urljoin(BASE_URL, href))
        # Pagination: check for next page button
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'ul.ant-pagination li.ant-pagination-next')
            aria_disabled = next_btn.get_attribute('aria-disabled')
            if aria_disabled == 'true':
                break
            # Click next page and wait for table to refresh
            btn = next_btn.find_element(By.TAG_NAME, 'button')
            driver.execute_script('arguments[0].click();', btn)
            WebDriverWait(driver, 10).until(EC.staleness_of(rows[0]))
        except Exception:
            break
    return review_links

def process_review_urls(driver, input_file='review_urls.txt', output_dir='shared_reviews'):
    """
    For each URL in input_file, open the URL, wait for any redirect, and check the final URL:
    - If it contains 'shared-review', extract all <div class="css-1veelxu"> texts and save to a file in output_dir.
    - If it contains 'write-review', skip.
    - Otherwise, do nothing.
    Diagnostic output is printed for each step.
    """
    os.makedirs(output_dir, exist_ok=True)
    found_shared_review = False
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        driver.get(url)
        time.sleep(5)  # Wait for possible client-side redirect
        final_url = driver.current_url
        print(f"Visited: {final_url}")
        if 'write-review' in final_url:
            print("  Skipped (write-review)")
            continue
        if 'shared-review' in final_url:
            found_shared_review = True
            # Extract review ID for filename (second-to-last path segment)
            review_id = final_url.rstrip('/').split('/')[-2] if final_url.rstrip('/').endswith('shared-review') else final_url.rstrip('/').split('/')[-1]
            filename = f'shared-review-{review_id}.txt'
            filepath = os.path.join(output_dir, filename)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.css-1veelxu'))
                )
                divs = driver.find_elements(By.CSS_SELECTOR, 'div.css-1veelxu')
                print(f"  Found {len(divs)} div.css-1veelxu elements")
                if divs:
                    with open(filepath, 'w', encoding='utf-8') as out:
                        # Extract headline from .css-tojoty .typography-headline6.grow FIRST
                        headline_written = False
                        try:
                            headline_elems = driver.find_elements(By.CSS_SELECTOR, 'div.css-tojoty .typography-headline6.grow')
                            if headline_elems:
                                for headline_elem in headline_elems:
                                    headline_text = headline_elem.text.strip()
                                    if headline_text:
                                        out.write('[Headline]\n' + headline_text + '\n---\n')
                                        headline_written = True
                                print(f'  Extracted {len(headline_elems)} headline(s) from css-tojoty')
                            else:
                                print('  No css-tojoty headline found on page')
                        except Exception as e:
                            print(f'  Error extracting css-tojoty headline: {e}')
                        # Now write the review blocks
                        for div in divs:
                            text = div.text.strip()
                            if text:
                                out.write(text + '\n---\n')
                    print(f'  Saved shared review text to {filepath}')
                else:
                    print(f'  No matching divs to save for {final_url}')
            except Exception as e:
                print(f'  Error processing {final_url}: {e}')
        else:
            print("  Not a shared-review page, skipping.")
    if not found_shared_review:
        print("No shared-review pages were found after redirects.")

def test_crawl_single_shared_review(driver, url):
    """
    Test utility: Log in and extract all <div class="css-1veelxu"> texts and <div class="css-tojoty"><div class="typography-headline6 grow">...</div></div> headlines from a single shared-review URL using process_review_urls logic.
    Prints the extracted text blocks to stdout for verification.
    """
    login(driver)
    # Write the test URL to a temporary file
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as tmp:
        tmp.write(url + '\n')
        tmp_path = tmp.name
    output_dir = 'shared_reviews'
    # Run the main extraction logic
    process_review_urls(driver, input_file=tmp_path, output_dir=output_dir)
    # Find the output file (should be only one new file)
    time.sleep(1)  # Ensure file system sync
    output_files = sorted(glob(os.path.join(output_dir, 'shared-review-*.txt')), key=os.path.getmtime, reverse=True)
    if output_files:
        print(f"\n--- Extracted output from {output_files[0]} ---\n")
        with open(output_files[0], 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print("No output file found in shared_reviews directory.")
    # Clean up temp file
    os.remove(tmp_path)

def main():
    """
    Main workflow:
    - Launch headless Chrome
    - Log in to Lemonbase
    - Crawl all review URLs and save to review_urls.txt
    - For each review, follow redirects and extract shared-review texts to files
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    try:
        login(driver)
        review_urls = crawl_review_urls(driver)
        print(f"Found {len(review_urls)} reviews:")
        for url in review_urls:
            print(url)
        # Save to file
        with open('review_urls.txt', 'w', encoding='utf-8') as f:
            for url in review_urls:
                f.write(url + '\n')
        print("Saved review URLs to review_urls.txt")
        # Process shared-review URLs and save their texts
        process_review_urls(driver)
        print("Saved shared review texts to individual files in shared_reviews directory")
    finally:
        driver.quit()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test-single':
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        try:
            test_url = 'https://lemonbase.com/app/reviews/e47b95e8-5ca5-453b-9db6-63e40bb65664/shared-review'
            test_crawl_single_shared_review(driver, test_url)
        finally:
            driver.quit()
    else:
        main() 