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
import gspread.utils
import os

class KartLapMatrixLogger:
    def __init__(self, spreadsheet_name, worksheet_name, kart_numbers, credentials_file):
        self.url = "https://live.racefacer.com/speedbay"
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
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0")

        # Try to get Chrome binary location from environment variable
        chrome_binary = os.getenv('CHROME_BIN')
        
        # If not set, try common locations
        if not chrome_binary:
            common_locations = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",  # Windows
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",  # Windows (x86)
                "/usr/bin/google-chrome",  # Linux
                "/usr/bin/google-chrome-stable",  # Linux (stable)
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS
            ]
            
            for location in common_locations:
                if os.path.exists(location):
                    chrome_binary = location
                    break

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                self.driver = webdriver.Chrome(options=chrome_options)
            else:
                raise Exception("Could not find Chrome binary. Please set CHROME_BIN environment variable or ensure Chrome is installed in a standard location.")

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
        if ":" in lap_time_str:
            try:
                minutes, rest = lap_time_str.split(":")
                seconds = float(rest)
                return round(int(minutes) * 60 + seconds, 3)
            except Exception:
                return None
        else:
            try:
                return round(float(lap_time_str), 3)
            except Exception:
                return None

    def get_kart_data(self):
        self.driver.get(self.url)
        time.sleep(5)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[2]/table"))
        )
        rows = self.driver.find_elements(By.XPATH, "/html/body/div[4]/div[2]/div/div[2]/table/tr")
        kart_data = {}
        for row_index in range(2, len(rows) + 1, 2):
            try:
                kart_number = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[2]/div/span").text
                if kart_number in self.kart_numbers:
                    lap_time_text = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[4]").text
                    if lap_time_text == "-": continue
                    lap_time = self.parse_lap_time(lap_time_text)
                    if lap_time is None: continue
                    lap_count = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[8]").text
                    driver_name = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[3]/div/div/div[2]").text
                    kart_data[kart_number] = (driver_name, lap_time, lap_count)
            except: continue
        return kart_data

    def update_matrix(self, kart_data):
        for kart_idx, kart in enumerate(self.kart_numbers):
            if kart in kart_data:
                driver, lap_time, lap_count = kart_data[kart]
                if lap_count != self.last_lap_counts[kart] and lap_time != "-":
                    self.lap_history[kart].append((driver, lap_time))
                    self.last_lap_counts[kart] = lap_count
                    self.last_lap_times[kart] = lap_time
                    self.last_driver_names[kart] = driver
                    try:
                        row = int(lap_count) + 2
                        col_driver = kart_idx * 2 + 2
                        col_laptime = kart_idx * 2 + 3
                        self.worksheet.update(gspread.utils.rowcol_to_a1(row, col_driver), [[driver]])
                        self.worksheet.update(gspread.utils.rowcol_to_a1(row, col_laptime), [[lap_time]])
                    except: continue

    def recreate_driver(self):
        try: self.driver.quit()
        except: pass
        self.setup_driver()

    def run(self, interval=5):
        try:
            while True:
                try:
                    data = self.get_kart_data()
                    self.update_matrix(data)
                    time.sleep(interval)
                except Exception as e:
                    if "invalid session id" in str(e).lower():
                        self.recreate_driver()
        except KeyboardInterrupt:
            self.driver.quit()

