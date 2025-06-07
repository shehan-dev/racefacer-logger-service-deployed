from flask import Flask, request, jsonify
from kart_lap_matrix_logger import KartLapMatrixLogger
from kart_timing_scraper import KartTimingScraper
import threading
import os

# Create Flask app with the correct base path
app = Flask(__name__, static_url_path='/rs/static')

matrix_logger = None
scraper = None
scraper_thread = None

@app.route("/rs/")
def home():
    return "🏁 Kart Timing Flask API is running!"

@app.route("/rs/start-matrix-logger", methods=["POST"])
def start_matrix_logger():
    global matrix_logger
    if matrix_logger:
        return jsonify({"message": "Matrix logger already running"}), 400

    try:
        matrix_logger = KartLapMatrixLogger(
            spreadsheet_name="Time logging 31/05/2025",
            worksheet_name="Lap Matrix",
            kart_numbers=["201", "202", "203", "204", "205"],
            credentials_file="google_credentials.json"
        )
        threading.Thread(target=matrix_logger.run, daemon=True).start()
        return jsonify({"message": "Matrix logger started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/rs/start-scraper", methods=["POST"])
def start_scraper():
    global scraper, scraper_thread
    if scraper:
        return jsonify({"message": "Scraper already running"}), 400

    try:
        kart_configs = [
            {'kart_number': '202', 'worksheet_name': 'Access'},
            # Add more karts as needed
        ]
        scraper = KartTimingScraper(
            spreadsheet_name="Time logging 31/05/2025",
            kart_configs=kart_configs,
            credentials_file="google_credentials.json"
        )
        scraper_thread = threading.Thread(target=scraper.run, daemon=True)
        scraper_thread.start()
        return jsonify({"message": "Scraper started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/rs/stop-scraper", methods=["POST"])
def stop_scraper():
    global scraper
    if not scraper:
        return jsonify({"message": "No scraper running"}), 400

    scraper.stop()
    scraper = None
    return jsonify({"message": "Scraper stopped"})

if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    # Bind to all interfaces and use production server
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
