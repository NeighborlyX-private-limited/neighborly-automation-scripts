import json
from flask import Flask, request, jsonify
import sys
import threading
import os
import logging
import io
import asyncio

# Ensure the worker directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import generate_insights_for_location

app = Flask(__name__)
# Configure logging for the main Flask server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# The URL of the main application's callback endpoint
CALLBACK_URL = "https://prod.neighborly.in/api"

def worker_task(location_slug, lat, lon, callback_url, log_capture):
    """
    This function runs the async insight generation and captures its output.
    """
    # Redirect stdout and stderr to our log capture
    sys.stdout = log_capture
    sys.stderr = log_capture
    
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Run the async function
            loop.run_until_complete(generate_insights_for_location(location_slug, lat, lon, callback_url))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error in worker_task for {location_slug}: {e}")
    finally:
        # Restore original stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

@app.route('/generate', methods=['POST'])
def generate_insights():
    """
    Endpoint to trigger the AI insight generation.
    """
    try:
        data = request.json
        location_slug = data.get('location_slug')
        lat = data.get('lat')
        lon = data.get('lon')

        if not all([location_slug, lat, lon]):
            return jsonify({"status": "error", "message": "Missing location_slug, lat, or lon"}), 400

        logger.info(f"Received request to generate insights for {location_slug}")

        # Use an in-memory buffer to capture the thread's output
        log_capture = io.StringIO()
        
        # Start the worker task in a new thread
        worker_thread = threading.Thread(
            target=worker_task,
            args=(location_slug, lat, lon, CALLBACK_URL, log_capture)
        )
        worker_thread.start()

        # Print the captured output from the worker thread as it runs
        worker_thread.join(timeout=1) # Don't wait too long for it to finish

        logger.info(f"Worker thread for {location_slug} started. Check logs for details.")
        
        # Send a 202 Accepted response immediately
        return jsonify({
            "status": "ok",
            "message": "Insight generation started",
            "location_slug": location_slug
        }), 202

    except Exception as e:
        logger.error(f"Error processing generate request: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)