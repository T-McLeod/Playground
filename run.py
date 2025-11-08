"""
Development server entry point.
Run this file to start the Flask application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file in root directory
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    use_https = os.getenv("FLASK_HTTPS") == "1"

    ssl_context = None
    if use_https:
        cert = os.getenv("FLASK_SSL_CERT")
        key = os.getenv("FLASK_SSL_KEY")
        ssl_context = (cert, key)
        
        app.run(
            host="0.0.0.0",
            port=5000,
            ssl_context=ssl_context,
            debug=True
        )
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
