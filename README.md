# Kart Timing Scraper

This script scrapes the current timing for kart #10 from the live timing website (https://live.racefacer.com/speedbay) and updates a Google Sheet with the data.

## Setup Instructions

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Set up Google Sheets API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Sheets API and Google Drive API
   - Create a service account and download the credentials JSON file
   - Rename the credentials file to `google_credentials.json` and place it in the same directory as the script

3. Create a Google Sheet:
   - Create a new Google Sheet
   - Share it with the service account email (found in the credentials JSON file)
   - Note down the spreadsheet name

4. Update the script:
   - Open `kart_timing_scraper.py`
   - Update the `SPREADSHEET_NAME` variable with your Google Sheet name
   - Make sure the `CREDENTIALS_FILE` path is correct

## Running the Script

Run the script using:
```bash
python kart_timing_scraper.py
```

The script will:
- Scrape the live timing website every 30 seconds
- Look for kart #10's current timing
- Update the Google Sheet with the timing data
- Include timestamps for each entry

## Output Format

The Google Sheet will contain the following columns:
- Timestamp (when the data was scraped)
- Kart Number
- Current Time

## Notes

- The script runs in headless mode (no browser window)
- It will continue running until you stop it (Ctrl+C)
- Error handling is included to handle network issues or website changes
- The script includes a 30-second delay between scrapes to avoid overwhelming the server 