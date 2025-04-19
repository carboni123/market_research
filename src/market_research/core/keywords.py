# src/market_research/core/keywords.py
"""
keywords.py

This script provides two main functionalities:
1. A pre-defined list of market-related keywords.
2. Extraction of portfolio-specific keywords based on a user portfolio file 
   and the current date.

The portfolio keywords are constructed by combining each stock's security name 
with its corresponding earnings quarter and year. For BDR stocks (identified by 
"34" in their ticker), the quarter is adjusted forward by two quarters; for other 
stocks, the quarter is adjusted backward by one quarter.
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import logging

# -----------------------------------------------------------------------------
# Pre-defined Keywords for Market Events
# -----------------------------------------------------------------------------
MARKET_KEYWORDS = {
    "daily": [
        "Fed monetary policy news",
        "European Central Bank (ECB) monetary policy news",
        "breaking press conference news",
        "geopolitical news",
        "regulatory changes news",
        "financial news",
        "market volatility update",
        "interest rate update",
        "quantitative easing news",
        "US political uncertainty news",
        "tariff news",
        "trade dispute news",
        "war updates"
        "M&A deals",
        "major companies product launches news",
        "stock split announcements",
        "US election news",
        "terrorist economy news",
        "US sanctions news"
    ],
    "weekly": [
        "FOMC meetings calendar",
        "central bank meetings calendar",
        "weekly financial market data",
        "initial jobless claims latest",
        "options expiration this week"
        "nonfarm payrolls latest",
        "economic data releases schedule",
        "unemployment rate US latest",
        "Consumer Price Index (CPI) latest",
        "industrial production update",
        "Personal Consumption Expenditures (PCE) update",
        "US manufacturing data",
        "China manufacturing data",
        "US retail sales data",
        "US housing starts data",
        "US consumer confidence index",
        "US stock market dividend announcements news",
    ],
    "monthly": [
        "earnings event calendar",
        "quarterly reports schedule US stock market",
        "US GDP update",  
        "monetary policy announcements",
        "BoJ monetary policy news"
    ],
}

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def load_user_portfolio(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads the user portfolio from a JSON-formatted file.

    Args:
        file_path (str): Path to the portfolio file.

    Returns:
        List[Dict[str, Any]]: The portfolio data as a list of dictionaries.
    """
    if not os.path.exists(file_path):
        print(f"Warning: Portfolio file not found at {file_path}")
        return []
    try:
        with open(file_path, "r", encoding='utf-8') as file: # Added encoding
            data = file.read()
        return json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error reading portfolio file {file_path}: {e}")
        return []


def get_current_quarter_details() -> Dict[str, int]:
    """
    Returns the current calendar quarter and year based on today's date.

    Returns:
        Dict[str, int]: A dictionary containing 'quarter' and 'year'.
    """
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    calendar_quarter = (current_month - 1) // 3 + 1
    return {"quarter": calendar_quarter, "year": current_year}


def extract_portfolio_keywords(portfolio_file_path: str) -> List[str]: # Added explicit path argument
    """
    Extracts portfolio keywords...

    Args:
        portfolio_file_path (str): The full path to the user portfolio file.

    Returns:
        List[str]: A list of strings in the format "<security> earnings Q<quarter> FY<year>".
                   Returns empty list on error or if portfolio is empty/invalid.
    """
    try:
        quarter_info = get_current_quarter_details()
        current_quarter = quarter_info["quarter"]
        current_year = quarter_info["year"]

        ticker_list: List[str] = []
        portfolio = load_user_portfolio(portfolio_file_path) # Use passed path

        if not portfolio:
            logging.warning(f"No valid portfolio data loaded from {portfolio_file_path}.") # Use logging
            return ticker_list

        for stock in portfolio:
            security = stock.get("security")
            ticker = stock.get("ticker")
            if not security or not ticker:
                logging.warning(f"Skipping portfolio item due to missing security or ticker: {stock}") # Use logging
                continue

            is_bdr = "34" in ticker.lower() # Assuming '34' reliably indicates BDR
            quarter = current_quarter
            year = current_year

            # --- Quarter Adjustment Logic (Keep as is, assuming it's correct for the domain) ---
            if is_bdr:
                quarter += 2
                if quarter > 4:
                    quarter -= 4
                    year += 1
            else:
                quarter -= 1
                if quarter < 1:
                    quarter = 4
                    year -= 1
            # --- End Adjustment Logic ---

            ticker_entry = f"{security} earnings Q{quarter} FY{year}"
            ticker_list.append(ticker_entry)

        return ticker_list

    except Exception as e:
        logging.exception(f"Error in extract_portfolio_keywords processing {portfolio_file_path}: {e}")
        return []

def get_all_keywords(portfolio_file_path: str) -> List[str]:
    """
    Combines general market keywords and portfolio-specific keywords.

    Args:
        portfolio_file_path (str): Path to the user portfolio file.

    Returns:
        List[str]: A combined list of all keywords.
    """
    all_keywords = []
    # Add keywords from all periods in MARKET_KEYWORDS
    for period in MARKET_KEYWORDS:
        all_keywords.extend(MARKET_KEYWORDS[period])

    # Add portfolio keywords
    portfolio_kws = extract_portfolio_keywords(portfolio_file_path)
    all_keywords.extend(portfolio_kws)

    # Return unique keywords if desired, though main.py handles this
    # return list(set(all_keywords))
    return all_keywords

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Find the project root to locate the data directory
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        project_root = os.path.abspath("../..") # Adjust relative path if needed

    default_portfolio_path = os.path.join(project_root, "..", "data", "user_portfolio.txt")

    print(f"Attempting to load portfolio from: {default_portfolio_path}")

    # Get combined list using the corrected function
    combined_keywords = get_all_keywords(default_portfolio_path)

    print("\nCombined Keywords:")
    if combined_keywords:
        # Print unique keywords for clarity
        unique_keywords = sorted(list(set(combined_keywords)))
        for keyword in unique_keywords:
            print(f" - {keyword}")
    else:
        print("No keywords generated (check portfolio file path and content).")