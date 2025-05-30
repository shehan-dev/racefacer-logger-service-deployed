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

# CONFIGURATION
SPREADSHEET_NAME = "Time logging 31/05/2025"
WORKSHEET_NAME = "Lap Matrix"
CREDENTIALS_FILE = "google_credentials.json"
URL = "https://live.racefacer.com/e1gokartchorzow"
KART_NUMBERS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]  # Order preserved

class KartLapMatrixLogger:
    def __init__(self, spreadsheet_name, worksheet_name, kart_numbers, credentials_file):
        self.url = URL
        self.spreadsheet_name = spreadsheet_name
        self.worksheet_name = worksheet_name
        self.kart_numbers = kart_numbers
        self.last_lap_counts = {kart: None for kart in kart_numbers}
        self.last_lap_times = {kart: None for kart in kart_numbers}
        self.last_driver_names = {kart: None for kart in kart_numbers}
        self.lap_history = {kart: [] for kart in kart_numbers}
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
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        self.gc = gspread.authorize(credentials)
        self.spreadsheet = self.gc.open(self.spreadsheet_name)
        try:
            self.worksheet = self.spreadsheet.worksheet(self.worksheet_name)
        except Exception:
            self.worksheet = self.spreadsheet.add_worksheet(title=self.worksheet_name, rows="1000", cols=str(2*len(self.kart_numbers)))

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

    def get_kart_data(self):
        """Scrape the table and return a dict of kart_number -> (driver, lap_time, lap_count)"""
        self.driver.get(self.url)
        time.sleep(5)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[3]/table"))
        )
        rows = self.driver.find_elements(By.XPATH, "/html/body/div[4]/div[2]/div/div[3]/table/tr")
        kart_data = {}
        for row_index in range(2, len(rows) + 1):
            try:
                kart_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[2]/div/span")
                kart_number = kart_element.text
                if kart_number in self.kart_numbers:
                    lap_time_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[4]")
                    current_time = lap_time_element.text
                    if current_time == "-":
                        continue
                    lap_time_sec = self.parse_lap_time(current_time)
                    if lap_time_sec is None:
                        continue
                    lap_count_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[9]")
                    current_lap_count = lap_count_element.text
                    driver_element = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[3]/table/tr[{row_index}]/td[3]/div/div/div[2]")
                    driver_name = driver_element.text
                    kart_data[kart_number] = (driver_name, lap_time_sec, current_lap_count)
            except Exception:
                continue
        return kart_data

    def update_matrix(self, kart_data):
        # For each kart, if a new lap is detected, add to lap_history and update only the relevant cells
        for kart_idx, kart in enumerate(self.kart_numbers):
            if kart in kart_data:
                driver, lap_time, lap_count = kart_data[kart]
                if lap_count != self.last_lap_counts[kart] and lap_time != "-":
                    self.lap_history[kart].append((driver, lap_time))
                    self.last_lap_counts[kart] = lap_count
                    self.last_lap_times[kart] = lap_time
                    self.last_driver_names[kart] = driver
                    # Update only the relevant cells for this kart and lap
                    try:
                        # lap_count is 1-based, row 3 is lap 1, so row = int(lap_count) + 2
                        row = int(lap_count) + 2
                        col_driver = kart_idx * 2 + 2  # B=2, D=4, F=6, ...
                        col_laptime = kart_idx * 2 + 3 # C=3, E=5, G=7, ...
                        cell_driver = gspread.utils.rowcol_to_a1(row, col_driver)
                        cell_laptime = gspread.utils.rowcol_to_a1(row, col_laptime)
                        self.worksheet.update(cell_driver, [[driver]])
                        self.worksheet.update(cell_laptime, [[lap_time]])
                        print(f"Updated kart {kart} lap {lap_count} at {cell_driver} and {cell_laptime}")
                    except Exception as e:
                        print(f"Error updating cell for kart {kart} lap {lap_count}: {e}")
            else:
                print(f"Kart {kart} not found in this cycle, skipping update for this kart.")

    def write_matrix_to_sheet(self):
        # This function is now unused, but kept for reference
        pass

    def run(self, interval=30):
        print(f"Logging lap times for karts: {', '.join(self.kart_numbers)}")
        try:
            while True:
                kart_data = self.get_kart_data()
                self.update_matrix(kart_data)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopping logger...")
            self.driver.quit()

if __name__ == "__main__":
    logger = KartLapMatrixLogger(SPREADSHEET_NAME, WORKSHEET_NAME, KART_NUMBERS, CREDENTIALS_FILE)
    logger.run() 