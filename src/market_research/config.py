# config.py
import os
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse, unquote

# --- Configuration Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    def __init__(self):
        # --- OpenAI Configuration ---
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            logging.warning("OPENAI_API_KEY not found in environment variables.")

        self.GPT_MODEL = os.getenv("GPT_MODEL", "o4-mini")
        logging.info(f"Using GPT Model: {self.GPT_MODEL}")

        # Determine the true project root for resolving relative paths:
        root_dir = project_root

        # --- Cache Database Path ---
        db_rel = os.getenv("DATABASE_PATH")
        self.CACHE_DB_PATH = os.path.abspath(os.path.join(root_dir, db_rel))
        logging.info(f"Cache Database Path: {self.CACHE_DB_PATH}")
        os.makedirs(os.path.dirname(self.CACHE_DB_PATH), exist_ok=True)
        self.CACHE_EXPIRATION_HOURS = int(os.getenv("CACHE_EXPIRATION_HOURS", "24"))

        # --- User Database Path ---
        user_db_rel = os.getenv("USER_DB_PATH")
        self.USER_DB_PATH = os.path.abspath(os.path.join(root_dir, user_db_rel))
        logging.info(f"User Database Path: {self.USER_DB_PATH}")
        os.makedirs(os.path.dirname(self.USER_DB_PATH), exist_ok=True)

        # --- Portfolio File Path ---
        portfolio_rel = os.getenv("PORTFOLIO_PATH")
        self.PORTFOLIO_PATH = os.path.abspath(os.path.join(root_dir, portfolio_rel))
        logging.info(f"Portfolio Path: {self.PORTFOLIO_PATH}")
        os.makedirs(os.path.dirname(self.PORTFOLIO_PATH), exist_ok=True)

# Create a single, importable instance
config = Config()
