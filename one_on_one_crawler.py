import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import getpass
import json
import tempfile

ONE_ON_ONE_URL = 'https://lemonbase.com/app/one-on-one?one_on_one_home%5Bpagination%5D%5Bcurrent%5D=1&one_on_one_home%5Bpagination%5D%5BpageSize%5D=100&one_on_one_home%5Bsorter%5D%5BcolumnKey%5D=startAt'
BASE_1_1_URL = 'https://lemonbase.com/app/one-on-one/'

# Credential logic (reuse from crawler.py)
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

def crawl_one_on_one_urls(driver, output_file='1_1_urls.txt'):
    driver.get(ONE_ON_ONE_URL)
    # Wait for table rows to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.ant-table-row'))
    )
    rows = driver.find_elements(By.CSS_SELECTOR, 'tr.ant-table-row[data-row-key]')
    print(f'Found {len(rows)} rows with data-row-key')
    urls = []
    for row in rows:
        data_key = row.get_attribute('data-row-key')
        if data_key:
            url = BASE_1_1_URL + data_key
            urls.append(url)
    with open(output_file, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url + '\n')
    print(f'Saved {len(urls)} 1:1 URLs to {output_file}')

def process_one_on_one_urls(driver, input_file='1_1_urls.txt', output_dir='one_on_one_sessions'):
    """
    For each URL in input_file:
      - Open the URL and wait for redirect
      - Find all meeting date elements (div.typography-body2-bold.text-secondary.css-avbo3m.essl35z0)
      - For each meeting:
          - Click the date element to load the meeting's conversation
          - Extract all conversation blocks (div[data-rbd-draggable-context-id][data-rbd-draggable-id])
          - For each, extract all child divs except those containing a textarea with placeholder '코멘트 입력'
          - For each valid child div, extract text and avatar icon info
      - Save results grouped by meeting date as a JSON file per 1:1 session in output_dir
    """
    import re
    os.makedirs(output_dir, exist_ok=True)
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        # Compute output file path for this session
        session_id = url.rstrip('/').split('/')[-1]
        out_path = os.path.join(output_dir, f'session_{session_id}.json')
        if os.path.exists(out_path):
            print(f"Skipping {url} (already crawled: {out_path})")
            continue
        driver.get(url)
        time.sleep(5)  # Wait for possible client-side redirect
        final_url = driver.current_url
        print(f"Processing 1:1 session: {final_url}")
        # Find all meeting date elements
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.typography-body2-bold.text-secondary.css-avbo3m.essl35z0'))
            )
            meeting_elems = driver.find_elements(By.CSS_SELECTOR, 'div.typography-body2-bold.text-secondary.css-avbo3m.essl35z0')
            print(f"  Found {len(meeting_elems)} meeting date elements")
        except Exception as e:
            print(f"  Error finding meeting date elements: {e}")
            continue
        session_results = []
        for meeting_idx, meeting_elem in enumerate(meeting_elems):
            try:
                meeting_date = meeting_elem.text.strip()
                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView();", meeting_elem)
                meeting_elem.click()
                time.sleep(2)  # Wait for content to update
                # Now extract conversation blocks for this meeting
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-rbd-draggable-context-id][data-rbd-draggable-id]'))
                    )
                    conv_blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-rbd-draggable-context-id][data-rbd-draggable-id]')
                except Exception as e:
                    print(f"    Error finding conversation blocks for meeting '{meeting_date}': {e}")
                    continue
                conversations = []
                for block_idx, conv_block in enumerate(conv_blocks):
                    child_divs = conv_block.find_elements(By.XPATH, './div')
                    for child_idx, child_div in enumerate(child_divs):
                        # Skip if this is a comment input block (contains textarea with placeholder '코멘트 입력')
                        try:
                            textarea = child_div.find_element(By.XPATH, ".//textarea[@placeholder='코멘트 입력']")
                            if textarea:
                                continue
                        except Exception:
                            pass
                        text = child_div.text.strip()
                        avatar_url = ''
                        try:
                            avatar_img = child_div.find_element(By.CSS_SELECTOR, 'span.ant-avatar img')
                            avatar_url = avatar_img.get_attribute('src')
                        except Exception:
                            avatar_url = ''
                        if text:
                            conversations.append({
                                'block_index': block_idx,
                                'child_index': child_idx,
                                'text': text,
                                'avatar_url': avatar_url
                            })
                session_results.append({
                    'meeting_date': meeting_date,
                    'conversations': conversations
                })
                print(f"    Extracted {len(conversations)} conversations for meeting '{meeting_date}'")
            except Exception as e:
                print(f"    Error processing meeting element {meeting_idx}: {e}")
                continue
        # Save results for this session
        with open(out_path, 'w', encoding='utf-8') as out:
            json.dump(session_results, out, ensure_ascii=False, indent=2)
        print(f"  Saved {len(session_results)} meetings to {out_path}")

def test_process_one_on_one_url(driver, test_url):
    """
    Test utility: Run process_one_on_one_urls on a single test URL, print the extracted results for verification.
    """
    import glob
    # Write the test URL to a temporary file
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as tmp:
        tmp.write(test_url + '\n')
        tmp_path = tmp.name
    output_dir = 'test_sessions'
    # Run the extraction logic
    process_one_on_one_urls(driver, input_file=tmp_path, output_dir=output_dir)
    # Find the output file (should be only one new file)
    import time
    time.sleep(1)  # Ensure file system sync
    output_files = sorted(glob.glob(os.path.join(output_dir, 'session_*.json')), key=os.path.getmtime, reverse=True)
    if output_files:
        print(f"\n--- Extracted output from {output_files[0]} ---\n")
        with open(output_files[0], 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print("No output file found in test_sessions directory.")
    # Clean up temp file
    os.remove(tmp_path)

def main():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    try:
        login(driver)
        # Instead of crawling URLs, process all 1:1 session URLs in 1_1_urls.txt
        process_one_on_one_urls(driver)
    finally:
        driver.quit()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'process-1-1':
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        try:
            login(driver)
            process_one_on_one_urls(driver)
        finally:
            driver.quit()
    elif len(sys.argv) > 1 and sys.argv[1] == 'test-single':
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        try:
            login(driver)
            test_url = 'https://lemonbase.com/app/one-on-one/0149ff12-8cb3-41db-8b4d-96f02c986dc3/schedules/99ae864c-8976-46aa-b347-eff422f92e85'
            test_process_one_on_one_url(driver, test_url)
        finally:
            driver.quit()
    else:
        main() 