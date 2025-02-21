# user_database.py
import sqlite3
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class UserDatabase:
    def __init__(self, db_path="user_data.db"):
        self.db_path = db_path
        # Connect to the database (or create it if it doesn't exist)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Enable foreign key constraints
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self.create_tables()
    
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
                summary TEXT,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Create the calendar_results table to store calendar outputs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                calendar_result TEXT,
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
            logging.error(f"Error adding user '{username}': {e}")
            return None

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
        Retrieve summary results for a given user.
        Optionally filter by summary_type (e.g., "market" or "portfolio").
        """
        if summary_type:
            self.cursor.execute("""
                SELECT summary_type, keyword, summary, created_at
                FROM user_summaries
                WHERE user_id = ? AND summary_type = ?
                ORDER BY created_at DESC
            """, (user_id, summary_type))
        else:
            self.cursor.execute("""
                SELECT summary_type, keyword, summary, created_at
                FROM user_summaries
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        return self.cursor.fetchall()
    
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
        """Retrieve calendar results for a given user."""
        self.cursor.execute("""
            SELECT calendar_result, created_at FROM calendar_results
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def get_summary_result_by_date(self, user_id, summary_type, date_str):
        """
        Retrieve the latest summary result for a given user, summary_type, and date.
        The date_str should be in YYYY-MM-DD format and is matched against the created_at timestamp.
        """
        self.cursor.execute("""
            SELECT summary_type, keyword, summary, created_at
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
        """
        self.cursor.execute("""
            SELECT calendar_result, created_at
            FROM calendar_results
            WHERE user_id = ? AND substr(created_at, 1, 10) = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, date_str))
        return self.cursor.fetchone()
    
    def close(self):
        self.conn.close()

# --- Example Usage ---
if __name__ == "__main__":
    # Instantiate the user database
    user_db = UserDatabase()
    
    # Add a user or retrieve existing one
    user_id = user_db.add_user("alice", "alice@example.com", "hashedpassword123")
    if user_id is None:
        user = user_db.get_user("alice")
        if user:
            user_id = user[0]
    
    # Update the user's portfolio
    user_db.update_portfolio(user_id, '{"stocks": ["AAPL", "GOOGL", "MSFT"]}')
    
    # Add a summary result for the user
    user_db.add_summary_result(user_id, "market", "AAPL", "Apple summary result example.")
    
    # Add a calendar result for the user
    user_db.add_calendar_result(user_id, "Calendar event: Quarterly Earnings Call")
    
    # Retrieve and print the portfolio
    portfolio = user_db.get_portfolio(user_id)
    print("Portfolio:", portfolio)
    
    # Retrieve and print summary results
    summaries = user_db.get_summary_results(user_id)
    print("Summary Results:")
    for summary in summaries:
        print(summary)
    
    # Retrieve and print calendar results
    calendars = user_db.get_calendar_results(user_id)
    print("Calendar Results:")
    for calendar in calendars:
        print(calendar)
    
    # Retrieve a summary result by date (using today's date)
    today = datetime.now().strftime("%Y-%m-%d")
    analysis_today = user_db.get_summary_result_by_date(user_id, "analysis", today)
    print("Today's Analysis:", analysis_today)
    
    # Retrieve a calendar result by date (using today's date)
    calendar_today = user_db.get_calendar_result_by_date(user_id, today)
    print("Today's Calendar:", calendar_today)
    
    # Close the connection when done
    user_db.close()
