#!/usr/bin/env python3
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

import json
from datetime import datetime
from typing import List, Dict, Any

# -----------------------------------------------------------------------------
# Pre-defined Keywords for Market Events
# -----------------------------------------------------------------------------
MARKET_KEYWORDS: List[str] = [
    "nonfarm payrolls latest",
    "FOMC meetings calendar",
    "earnings event calendar",
    "economic data releases schedule",
    "unemployment rate US latest",
    "Consumer Price Index (CPI) latest",
    "quarterly reports schedule US stock market",
    "US GDP update",
    "industrial production update",
    "weekly financial market data",
    "initial jobless claims latest",
    "monetary policy announcements",
    "central bank meetings calendar",
    "breaking press conference news",
    "US stock market dividend announcements news",
    "M&A deals",
    "major companies product launches news",
    "options expiration this week",
    "geopolitical news",
    "regulatory changes news",
    "financial news",
    "market volatility update",
    "Fed monetary policy news",
    "European Central Bank (ECB) monetary policy news",
    "BoJ monetary policy news",
    "interest rate update",
    "quantitative easing news",
    "Personal Consumption Expenditures (PCE) update",
    "US manufacturing data",
    "China manufacturing data",
    "US retail sales data",
    "US housing starts data",
    "US consumer confidence index",
    "stock split announcements",
    "US election news",
    "US political uncertainty news",
    "tariff news",
    "trade dispute news",
    "war updates",
    "terrorist news",
    "sanction news"
]

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def load_user_portfolio(file_path: str = "user_portfolio.txt") -> List[Dict[str, Any]]:
    """
    Loads the user portfolio from a JSON-formatted file.

    Args:
        file_path (str): Path to the portfolio file. Defaults to "user_portfolio.txt".

    Returns:
        List[Dict[str, Any]]: The portfolio data as a list of dictionaries.
    """
    with open(file_path, "r") as file:
        data = file.read()
    return json.loads(data)


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


def extract_portfolio_keywords() -> List[str]:
    """
    Extracts portfolio keywords by combining each stock's security name with its 
    respective earnings quarter and year. The quarter is adjusted as follows:
    
    - For BDR stocks (ticker contains "34"): add 2 quarters.
    - For non-BDR stocks: subtract 1 quarter (since the current quarter has not passed yet).
    
    Year adjustments are applied when quarter calculations roll over past Q4 or before Q1.

    Returns:
        List[str]: A list of strings in the format "<security> earnings Q<quarter> <year>".
    """
    try:
        quarter_info = get_current_quarter_details()
        current_quarter = quarter_info["quarter"]
        current_year = quarter_info["year"]

        ticker_list: List[str] = []
        portfolio = load_user_portfolio()

        if not portfolio:
            return ticker_list  # Return empty list if portfolio is empty

        for stock in portfolio:
            security = stock.get("security")
            ticker = stock.get("ticker")
            if not security or not ticker:
                continue  # Skip stocks with missing data

            is_bdr = "34" in ticker.lower()
            quarter = current_quarter
            year = current_year

            if is_bdr:
                # Add 2 quarters for BDR stocks
                quarter += 2
                if quarter > 4:
                    quarter -= 4
                    year += 1
            else:
                # Subtract 1 quarter for non-BDR stocks
                quarter -= 1
                if quarter < 1:
                    quarter = 4
                    year -= 1

            ticker_entry = f"{security} earnings Q{quarter} FY{year}"
            ticker_list.append(ticker_entry)

        return ticker_list

    except Exception as e:
        print(f"Error in extract_portfolio_keywords: {str(e)}")
        return []

def get_keywords() -> List[str]:
    return MARKET_KEYWORDS + extract_portfolio_keywords()

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    portfolio_keywords = extract_portfolio_keywords()
    print("Portfolio Keywords:")
    for keyword in portfolio_keywords + MARKET_KEYWORDS:
        print(f" - {keyword}")
