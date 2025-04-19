# main.py
import os
import asyncio
import sqlite3
import logging
from datetime import datetime, date
from typing import List, Dict, Any # Added typing imports

# Local Imports
from keywords import extract_portfolio_keywords, MARKET_KEYWORDS
from llm_call import combine_scrape_prompt, combine_portfolio_prompt, analyze_data, create_calendar
# --- API and Tool Factory Imports ---
from api import OpenAIAPI  # Import the correct class
from api.api_tool_factory import ApiToolFactory # Import the factory
# --- User Database Import ---
from user_database import UserDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger('openai').setLevel(logging.WARNING) # Quieten OpenAI library logs if desired

# Ensure analysis directory exists
os.makedirs("analysis", exist_ok=True)

# --- Instantiate API with Tool Factory ---
# Use a model that supports tool calling and web search
OPENAI_MODEL = "gpt-4o-mini" # Or "gpt-4-turbo", "gpt-4o" etc.
tool_factory = ApiToolFactory()
openai_api = OpenAIAPI(tool_factory=tool_factory, model=OPENAI_MODEL)
# -----------------------------------------

# Define cache expiration period in hours
CACHE_EXPIRATION_HOURS = 24 # Keep cache logic

# --- CacheManager Definition (Keep as is) ---
class CacheManager:
    def __init__(self, db_path='cache.db'):
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

# Instantiate our cache manager
cache_manager = CacheManager()

# --- Remove Old Scraping Logic ---
# Delete async_search_api, async_scrape_api, and related globals

# --- Modified Asynchronous Functions ---

async def generate_summary(summary_type: str, keyword: str) -> str:
    """
    Generates a summary using the OpenAI API with web search tool.
    The LLM is instructed to perform the search and synthesize results.
    """
    logging.info(f"Generating summary for type '{summary_type}', keyword: '{keyword}'")
    if summary_type == "market":
        system_prompt = combine_scrape_prompt(keyword)
    elif summary_type == "portfolio":
        system_prompt = combine_portfolio_prompt(keyword)
    else:
        logging.error(f"Invalid summary type requested: {summary_type}")
        raise ValueError("Invalid summary type")

    # Construct initial messages: System prompt guides the task, user message provides the keyword/topic.
    initial_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please provide the report for: {keyword}"}
    ]

    try:
        # Use the generate_text_with_tools method. It handles the tool call loop.
        # We expect the model to use the built-in web_search tool based on the prompt.
        # Set a reasonable timeout for the entire process.
        response = await asyncio.wait_for(
            openai_api.generate_text_with_tools(
                messages=initial_messages,
                model=OPENAI_MODEL, # Use the configured model
                max_tokens=4096, # Adjust as needed
                temperature=0.5, # Lower temperature for factual synthesis
                max_tool_iterations=3 # Limit iterations in case of loops
            ),
            timeout=180.0 # e.g., 3 minutes timeout for search + generation
        )

        if response:
            logging.info(f"Successfully generated summary for keyword: '{keyword}'")
            cache_manager.update_cache(summary_type, keyword, response)
            return response
        else:
            logging.warning(f"No content returned from generate_text_with_tools for keyword: '{keyword}'")
            # Cache an error message or empty string?
            error_msg = "Error: Failed to generate summary (no content)."
            cache_manager.update_cache(summary_type, keyword, error_msg)
            return error_msg # Return error message

    except asyncio.TimeoutError:
        logging.error(f"Timeout generating summary for keyword: '{keyword}'")
        error_msg = "Error: Timeout generating summary."
        cache_manager.update_cache(summary_type, keyword, error_msg)
        return error_msg
    except Exception as e:
        logging.exception(f"Error generating summary for keyword '{keyword}': {e}")
        error_msg = f"Error: Exception during summary generation - {type(e).__name__}"
        cache_manager.update_cache(summary_type, keyword, error_msg)
        return error_msg # Return error message


