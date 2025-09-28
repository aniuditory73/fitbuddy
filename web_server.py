from flask import Flask
import threading
import logging


logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask_app():
    port = 8080 # Default port for Render
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error running Flask app: {e}")

def start_web_server():
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()
    logger.info("Flask web server started in a separate thread.")
