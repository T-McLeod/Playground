"""
Flask application initialization.
This module creates and configures the Flask app instance.
"""
from flask import Flask
import os
from dotenv import load_dotenv
import google.cloud.logging

# Load environment variables from .env file
load_dotenv()


def create_app():
    """
    Application factory function.
    Creates and configures the Flask application.
    """
    app = Flask(__name__)

    # Configuration from environment variables
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    if os.environ.get("K_SERVICE"):
        client = google.cloud.logging.Client()
            
        client.setup_logging()
        
        app.logger.info("Google Cloud Logging configured successfully.")
            

    # Register routes
    with app.app_context():
        from . import routes

    return app
