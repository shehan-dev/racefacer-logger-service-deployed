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
import os

class KartTimingScraper:
    def __init__(self, spreadsheet_name, kart_configs, credentials_file):
        self.url = "https://live.racefacer.com/speedbay"
        self.spreadsheet_name = spreadsheet_name
        self.kart_configs = kart_configs
        self.last_lap_times = {cfg['kart_number']: None for cfg in kart_configs}
        self.last_lap_counts = {cfg['kart_number']: None for cfg in kart_configs}
        self.running = True
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

        self.worksheets = {}
        for cfg in self.kart_configs:
            try:
                self.worksheets[cfg['kart_number']] = self.spreadsheet.worksheet(cfg['worksheet_name'])
            except:
                self.worksheets[cfg['kart_number']] = self.spreadsheet.sheet1

    def parse_lap_time(self, lap_time_str):
        if ":" in lap_time_str:
            try:
                minutes, seconds = lap_time_str.split(":")
                return round(int(minutes) * 60 + float(seconds), 3)
            except:
                return None
        try:
            return round(float(lap_time_str), 3)
        except:
            return None

    def get_lap_times(self):
        self.driver.get(self.url)
        time.sleep(5)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[2]/table"))
        )

        rows = self.driver.find_elements(By.XPATH, "/html/body/div[4]/div[2]/div/div[2]/table/tr")
        updates = []
        for row_index in range(2, len(rows) + 1, 2):
            try:
                kart_number = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[2]/div/span").text
                if kart_number in self.last_lap_times:
                    lap_time_str = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[4]").text
                    if lap_time_str == "-": continue
                    lap_time = self.parse_lap_time(lap_time_str)
                    if lap_time is None: continue
                    lap_count = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[8]").text
                    driver_name = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[2]/div/div[2]/table/tr[{row_index}]/td[3]/div/div/div[2]").text
                    if lap_time != self.last_lap_times[kart_number] or lap_count != self.last_lap_counts[kart_number]:
                        self.last_lap_times[kart_number] = lap_time
                        self.last_lap_counts[kart_number] = lap_count
                        updates.append({
                            'kart_number': kart_number,
                            'data': {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'kart_number': kart_number,
                                'driver_name': driver_name,
                                'current_time': lap_time,
                                'lap_count': lap_count
                            }
                        })
            except:
                continue
        return updates

    def update_spreadsheet(self, updates):
        for update in updates:
            try:
                kart_number = update['kart_number']
                data = update['data']
                worksheet = self.worksheets[kart_number]
                all_data = worksheet.get('A:E')
                next_row = len(all_data) + 1
                new_row = [data['timestamp'], data['kart_number'], data['driver_name'], data['current_time'], data['lap_count']]
                worksheet.update(f'A{next_row}:E{next_row}', [new_row])
            except:
                continue

    def recreate_driver(self):
        try: self.driver.quit()
        except: pass
        self.setup_driver()

    def run(self, interval=30):
        try:
            while self.running:
                try:
                    updates = self.get_lap_times()
                    if updates:
                        self.update_spreadsheet(updates)
                    time.sleep(interval)
                except Exception as e:
                    if "invalid session id" in str(e).lower():
                        self.recreate_driver()
        except KeyboardInterrupt:
            self.cleanup()

    def stop(self):
        self.running = False
        self.cleanup()

    def cleanup(self):
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                self.driver = None
        except:
            pass