async def process_keyword(summary_type: str, keyword: str) -> str:
    """
    Checks cache, and if missed/expired, calls generate_summary to get data via web search tool.
    """
    logging.info(f"Processing keyword '{keyword}' (type: {summary_type})")
    cached = cache_manager.check_cache(summary_type, keyword)
    if cached:
        return cached

    logging.info(f"Cache miss/expired for '{keyword}'. Generating new summary...")
    # Directly call generate_summary, which now handles the search internally
    summary = await generate_summary(summary_type, keyword)
    return summary # Return the generated summary (or error message)


async def analyze_summaries(summaries: List[str]) -> str:
    """
    Analyzes the provided summaries using the OpenAI API.
    """
    logging.info("Analyzing summaries...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join("analysis", f"analyze_{timestamp}.txt")
    summaries_str = "\n---\n".join(filter(None, summaries)) # Join summaries, skip None/empty

    if not summaries_str.strip():
        logging.warning("No valid summaries provided for analysis.")
        return "Error: No summaries available to analyze."

    instructions = analyze_data() # Get the analysis prompt

    # Construct messages for the analysis task
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": summaries_str}
    ]

    try:
        # Call the API. Tool usage is not expected here, but use the same method for consistency.
        response = await asyncio.wait_for(
            openai_api.generate_text_with_tools(
                messages=messages,
                model=OPENAI_MODEL, # Can use the same model or a different one if needed
                max_tokens=4096, # Adjust as needed, analysis might be long
                temperature=0.5,
                max_tool_iterations=1 # Should not need tools here
            ),
            timeout=120.0 # 2 minutes timeout
        )

        if response:
            logging.info(f"Analysis generated successfully. Saving to {output_filename}")
            # Ensure directory exists before writing
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response)
            return response
        else:
             logging.warning("Analysis generation returned no content.")
             return "Error: Analysis generation failed (no content)."

    except asyncio.TimeoutError:
        logging.error("Timeout during summary analysis.")
        return "Error: Timeout during analysis."
    except Exception as e:
        logging.exception(f"Error analyzing summaries: {e}")
        return f"Error: Exception during analysis - {type(e).__name__}"


async def create_calendar_from_analysis(analysis: str) -> str:
    """
    Creates a calendar from the analysis using the OpenAI API.
    """
    logging.info("Creating calendar from analysis...")
    output_filename = os.path.join("analysis", f"{date.today().isoformat()}_calendar.txt")

    if not analysis or analysis.startswith("Error:") :
        logging.warning("Analysis is empty or contains an error. Skipping calendar creation.")
        return "Error: Cannot create calendar from invalid or missing analysis."

    instructions = create_calendar() # Get the calendar prompt

    # Construct messages for the calendar task
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": analysis}
    ]

    try:
        # Call the API. Tool usage is not expected here.
        response = await asyncio.wait_for(
            openai_api.generate_text_with_tools(
                messages=messages,
                model=OPENAI_MODEL,
                max_tokens=4096, # Calendar output can be large
                temperature=0.3, # More deterministic for structured output
                max_tool_iterations=1 # Should not need tools
            ),
            timeout=90.0 # 1.5 minutes timeout
        )

        if response:
            logging.info(f"Calendar created successfully. Saving to {output_filename}")
            # Ensure directory exists before writing
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response)
            return response
        else:
            logging.warning("Calendar creation returned no content.")
            return "Error: Calendar creation failed (no content)."

    except asyncio.TimeoutError:
        logging.error("Timeout during calendar creation.")
        return "Error: Timeout during calendar creation."
    except Exception as e:
        logging.exception(f"Error creating calendar: {e}")
        return f"Error: Exception during calendar creation - {type(e).__name__}"

