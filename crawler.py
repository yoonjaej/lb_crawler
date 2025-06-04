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

# Load credentials from .env or environment
load_dotenv()
EMAIL = os.getenv('LEMONBASE_EMAIL')
PASSWORD = os.getenv('LEMONBASE_PASSWORD')
if not EMAIL or not PASSWORD:
    print('Error: LEMONBASE_EMAIL and LEMONBASE_PASSWORD environment variables must be set.')
    exit(1)

LOGIN_URL = 'https://lemonbase.com/login'
REVIEWS_URL = 'https://lemonbase.com/app/reviews?page=1'
BASE_URL = 'https://lemonbase.com'


def login(driver):
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


def crawl_reviews(driver):
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
                    review_links.append(href if href.startswith('http') else urljoin(BASE_URL, href))
        # Pagination: check for next page button
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'ul.ant-pagination li.ant-pagination-next')
            aria_disabled = next_btn.get_attribute('aria-disabled')
            if aria_disabled == 'true':
                break
            # Click next page
            btn = next_btn.find_element(By.TAG_NAME, 'button')
            driver.execute_script('arguments[0].click();', btn)
            WebDriverWait(driver, 10).until(EC.staleness_of(rows[0]))
        except Exception:
            break
    return review_links


def process_review_urls(driver, input_file='review_urls.txt', output_dir='shared_reviews'):
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
    login(driver)
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.css-1veelxu'))
        )
        divs = driver.find_elements(By.CSS_SELECTOR, 'div.css-1veelxu')
        print(f"Extracted {len(divs)} text blocks from {url}:")
        for i, div in enumerate(divs, 1):
            text = div.text.strip()
            print(f"--- Block {i} ---\n{text}\n")
    except Exception as e:
        print(f'Error processing {url}: {e}')


def main():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    try:
        login(driver)
        review_urls = crawl_reviews(driver)
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