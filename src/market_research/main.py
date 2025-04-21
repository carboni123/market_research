# main.py
import os
import asyncio
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional # Added Optional

# Local Imports
from core.keywords import extract_portfolio_keywords, MARKET_KEYWORDS
from prompts import combine_scrape_prompt, combine_portfolio_prompt, analyze_data, create_calendar
# --- API and Tool Factory Imports ---
from api.openai_api import OpenAIAPI
from api.api_tool_factory import ApiToolFactory
# --- User Database Import ---
from core.user_database import UserDatabase
from core.call_cache import CacheManager

from config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger('openai').setLevel(logging.WARNING) # Quieten OpenAI library logs if desired

# Ensure analysis directory exists
os.makedirs("analysis", exist_ok=True)

PORTFOLIO_PATH = config.PORTFOLIO_PATH

# --- Instantiate API with Tool Factory ---
# Use a model that supports tool calling and web search
OPENAI_MODEL = config.GPT_MODEL
MAX_TOKENS = 8192
tool_factory = ApiToolFactory()
openai_api = OpenAIAPI(tool_factory=tool_factory, model=OPENAI_MODEL)
# -----------------------------------------
# Instantiate our cache manager
cache_manager = CacheManager(db_path=config.CACHE_DB_PATH)

# --- Helper function to check for error responses ---
def is_error_response(response: Optional[str]) -> bool:
    """Checks if the response string indicates an error from the API or processing."""
    if response is None:
        return True
    # Check for common error prefixes used in openai_api.py and main.py
    response_strip = response.strip()
    return response_strip.startswith(("[Error:", "[Warning:", "Error:"))

# --- Asynchronous Functions ---
async def generate_summary(summary_type: str, keyword: str) -> Optional[str]: # Return Optional[str]
    """
    Generates a summary using the OpenAI API with web search tool.
    Returns the summary text on success, or an error string on failure.
    """
    logging.info(f"Generating summary for type '{summary_type}', keyword: '{keyword}'")
    if summary_type == "market":
        system_prompt = combine_scrape_prompt(keyword)
    elif summary_type == "portfolio":
        system_prompt = combine_portfolio_prompt(keyword)
    else:
        logging.error(f"Invalid summary type requested: {summary_type}")
        raise ValueError("Invalid summary type")

    initial_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please provide the report for: {keyword}"}
    ]

    try:
        response = await asyncio.wait_for(
            openai_api.generate_text_with_tools(
                messages=initial_messages,
                model=OPENAI_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=0.5,
                max_tool_iterations=3
            ),
            timeout=180.0
        )

        # Check if the response itself indicates an error from the API layer
        if is_error_response(response):
            logging.warning(f"API call for keyword '{keyword}' returned an error response: {response}")
            # DO NOT cache error responses as valid results
            # cache_manager.update_cache(summary_type, keyword, response) # REMOVED
            return response # Propagate the error message

        if response: # Should be a valid summary if not an error response
            logging.info(f"Successfully generated summary for keyword: '{keyword}'")
            cache_manager.update_cache(summary_type, keyword, response) # Cache successful result
            return response
        else:
            # This case (empty but not error) might be unlikely with current API checks
            logging.warning(f"No content returned from generate_text_with_tools for keyword: '{keyword}', but not flagged as error.")
            error_msg = "Error: Failed to generate summary (empty response)."
            # DO NOT cache this error state either
            # cache_manager.update_cache(summary_type, keyword, error_msg) # REMOVED
            return error_msg # Return error message

    except asyncio.TimeoutError:
        logging.error(f"Timeout generating summary for keyword: '{keyword}'")
        error_msg = f"[Error: Timeout generating summary for '{keyword}']" # Use consistent format
        # DO NOT cache error responses
        # cache_manager.update_cache(summary_type, keyword, error_msg) # REMOVED
        return error_msg
    except Exception as e:
        logging.exception(f"Error generating summary for keyword '{keyword}': {e}")
        error_msg = f"[Error: Exception during summary generation for '{keyword}' - {type(e).__name__}]"
        # DO NOT cache error responses
        # cache_manager.update_cache(summary_type, keyword, error_msg) # REMOVED
        return error_msg


async def process_keyword(summary_type: str, keyword: str) -> Optional[str]: # Return Optional[str]
    """
    Checks cache, and if missed/expired, calls generate_summary.
    Returns the valid summary or an error string.
    """
    logging.info(f"Processing keyword '{keyword}' (type: {summary_type})")
    cached = cache_manager.check_cache(summary_type, keyword)

    # Check if the cached result itself is an old error message (if we decide to cache them)
    # For now, assuming cache only stores valid data based on changes in generate_summary
    if cached and not is_error_response(cached): # Ensure cached item isn't an error itself
        return cached
    elif cached:
        logging.warning(f"Found cached item for '{keyword}', but it appears to be an error message. Regenerating.")


    logging.info(f"Cache miss/expired or invalid cache for '{keyword}'. Generating new summary...")
    summary = await generate_summary(summary_type, keyword)
    # The summary returned by generate_summary is either valid content or an error string
    return summary


