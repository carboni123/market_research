# src/market_research/core/user_database.py
import sqlite3
import logging
import os
from datetime import datetime

from market_research.config import config



# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class UserDatabase:
    def __init__(self, db_path=None): # Allow db_path override
        self.db_path = db_path or config.USER_DB_PATH # Use provided path or config default
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            # Connect to the database (or create it if it doesn't exist)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Enable foreign key constraints
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
            self.create_tables()
            logging.info(f"UserDatabase connected to {self.db_path}")
        except sqlite3.Error as e:
            logging.error(f"Failed to connect to database at {self.db_path}: {e}")
            # Optionally raise the error or handle it to prevent app failure
            raise # Reraise the exception to signal connection failure

    def create_tables(self):
        # Create the users table to store account information
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                hashed_password TEXT,
                created_at TEXT
            )
        """)
        # Create the portfolios table to store user portfolio data
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                portfolio_data TEXT,
                updated_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Create the user_summaries table to store summary results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                summary_type TEXT,
                keyword TEXT,
                summary TEXT, -- Stores the raw output (likely JSON string)
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Create the calendar_results table to store calendar outputs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                calendar_result TEXT, -- Stores the raw output (likely JSON string)
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def add_user(self, username, email, hashed_password):
        """Add a new user to the database."""
        created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
        try:
            self.cursor.execute("""
                INSERT INTO users (username, email, hashed_password, created_at)
                VALUES (?, ?, ?, ?)
            """, (username, email, hashed_password, created_at))
            self.conn.commit()
            user_id = self.cursor.lastrowid
            logging.info(f"User '{username}' added with id {user_id}")
            return user_id
        except sqlite3.IntegrityError as e:
            # Check if the error is due to UNIQUE constraint violation
            if "UNIQUE constraint failed: users.username" in str(e):
                 logging.warning(f"User '{username}' already exists.")
            else:
                logging.error(f"Error adding user '{username}': {e}")
            return None # Return None if user already exists or other error

    def get_user(self, username):
        """Retrieve user information based on username."""
        self.cursor.execute("""
            SELECT id, username, email, created_at FROM users
            WHERE username = ?
        """, (username,))
        return self.cursor.fetchone()

    def update_portfolio(self, user_id, portfolio_data):
        """
        Insert or update the portfolio data for a given user.
        The portfolio_data can be any text (e.g., a JSON string).
        """
        updated_at = datetime.now().isoformat(sep=" ", timespec="seconds")
        # Check if the portfolio already exists
        self.cursor.execute("""
            SELECT id FROM portfolios WHERE user_id = ?
        """, (user_id,))
        result = self.cursor.fetchone()
        if result:
            self.cursor.execute("""
                UPDATE portfolios
                SET portfolio_data = ?, updated_at = ?
                WHERE user_id = ?
            """, (portfolio_data, updated_at, user_id))
        else:
            self.cursor.execute("""
                INSERT INTO portfolios (user_id, portfolio_data, updated_at)
                VALUES (?, ?, ?)
            """, (user_id, portfolio_data, updated_at))
        self.conn.commit()
        logging.info(f"Portfolio updated for user_id {user_id}")

    def get_portfolio(self, user_id):
        """Retrieve the portfolio data for a given user."""
        self.cursor.execute("""
            SELECT portfolio_data, updated_at FROM portfolios
            WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchone()

    def add_summary_result(self, user_id, summary_type, keyword, summary):
        """Store a summary result for a user."""
        created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.cursor.execute("""
            INSERT INTO user_summaries (user_id, summary_type, keyword, summary, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, summary_type, keyword, summary, created_at))
        self.conn.commit()
        logging.info(f"Added summary result for user_id {user_id}, keyword '{keyword}'")

    def get_summary_results(self, user_id, summary_type=None):
        """
        Retrieve summary results for a given user, including the ID.
        Optionally filter by summary_type (e.g., "market" or "portfolio").
        Returns: List of tuples (id, summary_type, keyword, summary, created_at)
        """
        if summary_type:
            self.cursor.execute("""
                SELECT id, summary_type, keyword, summary, created_at
                FROM user_summaries
                WHERE user_id = ? AND summary_type = ?
                ORDER BY created_at DESC
            """, (user_id, summary_type))
        else:
            self.cursor.execute("""
                SELECT id, summary_type, keyword, summary, created_at
                FROM user_summaries
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        return self.cursor.fetchall()

    def get_summary_by_id(self, summary_id):
        """
        Retrieve a specific summary by its primary key ID.
        Returns: Tuple (id, user_id, summary_type, keyword, summary, created_at) or None
        """
        self.cursor.execute("""
            SELECT id, user_id, summary_type, keyword, summary, created_at
            FROM user_summaries
            WHERE id = ?
        """, (summary_id,))
        return self.cursor.fetchone()


    def add_calendar_result(self, user_id, calendar_result):
        """Store a calendar result for a user."""
        created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.cursor.execute("""
            INSERT INTO calendar_results (user_id, calendar_result, created_at)
            VALUES (?, ?, ?)
        """, (user_id, calendar_result, created_at))
        self.conn.commit()
        logging.info(f"Added calendar result for user_id {user_id}")

    def get_calendar_results(self, user_id):
        """
        Retrieve calendar results for a given user, including the ID.
        Returns: List of tuples (id, calendar_result, created_at)
        """
        self.cursor.execute("""
            SELECT id, calendar_result, created_at FROM calendar_results
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def get_calendar_by_id(self, calendar_id):
        """
        Retrieve a specific calendar result by its primary key ID.
        Returns: Tuple (id, user_id, calendar_result, created_at) or None
        """
        self.cursor.execute("""
            SELECT id, user_id, calendar_result, created_at
            FROM calendar_results
            WHERE id = ?
        """, (calendar_id,))
        return self.cursor.fetchone()


    def get_summary_result_by_date(self, user_id, summary_type, date_str):
        """
        Retrieve the latest summary result for a given user, summary_type, and date.
        The date_str should be in YYYY-MM-DD format and is matched against the created_at timestamp.
        Returns: Tuple (id, summary_type, keyword, summary, created_at) or None
        """
        self.cursor.execute("""
            SELECT id, summary_type, keyword, summary, created_at
            FROM user_summaries
            WHERE user_id = ? AND summary_type = ? AND substr(created_at, 1, 10) = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, summary_type, date_str))
        return self.cursor.fetchone()

    def get_calendar_result_by_date(self, user_id, date_str):
        """
        Retrieve the latest calendar result for a given user on the specified date.
        The date_str should be in YYYY-MM-DD format and is matched against the created_at timestamp.
        Returns: Tuple (id, calendar_result, created_at) or None
        """
        self.cursor.execute("""
            SELECT id, calendar_result, created_at
            FROM calendar_results
            WHERE user_id = ? AND substr(created_at, 1, 10) = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, date_str))
        return self.cursor.fetchone()

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info(f"UserDatabase connection closed for {self.db_path}")

# --- Example Usage ---
if __name__ == "__main__":
    # Determine a default path for example usage
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

    # Use a specific example DB for testing if needed
    EXAMPLE_DB_PATH = os.path.join(project_root, 'data', 'user_data_example.db')
    print(f"Using example database: {EXAMPLE_DB_PATH}")

    # Instantiate the user database
    user_db = UserDatabase(db_path=EXAMPLE_DB_PATH)

    # Ensure 'alice' exists
    user_info = user_db.get_user("alice")
    if user_info:
        user_id = user_info[0]
        print(f"Found existing user 'alice' with ID: {user_id}")
    else:
        user_id = user_db.add_user("alice", "alice@example.com", "hashedpassword123")
        if user_id:
            print(f"Added new user 'alice' with ID: {user_id}")
        else:
            print("Failed to add or find user 'alice'. Exiting example.")
            exit()

    # --- Add sample data if needed (ensure it looks like JSON string) ---
    sample_summary_json_str = """
{
  "report": {
    "title": "Sample Market Analysis",
    "sections": [
      {
        "heading": "Current Events",
        "content": [
            {"Event Type": "CPI Release", "Relevance Rating": "Very High", "Event Date(s)": "2025-04-10", "General Overview and Summary": "CPI data came in slightly higher than expected, impacting rate cut expectations."}
        ]
      },
      {
        "heading": "Future Events",
        "content": [
             {"Event Type": "FOMC Meeting", "Relevance Rating": "Very High", "Event Date(s)": "2025-04-30", "General Overview and Summary": "Next Fed meeting to decide on interest rates."}
        ]
      },
      {
        "heading": "Portfolio Summary",
        "content": "Portfolio holds AAPL and MSFT. AAPL earnings next week."
      }
    ],
    "date_generated": "2025-04-21"
  }
}
"""
    user_db.add_summary_result(user_id, "analysis", "aggregate", sample_summary_json_str)

    sample_calendar_json_str = """
{
  "title": "Economic Calendar (April 2025 Edition)",
  "monthlyCalendar": {
    "events": [
      {
        "date": "April 10",
        "events": [ {"title": "CPI Release", "relevance": "Very High Relevance", "description": "Higher than expected."} ]
      },
      {
        "date": "April 30",
        "events": [ {"title": "FOMC Meeting", "relevance": "Very High Relevance", "description": "Rate decision."} ]
      }
    ]
  },
  "monthlyPastEventsSummary": [ {"category": "Economic Data", "description": "CPI was key."} ],
  "monthlyUpcomingEventsSummary": [ {"title": "FOMC Meeting", "relevance": "Very High Relevance", "description": "Watch for Fed guidance."} ],
  "weeklyHighlights": { "weekRange": "Week of April 21 - 27", "description": "Focus on earnings.", "upcomingEvents": [] },
  "dailyHighlights": { "date": "Monday, April 21, 2025", "todaysKeyEvents": [], "nextDayPreview": {"date": "April 22, 2025", "description": "Quiet day expected."} }
}
"""
    user_db.add_calendar_result(user_id, sample_calendar_json_str)
    # ---------------------------------------------------------------


    # Retrieve and print summary results (now includes ID)
    summaries = user_db.get_summary_results(user_id)
    print("\nSummary Results (with ID):")
    for summary in summaries:
        print(f"ID: {summary[0]}, Type: {summary[1]}, Keyword: {summary[2]}, Created: {summary[4]}")
        # print(f"  Content (start): {summary[3][:100]}...") # Print start of content

    # Retrieve and print calendar results (now includes ID)
    calendars = user_db.get_calendar_results(user_id)
    print("\nCalendar Results (with ID):")
    for calendar in calendars:
        print(f"ID: {calendar[0]}, Created: {calendar[2]}")
        # print(f"  Content (start): {calendar[1][:100]}...") # Print start of content

    # Fetch a specific summary by ID
    if summaries:
        first_summary_id = summaries[0][0]
        specific_summary = user_db.get_summary_by_id(first_summary_id)
        print(f"\nSpecific Summary (ID: {first_summary_id}):")
        if specific_summary:
            print(f"  Type: {specific_summary[2]}, Keyword: {specific_summary[3]}")
            # print(f"  Full Content: {specific_summary[4]}")
        else:
            print("  Not found.")

    # Fetch a specific calendar by ID
    if calendars:
        first_calendar_id = calendars[0][0]
        specific_calendar = user_db.get_calendar_by_id(first_calendar_id)
        print(f"\nSpecific Calendar (ID: {first_calendar_id}):")
        if specific_calendar:
            print(f"  Created: {specific_calendar[3]}")
            # print(f"  Full Content: {specific_calendar[2]}")
        else:
            print("  Not found.")

    # Close the connection when done
    user_db.close()