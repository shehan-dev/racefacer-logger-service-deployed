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

# Configuration
SPREADSHEET_NAME = "Time logging 31/05/2025"  # Name of the Google Spreadsheet
WORKSHEET_NAME = "Access"  # Name of the specific worksheet/tab
CREDENTIALS_FILE = "google_credentials.json"
KART_NUMBER = "16"  # Kart number to track
URL = "https://live.racefacer.com/e1gokartgdansk"

class KartTimingScraper:
    def __init__(self, spreadsheet_name, worksheet_name, credentials_file):
        self.url = URL
        self.kart_number = KART_NUMBER
        self.spreadsheet_name = spreadsheet_name
        self.worksheet_name = worksheet_name
        self.last_lap_time = None
        self.last_lap_count = None
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
            print(f"Available worksheets in {self.spreadsheet_name}:")
            for sheet in self.spreadsheet.worksheets():
                print(f"- {sheet.title}")
            
            # Try to get the specific worksheet
            try:
                self.worksheet = self.spreadsheet.worksheet(self.worksheet_name)
                print(f"Successfully connected to worksheet: {self.worksheet_name}")
            except Exception as e:
                print(f"Error accessing worksheet {self.worksheet_name}: {str(e)}")
                print("Falling back to first worksheet...")
                self.worksheet = self.spreadsheet.sheet1
                print(f"Using worksheet: {self.worksheet.title}")
        except Exception as e:
            print(f"Error setting up Google Sheets: {str(e)}")
            print("Please check your credentials file and permissions.")
            raise  # Re-raise the exception to prevent the script from continuing without proper setup

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
                        
                        # Get the lap count from the ninth column
                        lap_count_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[9]")
                        current_lap_count = lap_count_element.text
                        
                        # Get the driver name from the third column
                        driver_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[3]/div/div/div[2]")
                        driver_name = driver_element.text
                        
                        print(f"Found kart {self.kart_number} with time: {current_time} (Lap {current_lap_count}) - Driver: {driver_name}")
                        
                        # Check if this is a new lap
                        if current_time != self.last_lap_time or current_lap_count != self.last_lap_count:
                            self.last_lap_time = current_time
                            self.last_lap_count = current_lap_count
                            return {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'kart_number': self.kart_number,
                                'driver_name': driver_name,
                                'current_time': current_time,
                                'lap_count': current_lap_count
                            }
                        else:
                            print("Same lap time and count as previous check, skipping update")
                            return None
                            
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
            try:
                # Get all existing data
                all_data = self.worksheet.get_all_values()
                print(f"Current number of rows in worksheet: {len(all_data)}")
                
                # Find the next empty row
                next_row = len(all_data) + 1
                
                # Prepare the data row
                new_row = [
                    data['timestamp'],
                    data['kart_number'],
                    data['driver_name'],
                    data['current_time'],
                    data['lap_count']
                ]
                
                # Append new row to the worksheet
                self.worksheet.append_row(new_row)
                print(f"Data added to row {next_row}: {new_row}")
            except Exception as e:
                print(f"Error updating spreadsheet: {str(e)}")
                print("Full error details:", e.__class__.__name__)

    def run(self, interval=30):
        """Run the scraper continuously"""
        print("Starting kart timing scraper...")
        print(f"Tracking kart number: {self.kart_number}")
        print(f"Updating spreadsheet: {self.spreadsheet_name} - Worksheet: {self.worksheet_name}")
        while True:
            try:
                data = self.get_lap_times()
                if data:
                    self.update_spreadsheet(data)
                    print(f"Updated spreadsheet with new timing: {data['current_time']} (Lap {data['lap_count']}) - Driver: {data['driver_name']}")
                time.sleep(interval)  # Wait for specified interval before next scrape
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
                time.sleep(interval)

    def cleanup(self):
        """Clean up resources"""
        self.driver.quit()

if __name__ == "__main__":
    scraper = KartTimingScraper(SPREADSHEET_NAME, WORKSHEET_NAME, CREDENTIALS_FILE)
    try:
        scraper.run()
    except KeyboardInterrupt:
        print("\nStopping scraper...")
        scraper.cleanup() 