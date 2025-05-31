import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import threading
import signal
import sys

# Configuration
SPREADSHEET_NAME = "Time logging 31/05/2025"  # Name of the Google Spreadsheet
CREDENTIALS_FILE = "google_credentials.json"
URL = "https://live.racefacer.com/speedbay"

# Define kart configurations
KART_CONFIGS = [
    {
        'kart_number': '202',
        'worksheet_name': 'Access'
    }
    # Add more kart configurations as needed
]

class KartTimingScraper:
    def __init__(self, spreadsheet_name, kart_configs, credentials_file):
        self.url = URL
        self.spreadsheet_name = spreadsheet_name
        self.kart_configs = kart_configs
        self.last_lap_times = {config['kart_number']: None for config in kart_configs}
        self.last_lap_counts = {config['kart_number']: None for config in kart_configs}
        self.running = True
        self.setup_driver()
        self.setup_google_sheets(credentials_file)

    def setup_driver(self):
        """Setup Chrome driver with headless mode"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # First try using ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Error with ChromeDriverManager: {str(e)}")
            print("Trying alternative ChromeDriver setup...")
            
            # Alternative setup using system Chrome
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            self.driver = webdriver.Chrome(options=chrome_options)
        
        # Set page load timeout
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(10)

    def setup_google_sheets(self, credentials_file):
        """Setup Google Sheets connection"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(
                credentials_file, scopes=scopes
            )
            
            self.gc = gspread.authorize(credentials)
            self.spreadsheet = self.gc.open(self.spreadsheet_name)
            
            # List all available worksheets
            print(f"\nAvailable worksheets in {self.spreadsheet_name}:")
            for sheet in self.spreadsheet.worksheets():
                print(f"- {sheet.title}")
            
            # Setup worksheets for each kart
            self.worksheets = {}
            for config in self.kart_configs:
                try:
                    worksheet = self.spreadsheet.worksheet(config['worksheet_name'])
                    self.worksheets[config['kart_number']] = worksheet
                    print(f"Successfully connected to worksheet: {config['worksheet_name']} for kart {config['kart_number']}")
                except Exception as e:
                    print(f"Error accessing worksheet {config['worksheet_name']}: {str(e)}")
                    print("Falling back to first worksheet...")
                    self.worksheets[config['kart_number']] = self.spreadsheet.sheet1
                    print(f"Using worksheet: {self.worksheets[config['kart_number']].title} for kart {config['kart_number']}")
        except Exception as e:
            print(f"Error setting up Google Sheets: {str(e)}")
            print("Please check your credentials file and permissions.")
            raise

    def parse_lap_time(self, lap_time_str):
        """Convert lap time string to float seconds with 3 decimal places."""
        if ":" in lap_time_str:
            # Format is M:SS.sss
            try:
                minutes, rest = lap_time_str.split(":")
                seconds = float(rest)
                total_seconds = int(minutes) * 60 + seconds
                return round(total_seconds, 3)
            except Exception:
                return None
        else:
            try:
                return round(float(lap_time_str), 3)
            except Exception:
                return None

    def get_lap_times(self):
        """Scrape current timing for all configured karts using updated XPaths and only process even-numbered rows (skip progress bars)."""
        try:
            print(f"\nLoading page: {self.url}")
            self.driver.get(self.url)
            print("Page loaded successfully")
            
            # Wait for the page to be fully loaded
            time.sleep(5)  # Give extra time for dynamic content to load
            
            # Wait for the table to be present
            print("Waiting for table to load...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[2]/table"))
            )
            
            rows = self.driver.find_elements(By.XPATH, "/html/body/div[4]/div[2]/div/div[2]/table/tr")
            print(f"Found {len(rows)} rows in the table.")
            updates = []
            # Only process even-numbered rows (2, 4, 6, ...) for kart info
            for row_index in range(2, len(rows) + 1, 2):  # Start at 2, step by 2
                try:
                    kart_number_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[2]/div/span")
                    kart_number = kart_number_element.text
                    if kart_number in self.last_lap_times:
                        lap_time_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[4]")
                        current_time = lap_time_element.text
                        if current_time == "-":
                            print(f"Kart {kart_number} - Skipping update as lap time is not available")
                            continue
                        lap_time_sec = self.parse_lap_time(current_time)
                        if lap_time_sec is None:
                            print(f"Kart {kart_number} - Skipping update as lap time could not be parsed")
                            continue
                        lap_count_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[8]")
                        current_lap_count = lap_count_element.text
                        driver_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[3]/div/div/div[2]")
                        driver_name = driver_element.text
                        print(f"Kart {kart_number} - Time: {lap_time_sec} (Lap {current_lap_count}) - Driver: {driver_name}")
                        if lap_time_sec != self.last_lap_times[kart_number] or current_lap_count != self.last_lap_counts[kart_number]:
                            self.last_lap_times[kart_number] = lap_time_sec
                            self.last_lap_counts[kart_number] = current_lap_count
                            updates.append({
                                'kart_number': kart_number,
                                'data': {
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'kart_number': kart_number,
                                    'driver_name': driver_name,
                                    'current_time': lap_time_sec,
                                    'lap_count': current_lap_count
                                }
                            })
                        else:
                            print(f"Kart {kart_number} - Same lap time and count as previous check, skipping update")
                    else:
                        print(f"Row {row_index}: Kart {kart_number} not in KART_CONFIGS, skipping.")
                except Exception as e:
                    print(f"Error processing row {row_index}: {str(e)}")
                    continue
            return updates
                
        except Exception as e:
            print(f"Error scraping data: {str(e)}")
            # Print the page source for debugging
            print("\nPage source:")
            print(self.driver.page_source)
            return None

    def update_spreadsheet(self, updates):
        """Update Google Sheet with new timing data, appending after the last row of the first 5 columns only."""
        if updates:
            for update in updates:
                try:
                    kart_number = update['kart_number']
                    data = update['data']
                    worksheet = self.worksheets[kart_number]
                    
                    # Get all existing data in columns A-E
                    all_data = worksheet.get('A:E')
                    print(f"Current number of rows in worksheet for kart {kart_number} (A-E): {len(all_data)}")
                    
                    # Find the next empty row in columns A-E
                    next_row = 1
                    for i, row in enumerate(all_data, start=1):
                        if any(cell.strip() for cell in row[:5]):
                            next_row = i + 1
                    
                    # Prepare the data row
                    new_row = [
                        data['timestamp'],
                        data['kart_number'],
                        data['driver_name'],
                        data['current_time'],  # Already a float with 3 decimals
                        data['lap_count']
                    ]
                    
                    # Append new row to the worksheet at the correct row
                    worksheet.update(f'A{next_row}:E{next_row}', [new_row])
                    print(f"Data added to row {next_row} for kart {kart_number}: {new_row}")
                except Exception as e:
                    print(f"Error updating spreadsheet for kart {kart_number}: {str(e)}")
                    print("Full error details:", e.__class__.__name__)

    def recreate_driver(self):
        """Recreate the Chrome driver"""
        try:
            self.cleanup()  # Clean up the old driver
            self.setup_driver()  # Create a new driver
            print("Successfully recreated Chrome driver")
            return True
        except Exception as e:
            print(f"Error recreating driver: {str(e)}")
            return False

    def run(self, interval=30):
        """Run the scraper continuously"""
        print("\nStarting kart timing scraper...")
        print(f"Tracking karts: {', '.join(config['kart_number'] for config in self.kart_configs)}")
        print(f"Updating spreadsheet: {self.spreadsheet_name}")
        
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.running:
            try:
                updates = self.get_lap_times()
                if updates:
                    self.update_spreadsheet(updates)
                    consecutive_errors = 0  # Reset error counter on success
                time.sleep(interval)  # Wait for specified interval before next scrape
            except Exception as e:
                consecutive_errors += 1
                print(f"Error in main loop: {str(e)}")
                
                if "invalid session id" in str(e).lower():
                    print("Detected invalid session, attempting to recreate driver...")
                    if self.recreate_driver():
                        consecutive_errors = 0  # Reset error counter if driver recreation was successful
                    else:
                        print("Failed to recreate driver")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"Too many consecutive errors ({consecutive_errors}), attempting to recreate driver...")
                    if self.recreate_driver():
                        consecutive_errors = 0
                    else:
                        print("Failed to recover from errors, exiting...")
                        break
                
                if self.running:  # Only sleep if we're still running
                    time.sleep(interval)  # Wait before retrying

    def stop(self):
        """Stop the scraper gracefully"""
        print("\nStopping scraper...")
        self.running = False
        self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'driver'):
                try:
                    self.driver.quit()
                except Exception as e:
                    print(f"Error during driver quit: {str(e)}")
                finally:
                    self.driver = None
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

def signal_handler(signum, frame):
    """Handle termination signals"""
    print("\nReceived termination signal. Stopping all scrapers...")
    for scraper in scrapers:
        scraper.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Create and run scrapers for each kart
    scrapers = []
    threads = []
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        scraper = KartTimingScraper(SPREADSHEET_NAME, KART_CONFIGS, CREDENTIALS_FILE)
        scrapers.append(scraper)
        # Create a thread for each scraper
        thread = threading.Thread(target=scraper.run)
        threads.append(thread)
        thread.start()
        
        # Wait for all threads to complete (they won't unless interrupted)
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        print("\nStopping all scrapers...")
        for scraper in scrapers:
            scraper.stop()
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        for scraper in scrapers:
            scraper.stop() 