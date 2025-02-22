import os
import asyncio
import sqlite3
import logging
from datetime import datetime, date
from keywords import extract_portfolio_keywords, MARKET_KEYWORDS
from scrape_api import call_scrape_api
from llm_call import combine_scrape_prompt, combine_portfolio_prompt, analyze_data, create_calendar
from api import create_api_instance

# Import the UserDatabase class (assumes user_database.py defines this class with the helper methods)
from user_database import UserDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure analysis directory exists
os.makedirs("analysis", exist_ok=True)

# Create google_llm_api instance (assumed to be async-compatible)
google_llm_api = create_api_instance("google")  # For 2M tokens context size

# Global rate-limiting variables for scrape API calls
scrape_semaphore = asyncio.Semaphore(1)  # Maximum 2 concurrent calls
rate_limit_lock = asyncio.Lock()
last_scrape_call = 0.0  # Global timestamp for the last scrape call

# Define cache expiration period in hours
CACHE_EXPIRATION_HOURS = 24

# --- CacheManager Definition ---
class CacheManager:
    def __init__(self, db_path='cache.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                summary_type TEXT,
                keyword TEXT,
                summary TEXT,
                timestamp TEXT,
                UNIQUE(summary_type, keyword)
            )
        ''')
        self.conn.commit()
    
    def check_cache(self, summary_type, keyword):
        """
        Returns a cached summary if it exists and hasn’t expired based on:
          1. The stored date being today's date.
          2. The elapsed hours since storage being less than CACHE_EXPIRATION_HOURS.
          
        For example, a cache entry from 2025-02-20 will expire on 2025-02-21,
        even if less than 24 hours have passed.
        """
        self.cursor.execute('''
            SELECT summary, timestamp FROM summaries
            WHERE summary_type = ? AND keyword = ?
        ''', (summary_type, keyword))
        result = self.cursor.fetchone()
        if result:
            summary, timestamp_str = result
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError as e:
                logging.error(f"Error parsing timestamp for keyword {keyword}: {e}")
                return None

            now = datetime.now()
            # Expire if the cached entry's date is before today's date.
            if timestamp.date() < now.date():
                logging.info(f"Cache expired for {summary_type} - {keyword}: date mismatch ({timestamp.date()} vs {now.date()})")
                return None

            # Otherwise, if on the same day, check if the elapsed hours are within the limit.
            age_hours = (now - timestamp).total_seconds() / 3600
            if age_hours < CACHE_EXPIRATION_HOURS:
                logging.info(f"Cache hit for {summary_type} - {keyword} (age: {age_hours:.2f} hours)")
                return summary
            else:
                logging.info(f"Cache expired for {summary_type} - {keyword}: hour limit exceeded (age: {age_hours:.2f} hours)")
        logging.info(f"Cache miss for {summary_type} - {keyword}")
        return None
    
    def update_cache(self, summary_type, keyword, summary):
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.cursor.execute('''
            INSERT OR REPLACE INTO summaries (summary_type, keyword, summary, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (summary_type, keyword, summary, timestamp))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# Instantiate our cache manager
cache_manager = CacheManager()

# --- Asynchronous Functions ---
async def async_scrape_api(keyword):
    """
    Wraps call_scrape_api to enforce a maximum of 2 concurrent calls and at least 1 second
    between calls. Includes a timeout in case the scrape API hangs.
    """
    global last_scrape_call
    async with scrape_semaphore:
        async with rate_limit_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            wait_time = 1 - (now - last_scrape_call)
            if wait_time > 0:
                logging.info(f"Rate limiting: waiting {wait_time:.2f} seconds for keyword '{keyword}'")
                await asyncio.sleep(wait_time)
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, call_scrape_api, keyword),
                timeout=30
            )
            return result
        except Exception as e:
            logging.error(f"Error during scrape call for {keyword}: {e}")
            return "Error: Unable to scrape data."
        finally:
            # Update last_scrape_call after the API call completes
            async with rate_limit_lock:
                last_scrape_call = asyncio.get_running_loop().time()

async def generate_summary(summary_type, keyword, scrape_response):
    """
    Generate a summary using the appropriate prompt, update the cache, and return the result.
    Uses a timeout to prevent hanging on the LLM call.
    """
    if summary_type == "market":
        instructions = combine_scrape_prompt(keyword)
    elif summary_type == "portfolio":
        instructions = combine_portfolio_prompt(keyword)
    else:
        raise ValueError("Invalid summary type")
    
    prompt = instructions + "\n" + str(scrape_response)
    try:
        response = await asyncio.wait_for(
            google_llm_api.process_text(prompt.strip()),
            timeout=60
        )
    except Exception as e:
        logging.error(f"Error processing text for {keyword}: {e}")
        response = "Error: Unable to generate summary."
    
    cache_manager.update_cache(summary_type, keyword, response)
    return response

