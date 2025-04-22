# src/market_research/main.py
import os
import asyncio
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# Local Imports (ensure these are correct relative imports)
from .core.keywords import extract_portfolio_keywords, MARKET_KEYWORDS
from .prompts import combine_scrape_prompt, combine_portfolio_prompt, analyze_data, create_calendar
from .api.openai_api import OpenAIAPI
from .api.api_tool_factory import ApiToolFactory
from .core.user_database import UserDatabase
from .core.call_cache import CacheManager
from .config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logging.getLogger('openai').setLevel(logging.WARNING)

# --- Project Paths and Dirs ---
# Use absolute path based on config's project_root
project_root = getattr(config, 'project_root', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
analysis_dir = os.path.join(project_root, "analysis")
os.makedirs(analysis_dir, exist_ok=True)
PORTFOLIO_PATH = config.PORTFOLIO_PATH # Assumes config resolves this correctly

# --- Instantiate API, Cache Manager ---
SEARCH_MODEL = config.GPT_SEARCH_MODEL
OPENAI_MODEL = config.GPT_MODEL
MAX_TOKENS = 8192
tool_factory = ApiToolFactory()
openai_api = OpenAIAPI(tool_factory=tool_factory, model=OPENAI_MODEL)
cache_manager = CacheManager(db_path=config.CACHE_DB_PATH)

# --- Concurrency Limiter ---
API_CONCURRENCY_LIMIT = 2
api_semaphore = asyncio.Semaphore(API_CONCURRENCY_LIMIT)
logging.info(f"API concurrency limit set to: {API_CONCURRENCY_LIMIT}")

# --- Helper function ---
def is_error_response(response: Optional[str]) -> bool:
    if response is None: return True
    return response.strip().startswith(("[Error:", "[Warning:", "Error:"))


# --- Async Functions (generate_summary, process_keyword, analyze_summaries, create_calendar) ---
async def generate_summary(summary_type: str, keyword: str, semaphore: asyncio.Semaphore) -> Optional[str]:
    logging.info(f"Requesting summary generation for type '{summary_type}', keyword: '{keyword}'")
    if summary_type == "market":
        system_prompt = combine_scrape_prompt(keyword)
    elif summary_type == "portfolio":
        system_prompt = combine_portfolio_prompt(keyword)
    else:
        return f"[Error: Invalid summary type '{summary_type}']"

    initial_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Please provide the report for: {keyword}"}]
    response = None
    try:
        logging.debug(f"Waiting to acquire semaphore for keyword: '{keyword}'")
        async with semaphore:
            logging.info(f"Semaphore acquired, calling API for keyword: '{keyword}'")
            response = await asyncio.wait_for(
                openai_api.generate_text_with_tools(
                    messages=initial_messages,
                    model=SEARCH_MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=0.5,
                    max_tool_iterations=3,
                    web_search_options={},
                ),
                timeout=180.0,
            )
        logging.debug(f"Semaphore released for keyword: '{keyword}'")

        if is_error_response(response):
            logging.warning(f"API call for '{keyword}' returned error: {response}")
            return response
        if response:
            logging.info(f"Successfully generated summary for keyword: '{keyword}'")
            cache_manager.update_cache(summary_type, keyword, response)
            return response
        else:
            logging.warning(f"No content returned for keyword: '{keyword}' (not error).")
            return "[Error: Failed to generate summary (empty response).]"
    except asyncio.TimeoutError:
        logging.error(f"Timeout generating summary for keyword: '{keyword}'")
        return f"[Error: Timeout generating summary for '{keyword}']"
    except Exception as e:
        logging.exception(f"Error generating summary for keyword '{keyword}': {e}")
        return f"[Error: Exception during summary generation for '{keyword}' - {type(e).__name__}]"


async def process_keyword(summary_type: str, keyword: str, semaphore: asyncio.Semaphore) -> Optional[str]:
    logging.info(f"Processing keyword '{keyword}' (type: {summary_type})")
    cached = cache_manager.check_cache(summary_type, keyword)
    if cached and not is_error_response(cached):
        logging.info(f"Cache hit for '{keyword}'.")
        return cached
    elif cached:
        logging.warning(f"Cached item for '{keyword}' is error message. Regenerating.")
    logging.info(f"Cache miss/expired for '{keyword}'. Generating new summary...")
    return await generate_summary(summary_type, keyword, semaphore)

async def analyze_summaries(summaries: List[str]) -> Optional[str]:
    logging.info("Analyzing summaries...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(analysis_dir, f"analyze_{timestamp}.txt")
    summaries_str = "\n---\n".join(filter(None, summaries))
    if not summaries_str.strip():
        logging.warning("No valid summaries for analysis.")
        return "[Error: No summaries available to analyze.]"
    instructions = analyze_data()
    messages = [{"role": "system", "content": instructions}, {"role": "user", "content": summaries_str}]
    try:
        async with api_semaphore:
            logging.info("Semaphore acquired, calling API for analysis")
            response = await asyncio.wait_for(
                openai_api.generate_text_with_tools(
                    messages=messages,
                    model=OPENAI_MODEL,
                    max_completion_tokens=16384,
                ),
                timeout=120.0,
            )
        logging.debug("Semaphore released for analysis")
        if is_error_response(response):
            logging.warning(f"Analysis generation returned error: {response}")
            return response
        if response:
            logging.info(f"Analysis generated. Saving to {output_filename}")
            with open(output_filename, 'w', encoding='utf-8') as f: f.write(response)
            return response
        else:
            logging.warning("Analysis generation empty (not error).")
            return "[Error: Analysis generation failed (empty response).]"
    except asyncio.TimeoutError:
        logging.error("Timeout during analysis.")
        return "[Error: Timeout during analysis.]"
    except Exception as e:
        logging.exception(f"Error analyzing summaries: {e}")
        return f"[Error: Exception during analysis - {type(e).__name__}]"

async def create_calendar_from_analysis(analysis: str) -> Optional[str]:
    logging.info("Creating calendar from analysis...")
    output_filename = os.path.join(analysis_dir, f"{date.today().isoformat()}_calendar.txt")
    if is_error_response(analysis):
        logging.warning("Invalid analysis. Skipping calendar creation.")
        return "[Error: Cannot create calendar from invalid analysis.]"
    instructions = create_calendar()
    messages = [{"role": "system", "content": instructions}, {"role": "user", "content": analysis}]
    try:
        async with api_semaphore:  # Use semaphore
            logging.info("Semaphore acquired, calling API for calendar creation")
            response = await asyncio.wait_for(
                openai_api.generate_text_with_tools(
                    messages=messages,
                    model=OPENAI_MODEL,
                    max_completion_tokens=16384,
                ),
                timeout=90.0,
            )
        logging.debug("Semaphore released for calendar creation")
        if is_error_response(response):
            logging.warning(f"Calendar creation returned error: {response}")
            return response
        if response:
            logging.info(f"Calendar created. Saving to {output_filename}")
            with open(output_filename, 'w', encoding='utf-8') as f: f.write(response)
            return response
        else:
            logging.warning("Calendar creation empty (not error).")
            return "[Error: Calendar creation failed (empty response).]"
    except asyncio.TimeoutError:
        logging.error("Timeout during calendar creation.")
        return "[Error: Timeout during calendar creation.]"
    except Exception as e:
        logging.exception(f"Error creating calendar: {e}")
        return f"[Error: Exception during calendar creation - {type(e).__name__}]"

# --- Main Function ---
async def main():
    start_time = datetime.now()
    logging.info(f"Main process started at {start_time}")

    user_db = None # Initialize user_db
    user_id = None # Initialize user_id

    try:
        # --- Instantiate DB and Get User ID ONCE ---
        logging.info(f"Connecting to user database: {config.USER_DB_PATH}")
        user_db = UserDatabase(db_path=config.USER_DB_PATH)
        target_username = "alice" # Or get from config/args
        user = user_db.get_user(target_username)
        if user:
            user_id = user[0]
            logging.info(f"Found user '{target_username}' with ID: {user_id}")
        else:
            logging.info(f"User '{target_username}' not found, attempting to add.")
            # Use a placeholder hash - replace with real hashing in production
            user_id = user_db.add_user(target_username, f"{target_username}@example.com", "dummy_password_hash")
            if user_id:
                logging.info(f"Created user '{target_username}' with ID: {user_id}")
            else:
                 # If add_user returns None (e.g., DB error), we should stop
                 logging.error(f"Failed to get or create user '{target_username}'. Cannot proceed.")
                 # Close DB connection before returning
                 if user_db: user_db.close()
                 return # Exit if user cannot be established

        # --- Get Keywords ---
        all_market_keywords = []
        portfolio_keywords = []
        try:
            for period_keywords in MARKET_KEYWORDS.values():
                all_market_keywords.extend(period_keywords)
            portfolio_keywords = extract_portfolio_keywords(portfolio_file_path=PORTFOLIO_PATH)
            logging.info(f"Loaded {len(all_market_keywords)} market keywords and {len(portfolio_keywords)} portfolio keywords.")
        except Exception as e:
            logging.exception(f"Error loading keywords: {e}")
            # Close DB connection before returning
            if user_db: user_db.close()
            return # Exit if keywords are essential

        # --- Schedule Keyword Processing Tasks ---
        tasks = []
        keywords_processed = set()
        all_keywords_with_type = []
        for keyword in all_market_keywords:
            if keyword not in keywords_processed:
                task = asyncio.create_task(process_keyword("market", keyword, api_semaphore))
                tasks.append(task)
                keywords_processed.add(keyword)
                all_keywords_with_type.append(("market", keyword))
        for keyword in portfolio_keywords:
            if keyword not in keywords_processed:
                task = asyncio.create_task(process_keyword("portfolio", keyword, api_semaphore))
                tasks.append(task)
                keywords_processed.add(keyword)
                all_keywords_with_type.append(("portfolio", keyword))

        logging.info(f"Gathering results for {len(tasks)} keywords using {API_CONCURRENCY_LIMIT} concurrent API workers...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # --- Process Results & Save Individual Summaries ---
        valid_summaries = []
        logging.info("Processing gathered results...")
        for i, result in enumerate(results):
            if i < len(all_keywords_with_type):
                summary_type, keyword = all_keywords_with_type[i]
                if isinstance(result, asyncio.CancelledError):
                    logging.warning(f"Task for '{keyword}' cancelled.")
                elif isinstance(result, Exception):
                    logging.error(f"Task for '{keyword}' failed: {result}", exc_info=False)
                elif is_error_response(result):
                    logging.warning(f"Task for '{keyword}' returned error: {result}")
                elif result:
                    valid_summaries.append(result)
                    # --- Save individual summary using the EXISTING user_db instance ---
                    try:
                        logging.debug(f"Attempting to save individual summary for '{keyword}'")
                        # user_id is already known from the start
                        user_db.add_summary_result(user_id, summary_type, keyword, result)
                        logging.debug(f"Successfully saved individual summary for '{keyword}'")
                    except Exception as db_err:
                        # Log specific DB error, but don't stop the whole process
                        logging.error(f"Failed to save individual summary for '{keyword}' to DB: {db_err}", exc_info=True)
                else:
                    logging.warning(f"Task for '{keyword}' returned None/empty without error.")
            else:
                logging.error(f"Result index {i} out of bounds for keyword tracking.")

        logging.info(f"Finished processing keywords. {len(valid_summaries)} valid summaries obtained.")

        # --- Analysis ---
        analysis_response = "[Error: Analysis skipped - no valid summaries.]"
        if valid_summaries:
            logging.info("Analyzing summaries...")
            analysis_response = await analyze_summaries(valid_summaries)
            logging.info("Analysis response received.")
            if not is_error_response(analysis_response):
                 user_db.add_summary_result(user_id, "analysis", "aggregate", analysis_response)
                 logging.info("Saved analysis result to database.")
            else:
                 logging.error(f"Analysis error, NOT saving to DB: {analysis_response}")
        else:
             logging.warning("No valid summaries generated, skipping analysis.")

        # --- Calendar ---
        calendar_response = "[Error: Calendar skipped - invalid analysis.]"
        if not is_error_response(analysis_response):
            logging.info("Creating calendar...")
            calendar_response = await create_calendar_from_analysis(analysis_response)
            logging.info("Calendar response received.")
            if not is_error_response(calendar_response):
                user_db.add_calendar_result(user_id, calendar_response)
                logging.info("Saved calendar result to database.")
            else:
                logging.error(f"Calendar error, NOT saving to DB: {calendar_response}")
        else:
            logging.warning("Analysis errors or skipped, skipping calendar creation.")

    except Exception as e:
        # Catch errors during the main setup or processing phases
        logging.exception(f"An error occurred in the main execution block: {e}")
    finally:
        # Ensure the database connection is closed cleanly
        if user_db:
            user_db.close()
            logging.info("User database connection closed.")

    end_time = datetime.now()
    logging.info(f"Main process finished at {end_time}. Duration: {end_time - start_time}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
    except Exception as e:
        logging.exception("An unexpected error occurred running the main loop.")
