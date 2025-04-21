# /src/market_research/core/call_cache.py
import sqlite3
from datetime import datetime
import logging

from market_research.config import config

# Define cache expiration period in hours
CACHE_EXPIRATION_HOURS = config.CACHE_EXPIRATION_HOURS
DATABASE_PATH = config.CACHE_DB_PATH

# --- CacheManager Definition (Keep as is) ---
class CacheManager:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        # Use context manager for connection to ensure it's closed properly
        # self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # self.cursor = self.conn.cursor()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    summary_type TEXT,
                    keyword TEXT,
                    summary TEXT,
                    timestamp TEXT,
                    UNIQUE(summary_type, keyword)
                )
            ''')
            conn.commit()
        logging.info(f"CacheManager initialized with db: {db_path}")

    def _get_connection(self):
         # Return a new connection for thread safety if needed, or manage a single connection carefully.
         # For simplicity in this example, we create a new connection per operation.
         # In high-concurrency scenarios, consider a connection pool.
        return sqlite3.connect(self.db_path, check_same_thread=False) # Allow different threads


    def check_cache(self, summary_type, keyword):
        """
        Returns a cached summary if it exists and hasn’t expired.
        Checks based on timestamp within CACHE_EXPIRATION_HOURS.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT summary, timestamp FROM summaries
                    WHERE summary_type = ? AND keyword = ?
                ''', (summary_type, keyword))
                result = cursor.fetchone()

            if result:
                summary, timestamp_str = result
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    now = datetime.now()
                    age_hours = (now - timestamp).total_seconds() / 3600

                    if age_hours < CACHE_EXPIRATION_HOURS:
                        logging.info(f"Cache hit for {summary_type} - {keyword} (age: {age_hours:.2f} hours)")
                        return summary
                    else:
                        logging.info(f"Cache expired for {summary_type} - {keyword}: age limit exceeded ({age_hours:.2f} hours > {CACHE_EXPIRATION_HOURS})")
                        # Optionally delete expired entry here
                        # self.delete_cache_entry(summary_type, keyword)
                except ValueError as e:
                    logging.error(f"Error parsing timestamp for keyword {keyword} from cache: {e}")
                    # Treat as expired/invalid
            else:
                 logging.info(f"Cache miss for {summary_type} - {keyword}")

        except sqlite3.Error as e:
            logging.error(f"SQLite error checking cache for {summary_type} - {keyword}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error checking cache for {summary_type} - {keyword}: {e}")

        return None # Return None on miss, expiry, or error

    def update_cache(self, summary_type, keyword, summary):
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        try:
            with self._get_connection() as conn:
                 cursor = conn.cursor()
                 cursor.execute('''
                    INSERT OR REPLACE INTO summaries (summary_type, keyword, summary, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (summary_type, keyword, summary, timestamp))
                 conn.commit()
                 logging.info(f"Cache updated for {summary_type} - {keyword}")
        except sqlite3.Error as e:
            logging.error(f"SQLite error updating cache for {summary_type} - {keyword}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error updating cache for {summary_type} - {keyword}: {e}")

    # Optional: Add a close method if you manage a persistent connection
    # def close(self):
    #     if self.conn:
    #         self.conn.close()
    #         logging.info("CacheManager connection closed.")