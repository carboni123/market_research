# config.py
import os
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse, unquote

# --- Configuration Setup ---
# Load environment variables from .env file first
# Find the .env file path relative to this script or project root
project_root_guess = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
dotenv_path = os.path.join(project_root_guess, '.env')

# Check if .env exists at the guessed path, otherwise load from current dir or parent
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded environment variables from: {dotenv_path}")
else:
    load_dotenv() # Load from cwd or walk up the directory tree
    logging.info("Loaded environment variables (standard search).")
# --- End Configuration Setup ---


class Config:
    def __init__(self):
        # --- OpenAI Configuration ---
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            logging.warning("OPENAI_API_KEY not found in environment variables.")
            # Depending on requirements, you might want to raise an error here
            # raise ValueError("OPENAI_API_KEY is required and not set.")

        # Use the model from .env, fallback to "o4-mini" if not set
        self.GPT_MODEL = os.getenv("GPT_MODEL", "o4-mini")
        logging.info(f"Using GPT Model: {self.GPT_MODEL}")

        # --- Database Configuration ---
        # Cache Database (from DATABASE_URL in .env)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            parsed_url = urlparse(database_url)
            if parsed_url.scheme == 'sqlite':
                # Correctly extract path from sqlite:/// format
                # .netloc will be empty, .path will contain '//app/data/cache.db' or '/app/data/cache.db'
                # We need to remove the leading '/' if it's absolute in the container sense
                # Using os.path.abspath might resolve it based on the host system CWD if not careful.
                # Let's assume the path is relative to the project root or an absolute path within a container context.
                cache_db_rel_path = unquote(parsed_url.path).lstrip('/') # -> 'app/data/cache.db'
                # Construct path relative to the project root where .env is assumed to be
                project_root = os.path.dirname(dotenv_path) if dotenv_path and os.path.exists(dotenv_path) else project_root_guess
                self.CACHE_DB_PATH = os.path.abspath(os.path.join(project_root, cache_db_rel_path))

                logging.info(f"Cache Database Path (from DATABASE_URL): {self.CACHE_DB_PATH}")
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.CACHE_DB_PATH), exist_ok=True)
            else:
                logging.error(f"Unsupported database scheme in DATABASE_URL: {parsed_url.scheme}. Expected 'sqlite'.")
                self.CACHE_DB_PATH = self._get_default_path('data', 'cache.db') # Fallback path
                logging.warning(f"Using default cache DB path: {self.CACHE_DB_PATH}")
        else:
            # Default fallback if DATABASE_URL is not set
            self.CACHE_DB_PATH = self._get_default_path('data', 'cache.db')
            logging.warning(f"DATABASE_URL not found. Using default cache DB path: {self.CACHE_DB_PATH}")

        # User Database (Adding a specific config variable, not in the provided .env)
        # You can add USER_DB_PATH="path/to/your/user_data.db" to .env if needed
        default_user_db_path = self._get_default_path('data', 'user_data.db')
        self.USER_DB_PATH = os.getenv("USER_DB_PATH", default_user_db_path)
        logging.info(f"User Database Path: {self.USER_DB_PATH}")
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.USER_DB_PATH), exist_ok=True)


        # --- Cache Settings ---
        try:
            # Read CACHE_EXPIRATION_HOURS from env, default to 24 if not set or invalid
            self.CACHE_EXPIRATION_HOURS = int(os.getenv("CACHE_EXPIRATION_HOURS", 24))
        except ValueError:
            logging.warning("Invalid CACHE_EXPIRATION_HOURS value in .env. Using default: 24")
            self.CACHE_EXPIRATION_HOURS = 24
        logging.info(f"Cache Expiration (hours): {self.CACHE_EXPIRATION_HOURS}")

        # --- File Paths ---
        # Use PORTFOLIO_PATH from .env, default to 'data/user_portfolio.txt' relative to project root
        portfolio_path_rel = os.getenv("PORTFOLIO_PATH", "data/user_portfolio.txt")
        project_root = os.path.dirname(dotenv_path) if dotenv_path and os.path.exists(dotenv_path) else project_root_guess
        self.PORTFOLIO_PATH = os.path.abspath(os.path.join(project_root, portfolio_path_rel))
        logging.info(f"Portfolio Path: {self.PORTFOLIO_PATH}")

    def _get_default_path(self, *path_parts):
        """Helper to create a default absolute path relative to the project root."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        default_path = os.path.join(project_root, *path_parts)
        # Ensure the directory exists for the default path
        os.makedirs(os.path.dirname(default_path), exist_ok=True)
        return default_path

# Create a single, importable instance of the configuration
config = Config()

# Example of how to access:
# from config import config
# print(config.GPT_MODEL)
# print(config.CACHE_DB_PATH)