# main.py
import os
import asyncio
import glob
from datetime import datetime, date
from keywords import get_keywords
from scrape_api import call_scrape_api
from llm_call.combine_scrape_general import combine_scrape_prompt
from llm_call.analyze_data import analyze_data
from llm_call.create_calendar import create_calendar

from api import create_api_instance

openai_llm_api = create_api_instance("openai")  # For better processing
google_llm_api = create_api_instance("google")  # For 2M tokens context size

# Define the cache directory and ensure it exists
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def check_cache(keyword):
    cache_filename = os.path.join(CACHE_DIR, f"{keyword}_summary.txt")
    # Try to load cached response based on keyword if available
    if os.path.exists(cache_filename):
        with open(cache_filename, 'r', encoding='utf-8') as cache_file:
            cached_response = cache_file.read()
        return cached_response
    else:
        return None

def call_create_summary(keyword: str, scrape_response: dict):
    cache_filename = os.path.join(CACHE_DIR, f"{keyword}_summary.txt")
    cached_response = check_cache(keyword)
    if cached_response:
        return cached_response

    # Get prompt instructions to combine scrape results
    instructions = combine_scrape_prompt(keyword)
    prompt = instructions + "\n" + str(scrape_response)
    # Process the prompt with the language model
    response = asyncio.run(google_llm_api.process_text(prompt.strip("\n")))

    # Save the response to a file with the keyword as the filename
    with open(cache_filename, 'w', encoding='utf-8') as cache_file:
        cache_file.write(response)

    return response

def call_analyze_data(summaries: list):
    # Format timestamp to avoid illegal characters in filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_filename = os.path.join("analysis", f"analyze_{timestamp}.txt")

    # Combine all summaries into one string
    summaries_str = " ".join(summaries)
    instructions = analyze_data()
    prompt = instructions + "\n" + summaries_str

    response = asyncio.run(google_llm_api.process_text(prompt, max_tokens=16384))

    # Save the response to a file with the timestamped filename
    with open(cache_filename, 'w', encoding='utf-8') as cache_file:
        cache_file.write(response)
    return response

def call_calendar(analysis:str):
    cache_filename = os.path.join("analysis", f"{date.today()}_calendar.txt")
    # Combine the instructions and analysis in one string
    instructions = create_calendar()
    prompt = instructions + "\n" + analysis

    response = asyncio.run(openai_llm_api.process_text(prompt))
    # Save the response to a file with the timestamped filename
    with open(cache_filename, 'w', encoding='utf-8') as cache_file:
        cache_file.write(response)
    return response

if __name__ == "__main__":
    # Get keywords
    keywords = get_keywords()
    print(keywords)
    
    # # Use keywords to scrape data from web
    # summaries = []
    # for key in keywords:
    #     print(key)
    #     cached_response = check_cache(key)
    #     if not cached_response:
    #         scrape_response = call_scrape_api(key)
    #         summary = call_create_summary(key, scrape_response)
    #     else:
    #         summary = cached_response
    #     summaries.append(summary)

    # Load cached results for example
    summaries = []
    for summary_path in glob.glob("cache/*.txt"):
        with open(summary_path, "r", encoding="utf-8") as file:
            summary = file.read()
        summaries.append(summary)
    # With the summaries, make another LLM call to analyze the data
    analyze_response = call_analyze_data(summaries)

    # # Load cached analysis and create calendar
    # with open("analysis/analyze_20250220_171059.txt", "r") as f:
    #     analyze_response = f.read()
    # calendar_response = call_calendar(analyze_response)
    # print(calendar_response)