async def process_keyword(summary_type, keyword):
    """
    Check the cache for a given keyword and process it if not cached.
    """
    cached = cache_manager.check_cache(summary_type, keyword)
    if cached:
        return cached

    scrape_response = await async_scrape_api(keyword)
    # Check if the scrape_response is empty or indicates an error
    if not scrape_response or (isinstance(scrape_response, str) and scrape_response.startswith("Error:")):
        logging.error(f"Scrape API failed for keyword '{keyword}'. Skipping summary generation.")
        return f"Error: Scrape API failed for '{keyword}'. No summary generated."
    
    summary = await generate_summary(summary_type, keyword, scrape_response)
    return summary


async def analyze_summaries(summaries):
    """
    Analyze the provided summaries and save the result to a timestamped file.
    Uses a timeout to guard against hanging on the LLM call.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_filename = os.path.join("analysis", f"analyze_{timestamp}.txt")
    summaries_str = " ".join(summaries)
    instructions = analyze_data()
    prompt = instructions + "\n" + summaries_str
    try:
        response = await asyncio.wait_for(
            google_llm_api.process_text(prompt, max_tokens=16384),
            timeout=120
        )
    except Exception as e:
        logging.error(f"Error analyzing summaries: {e}")
        response = "Error: Unable to analyze summaries."
    
    with open(cache_filename, 'w', encoding='utf-8') as cache_file:
        cache_file.write(response)
    
    return response

async def create_calendar_from_analysis(analysis):
    """
    Create a calendar from the analysis and save it to a date-based file.
    Uses a timeout to guard against hanging on the LLM call.
    """
    cache_filename = os.path.join("analysis", f"{date.today()}_calendar.txt")
    instructions = create_calendar()
    prompt = instructions + "\n" + analysis
    try:
        response = await asyncio.wait_for(
            google_llm_api.process_text(prompt),
            timeout=60
        )
    except Exception as e:
        logging.error(f"Error creating calendar: {e}")
        response = "Error: Unable to create calendar."
    
    with open(cache_filename, 'w', encoding='utf-8') as cache_file:
        cache_file.write(response)
    
    return response

# --- Main Function ---
async def main():
    tasks = []
    
    # Process market keywords concurrently
    for keyword in MARKET_KEYWORDS:
        logging.info(f"Processing market keyword: {keyword}")
        tasks.append(process_keyword("market", keyword))
    
    # Process portfolio keywords concurrently
    for keyword in extract_portfolio_keywords():
        logging.info(f"Processing portfolio keyword: {keyword}")
        tasks.append(process_keyword("portfolio", keyword))
    
    # Await all processing tasks concurrently
    summaries = await asyncio.gather(*tasks)
    
    # --- Persist Results in the User Database ---
    user_db = UserDatabase()
    # For demonstration, assume the user "alice"
    user = user_db.get_user("alice")
    if user:
        user_id = user[0]
    else:
        user_id = user_db.add_user("alice", "alice@example.com", "hashedpassword123")
    
    # Use today's date as a string (YYYY-MM-DD)
    today_str = date.today().isoformat()
    
    # Check if an analysis report already exists for today.
    existing_analysis = user_db.get_summary_result_by_date(user_id, "analysis", today_str)
    if existing_analysis:
        analysis_response = existing_analysis[2]  # Assuming the third column is the summary text.
        logging.info("Using existing analysis for today.")
    else:
        print("Analyzing summaries ...")
        analysis_response = await analyze_summaries(summaries)
        logging.info(f"New analysis response: {analysis_response}")
        user_db.add_summary_result(user_id, "analysis", "aggregate", analysis_response)
    
    # Check if a calendar report already exists for today.
    existing_calendar = user_db.get_calendar_result_by_date(user_id, today_str)
    if existing_calendar:
        calendar_response = existing_calendar[0]  # Assuming the first column is the calendar result.
        logging.info("Using existing calendar for today.")
    else:
        calendar_response = await create_calendar_from_analysis(analysis_response)
        logging.info(f"New calendar response: {calendar_response}")
        user_db.add_calendar_result(user_id, calendar_response)
    
    # Clean up the cache and user database connections
    cache_manager.close()
    user_db.close()

if __name__ == "__main__":
    asyncio.run(main())
