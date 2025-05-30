# Kart Timing Scraper & Matrix Logger

This repository contains two main Python scripts for logging kart lap times from RaceFacer live timing pages to Google Sheets:

- `kart_timing_scraper.py`: Logs lap times for specified kart numbers from a RaceFacer live timing page.
- `kart_lap_matrix_logger.py`: Logs lap times for multiple karts in a single worksheet in a matrix format (each kart gets two columns: Driver, Lap Time).

---

## 1. kart_timing_scraper.py

**Purpose:**
- Scrapes lap times for specified kart numbers from a RaceFacer live timing page.
- Logs each kart's data to its own worksheet in a Google Sheet.
- Handles page reloads, duplicate prevention, and Google Sheets integration.

**Configuration:**
- Edit the following variables at the top of the script:
  - `SPREADSHEET_NAME`: Name of your Google Spreadsheet.
  - `CREDENTIALS_FILE`: Path to your Google service account credentials JSON file.
  - `URL`: RaceFacer live timing URL.
  - `KART_CONFIGS`: List of kart numbers and their corresponding worksheet names.

**Usage:**
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Ensure your Google credentials file is present and shared with your Google Sheet.
3. Run the script:
   ```sh
   python kart_timing_scraper.py
   ```

---

## 2. kart_lap_matrix_logger.py

**Purpose:**
- Logs lap times for multiple karts in a single worksheet in a matrix format.
- Each kart gets two columns: "Driver" and "Lap Time".
- Each row represents a lap (row 3 = lap 1, row 4 = lap 2, etc.).
- Only updates the relevant cells for each kart and lap, never overwrites lap numbers or other karts' data.

**Configuration:**
- Edit the following variables at the top of the script:
  - `SPREADSHEET_NAME`: Name of your Google Spreadsheet.
  - `WORKSHEET_NAME`: Name of the worksheet/tab to use (should already have headers and lap numbers set up).
  - `CREDENTIALS_FILE`: Path to your Google service account credentials JSON file.
  - `URL`: RaceFacer live timing URL.
  - `KART_NUMBERS`: List of kart numbers to track, in the order you want them to appear in the sheet.

**Usage:**
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Ensure your Google credentials file is present and shared with your Google Sheet.
3. Set up your worksheet with the desired headers and lap numbers (see below for an example structure).
4. Run the script:
   ```sh
   python kart_lap_matrix_logger.py
   ```

**Example worksheet structure:**

|   | A      | B      | C        | D      | E        | ... |
|---|--------|--------|----------|--------|----------|-----|
| 1 |        | 1      |          | 2      |          | ... |
| 2 |        | Driver | Lap Time | Driver | Lap Time | ... |
| 3 | 1      |        |          |        |          |     |
| 4 | 2      |        |          |        |          |     |
| 5 | 3      |        |          |        |          |     |
|...| ...    |        |          |        |          |     |

- Column A: Lap numbers (pre-filled)
- Columns B/C, D/E, ...: Each kart's Driver and Lap Time

**Notes:**
- The script will only update the relevant cells for each kart and lap, and will not overwrite your lap numbers or headers.
- If a kart is not found in the table for a cycle, it will be skipped for that cycle (others will still be updated).
- Lap times are logged as numbers (seconds, 3 decimal places), regardless of format.

---

## Google Sheets Setup
- Share your Google Sheet with the email address in your service account credentials.
- Make sure the worksheet/tab exists and is named as specified in your configuration.

---

## Requirements
- Python 3.7+
- Google service account credentials (JSON)
- See `requirements.txt` for required packages.

---

## Troubleshooting
- If you get a ChromeDriver or Selenium error, try deleting the webdriver_manager cache:
  ```sh
  rm -rf ~/.wdm
  ```
- Make sure your credentials file is correct and shared with your Google Sheet.
- If you change the list of karts or worksheet structure, restart the script.

---

For further help, open an issue or contact the maintainer. 