async def analyze_summaries(summaries: List[str]) -> Optional[str]: # Return Optional[str]
    """
    Analyzes the provided summaries using the OpenAI API.
    Returns analysis text on success, or an error string on failure.
    """
    logging.info("Analyzing summaries...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join("analysis", f"analyze_{timestamp}.txt")
    summaries_str = "\n---\n".join(filter(None, summaries))

    if not summaries_str.strip():
        logging.warning("No valid summaries provided for analysis.")
        return "[Error: No summaries available to analyze.]" # Use consistent format

    instructions = analyze_data()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": summaries_str}
    ]

    try:
        response = await asyncio.wait_for(
            openai_api.generate_text_with_tools(
                messages=messages,
                model=OPENAI_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=0.5,
                max_tool_iterations=1
            ),
            timeout=120.0
        )

        # Check if the response indicates an error
        if is_error_response(response):
            logging.warning(f"Analysis generation returned an error response: {response}")
            return response # Propagate error

        if response: # Valid analysis
            logging.info(f"Analysis generated successfully. Saving to {output_filename}")
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response)
            return response
        else:
             logging.warning("Analysis generation returned no content, but not flagged as error.")
             return "[Error: Analysis generation failed (empty response).]" # Consistent format

    except asyncio.TimeoutError:
        logging.error("Timeout during summary analysis.")
        return "[Error: Timeout during analysis.]" # Consistent format
    except Exception as e:
        logging.exception(f"Error analyzing summaries: {e}")
        return f"[Error: Exception during analysis - {type(e).__name__}]" # Consistent format


async def create_calendar_from_analysis(analysis: str) -> Optional[str]: # Return Optional[str]
    """
    Creates a calendar from the analysis using the OpenAI API.
    Returns calendar text on success, or an error string on failure.
    """
    logging.info("Creating calendar from analysis...")
    output_filename = os.path.join("analysis", f"{date.today().isoformat()}_calendar.txt")

    # Check if the input analysis itself is an error
    if is_error_response(analysis):
        logging.warning("Analysis contains an error. Skipping calendar creation.")
        return "[Error: Cannot create calendar from invalid analysis.]" # Consistent format

    instructions = create_calendar()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": analysis}
    ]

    try:
        response = await asyncio.wait_for(
            openai_api.generate_text_with_tools(
                messages=messages,
                model=OPENAI_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=0.3,
                max_tool_iterations=1
            ),
            timeout=90.0
        )

        # Check if the response indicates an error
        if is_error_response(response):
             logging.warning(f"Calendar creation returned an error response: {response}")
             return response # Propagate error

        if response: # Valid calendar
            logging.info(f"Calendar created successfully. Saving to {output_filename}")
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response)
            return response
        else:
            logging.warning("Calendar creation returned no content, but not flagged as error.")
            return "[Error: Calendar creation failed (empty response).]" # Consistent format

    except asyncio.TimeoutError:
        logging.error("Timeout during calendar creation.")
        return "[Error: Timeout during calendar creation.]" # Consistent format
    except Exception as e:
        logging.exception(f"Error creating calendar: {e}")
        return f"[Error: Exception during calendar creation - {type(e).__name__}]" # Consistent format

