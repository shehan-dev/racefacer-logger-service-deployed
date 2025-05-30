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

class KartTimingScraper:
    def __init__(self, spreadsheet_name, credentials_file):
        self.url = "https://live.racefacer.com/e1gokartgdansk"
        self.kart_number = "24"
        self.spreadsheet_name = spreadsheet_name
        self.setup_driver()
        # self.setup_google_sheets(credentials_file)

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
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        
        self.gc = gspread.authorize(credentials)
        self.spreadsheet = self.gc.open(self.spreadsheet_name)
        self.worksheet = self.spreadsheet.sheet1

    def get_lap_times(self):
        """Scrape current timing for kart #10"""
        try:
            print(f"Loading page: {self.url}")
            self.driver.get(self.url)
            print("Page loaded successfully")
            
            # Wait for the page to be fully loaded
            time.sleep(5)  # Give extra time for dynamic content to load
            
            # Wait for the table to be present
            print("Waiting for table to load...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[3]/table"))
            )
            
            # Get all rows in the table
            rows = self.driver.find_elements(By.XPATH, "/html/body/div[4]/div[2]/div/div[3]/table/tr")
            print(f"Found {len(rows)} rows in the table")
            
            # Start from row 2 to skip the header row
            for row_index in range(2, len(rows) + 1):
                try:
                    # Get kart number from the second column
                    kart_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[2]/div/span")
                    kart_number = kart_element.text
                    print(f"Checking row {row_index}, found kart number: {kart_number}")
                    
                    if kart_number == self.kart_number:
                        # Found our kart, get the lap time from the fourth column
                        lap_time_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[4]")
                        current_time = lap_time_element.text
                        print(f"Found kart {self.kart_number} with time: {current_time}")
                        
                        return {
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'kart_number': self.kart_number,
                            'current_time': current_time
                        }
                except Exception as e:
                    print(f"Error processing row {row_index}: {str(e)}")
                    continue
            
            print(f"Kart number {self.kart_number} not found in any row")
            return None
                
        except Exception as e:
            print(f"Error scraping data: {str(e)}")
            # Print the page source for debugging
            print("\nPage source:")
            print(self.driver.page_source)
            return None

    def update_spreadsheet(self, data):
        """Update Google Sheet with new timing data"""
        if data:
            # Append new row to the worksheet
            self.worksheet.append_row([
                data['timestamp'],
                data['kart_number'],
                data['current_time']
            ])

    def run(self, interval=30):
        """Run the scraper continuously"""
        print("Starting kart timing scraper...")
        while True:
            try:
                data = self.get_lap_times()
                if data:
                    # self.update_spreadsheet(data)
                    print(f"Updated spreadsheet with new timing: {data['current_time']}")
                time.sleep(interval)  # Wait for specified interval before next scrape
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
                time.sleep(interval)

    def cleanup(self):
        """Clean up resources"""
        self.driver.quit()

if __name__ == "__main__":
    # Replace these with your actual values
    SPREADSHEET_NAME = "Kart Timing Data"
    CREDENTIALS_FILE = "google_credentials.json"
    
    scraper = KartTimingScraper(SPREADSHEET_NAME, CREDENTIALS_FILE)
    try:
        scraper.run()
    except KeyboardInterrupt:
        print("\nStopping scraper...")
        scraper.cleanup() 