# --- Main Function (Modified) ---
async def main():
    start_time = datetime.now()
    logging.info(f"Main process started at {start_time}")

    tasks = []
    keywords_processed = set() # To avoid duplicate processing if keywords overlap

    # Combine all keywords first
    all_market_keywords = []
    for period_keywords in MARKET_KEYWORDS.values():
        all_market_keywords.extend(period_keywords)

    portfolio_keywords = extract_portfolio_keywords()

    # Schedule market keyword processing
    for keyword in all_market_keywords:
        if keyword not in keywords_processed:
            logging.debug(f"Queueing market keyword: {keyword}")
            tasks.append(process_keyword("market", keyword))
            keywords_processed.add(keyword)
        else:
            logging.debug(f"Skipping duplicate market keyword: {keyword}")


    # Schedule portfolio keyword processing
    for keyword in portfolio_keywords:
        if keyword not in keywords_processed:
            logging.debug(f"Queueing portfolio keyword: {keyword}")
            tasks.append(process_keyword("portfolio", keyword))
            keywords_processed.add(keyword)
        else:
            logging.debug(f"Skipping duplicate portfolio keyword: {keyword}")

    # Await all summary generation tasks concurrently
    logging.info(f"Gathering results for {len(tasks)} keywords...")
    summaries = await asyncio.gather(*tasks, return_exceptions=True) # Capture exceptions too

    # Filter out exceptions and log them
    valid_summaries = []
    for i, result in enumerate(summaries):
        task_keyword = list(keywords_processed)[i] # Note: Order depends on gather preserving task order
        if isinstance(result, Exception):
            logging.error(f"Task for keyword '{task_keyword}' failed: {result}")
        elif isinstance(result, str) and result.startswith("Error:"):
             logging.warning(f"Task for keyword '{task_keyword}' resulted in an error message: {result}")
             # Optionally decide whether to include error messages in the analysis
             # valid_summaries.append(result) # Or skip
        elif result:
            valid_summaries.append(result)
        else:
            logging.warning(f"Task for keyword '{task_keyword}' returned None or empty.")


    logging.info(f"Finished processing keywords. {len(valid_summaries)} valid summaries obtained.")

    # --- Persist Results in the User Database (Keep as is, but handle potential errors) ---
    # For demonstration, assume user "alice"
    user_db = UserDatabase()
    try: # Add try/finally for db connection
        user = user_db.get_user("alice")
        if user:
            user_id = user[0]
        else:
            logging.info("User 'alice' not found, adding new user.")
            user_id = user_db.add_user("alice", "alice@example.com", "hashedpassword123") # Example password hashing needed in real app

        if user_id is None:
             logging.error("Failed to get or create user 'alice'. Cannot proceed with DB operations.")
             return # Stop if user cannot be established

        today_str = date.today().isoformat()

        # --- Analysis ---
        analysis_response = "Error: Analysis skipped due to previous errors or no summaries." # Default error
        if valid_summaries:
             existing_analysis = user_db.get_summary_result_by_date(user_id, "analysis", today_str)
             if existing_analysis:
                 analysis_response = existing_analysis[2] # Assuming the third column is the summary text
                 logging.info("Using existing analysis from database for today.")
             else:
                 logging.info("Analyzing summaries...")
                 analysis_response = await analyze_summaries(valid_summaries)
                 logging.info(f"Analysis response generated.")
                 if not analysis_response.startswith("Error:"):
                     user_db.add_summary_result(user_id, "analysis", "aggregate", analysis_response)
                 else:
                     logging.error(f"Failed to generate analysis: {analysis_response}")
        else:
             logging.warning("No valid summaries generated, skipping analysis.")


        # --- Calendar ---
        calendar_response = "Error: Calendar skipped due to invalid analysis." # Default error
        if not analysis_response.startswith("Error:"):
            existing_calendar = user_db.get_calendar_result_by_date(user_id, today_str)
            if existing_calendar:
                calendar_response = existing_calendar[0] # Assuming the first column is the calendar result
                logging.info("Using existing calendar from database for today.")
            else:
                logging.info("Creating calendar...")
                calendar_response = await create_calendar_from_analysis(analysis_response)
                logging.info(f"Calendar response generated.")
                if not calendar_response.startswith("Error:"):
                    user_db.add_calendar_result(user_id, calendar_response)
                else:
                    logging.error(f"Failed to create calendar: {calendar_response}")
        else:
            logging.warning("Analysis contains errors, skipping calendar creation.")

    finally:
        # Ensure database connection is closed
        user_db.close()
        logging.info("User database connection closed.")
        # cache_manager.close() # Close if managing persistent connection

    end_time = datetime.now()
    logging.info(f"Main process finished at {end_time}. Duration: {end_time - start_time}")


if __name__ == "__main__":
    # Consider adding proper argument parsing or config file loading here
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
    except Exception as e:
        logging.exception("An unexpected error occurred in the main execution loop.")