# --- Main Function (Modified) ---
async def main():
    start_time = datetime.now()
    logging.info(f"Main process started at {start_time}")

    tasks = []
    keywords_processed = set()

    all_market_keywords = []
    for period_keywords in MARKET_KEYWORDS.values():
        all_market_keywords.extend(period_keywords)

    portfolio_keywords = extract_portfolio_keywords(portfolio_file_path=PORTFOLIO_PATH)

    # Schedule keyword processing
    all_keywords_with_type = []
    for keyword in all_market_keywords[:1]:
        if keyword not in keywords_processed:
            logging.debug(f"Queueing market keyword: {keyword}")
            tasks.append(process_keyword("market", keyword))
            keywords_processed.add(keyword)
            all_keywords_with_type.append(("market", keyword)) # Keep track for logging
        else:
            logging.debug(f"Skipping duplicate market keyword: {keyword}")

    # for keyword in portfolio_keywords:
    #     if keyword not in keywords_processed:
    #         logging.debug(f"Queueing portfolio keyword: {keyword}")
    #         tasks.append(process_keyword("portfolio", keyword))
    #         keywords_processed.add(keyword)
    #         all_keywords_with_type.append(("portfolio", keyword)) # Keep track for logging
    #     else:
    #         logging.debug(f"Skipping duplicate portfolio keyword: {keyword}")

    logging.info(f"Gathering results for {len(tasks)} keywords...")
    results = await asyncio.gather(*tasks, return_exceptions=True) # Gather results

    # --- Filter results: Only keep non-error strings ---
    valid_summaries = []
    for i, result in enumerate(results):
        summary_type, keyword = all_keywords_with_type[i] # Get corresponding keyword/type
        if isinstance(result, Exception):
            logging.error(f"Task for keyword '{keyword}' failed with exception: {result}")
        elif is_error_response(result): # Use the helper function here
             logging.warning(f"Task for keyword '{keyword}' resulted in an error message: {result}")
             # Do NOT add error messages to valid_summaries
        elif result: # Should be a non-empty, non-error string
            valid_summaries.append(result)
            # --- Optionally: Save INDIVIDUAL successful summaries to user_db ---
            # This wasn't explicitly done before, but might be useful.
            # Uncomment if needed, but ensure user_id is available here.
            # try:
            #     user_db_temp = UserDatabase(db_path=config.USER_DB_PATH)
            #     user = user_db_temp.get_user("alice") # Get user ID again or pass it
            #     if user:
            #         user_id = user[0]
            #         user_db_temp.add_summary_result(user_id, summary_type, keyword, result)
            #     user_db_temp.close()
            # except Exception as db_err:
            #     logging.error(f"Failed to save individual summary for '{keyword}' to DB: {db_err}")
            # --------------------------------------------------------------------
        else:
            logging.warning(f"Task for keyword '{keyword}' returned None or empty string without error.")

    logging.info(f"Finished processing keywords. {len(valid_summaries)} valid summaries obtained.")

    # --- Persist Aggregate Results in the User Database ---
    user_db = UserDatabase(db_path=config.USER_DB_PATH)
    try:
        user = user_db.get_user("alice")
        if user:
            user_id = user[0]
        else:
            logging.info("User 'alice' not found, adding new user.")
            user_id = user_db.add_user("alice", "alice@example.com", "hashedpassword123")

        if user_id is None:
             logging.error("Failed to get or create user 'alice'. Cannot proceed with DB operations.")
             return

        today_str = date.today().isoformat()

        # --- Analysis ---
        analysis_response = "[Error: Analysis skipped due to no valid summaries.]" # Default error
        if valid_summaries:
             # Check for existing analysis only if we intend to skip regeneration
             # If we always want fresh analysis based on current summaries, remove this check
             # existing_analysis = user_db.get_summary_result_by_date(user_id, "analysis", today_str)
             # if existing_analysis and not is_error_response(existing_analysis[2]):
             #     analysis_response = existing_analysis[2]
             #     logging.info("Using existing analysis from database for today.")
             # else:
             logging.info("Analyzing summaries...")
             analysis_response = await analyze_summaries(valid_summaries)
             logging.info(f"Analysis response generated.")
             # --- Save analysis to DB ONLY if it's NOT an error ---
             if not is_error_response(analysis_response):
                 user_db.add_summary_result(user_id, "analysis", "aggregate", analysis_response)
                 logging.info("Successfully saved analysis result to database.")
             else:
                 logging.error(f"Analysis resulted in an error, NOT saving to database: {analysis_response}")
        else:
             logging.warning("No valid summaries generated, skipping analysis.")


        # --- Calendar ---
        calendar_response = "[Error: Calendar skipped due to invalid analysis.]" # Default error
        # Create calendar only if analysis was successful
        if not is_error_response(analysis_response):
            # Check for existing calendar only if we intend to skip regeneration
            # existing_calendar = user_db.get_calendar_result_by_date(user_id, today_str)
            # if existing_calendar and not is_error_response(existing_calendar[0]):
            #     calendar_response = existing_calendar[0]
            #     logging.info("Using existing calendar from database for today.")
            # else:
            logging.info("Creating calendar...")
            calendar_response = await create_calendar_from_analysis(analysis_response)
            logging.info(f"Calendar response generated.")
            # --- Save calendar to DB ONLY if it's NOT an error ---
            if not is_error_response(calendar_response):
                user_db.add_calendar_result(user_id, calendar_response)
                logging.info("Successfully saved calendar result to database.")
            else:
                logging.error(f"Calendar creation resulted in an error, NOT saving to database: {calendar_response}")
        else:
            logging.warning("Analysis contains errors or was skipped, skipping calendar creation.")

    finally:
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
        logging.exception("An unexpected error occurred in the main execution loop.")