# llm_call/combine_scrape_portfolio.py
from datetime import datetime, date

def weekday():
    current_date = datetime.now()
    day_of_week = current_date.strftime('%A')
    return day_of_week

def combine_portfolio_prompt(stock_info): # Renamed parameter for clarity
    """
    Generates a prompt instructing the LLM to perform a web search for specific stock information
    and synthesize the results relevant to a user's portfolio.
    """
    prompt = f"""
<objective>
Today is {weekday()} {date.today()}. Your primary task is to perform a web search focused on the following stock information relevant to the user's portfolio: "{stock_info}".
This might include recent news, earnings reports, analyst ratings, price movements, or upcoming events related to this specific stock/security. After retrieving the search results, synthesize the information into a comprehensive report tailored for a portfolio holder.
</objective>

<instructions>
1.  **Perform Focused Web Search:** Use the available web search tool to find the latest and most relevant information specifically about "{stock_info}". Look for news articles, press releases, financial data, analyst updates, and event calendars.
2.  **Synthesize Portfolio-Relevant Results:** Combine the gathered information into a single report focusing on aspects important to an investor holding this stock.
3.  **Prioritize Recent & Dated Info:** Focus on the most current updates. Clearly state dates for news, reports, or events (e.g., "Earnings reported on YYYY-MM-DD", "Analyst upgrade dated YYYY-MM-DD"). Create a distinct 'Upcoming Events' section for future dates (e.g., next earnings call, ex-dividend date, product launch).
4.  **Include Key Financial & Event Details:** Ensure significant data points are included: stock price changes (mention timeframe if available), earnings results (EPS, revenue vs. estimates), analyst rating changes (upgrade/downgrade, price targets), major company announcements (M&A, partnerships, regulatory news), dividend information.
5.  **Structure for Investors:** Organize the report logically for an investor. Suggested sections:
    *   `Recent Performance`: Key price movements, volume changes.
    *   `Key News & Developments`: Summaries of significant recent news.
    *   `Earnings & Financials`: Latest earnings summary, relevant financial metrics.
    *   `Analyst Sentiment`: Recent changes in analyst ratings or price targets.
    *   `Upcoming Events`: Clearly list dates and descriptions of future events.
6.  **Concise yet Complete:** Avoid jargon where possible, be clear and concise. Summarize background information but provide specifics on recent data and events.
7.  **Attribute Key Changes (If Needed):** Mentioning the source of a significant change (e.g., "Rating upgrade by [Firm Name]...") can be useful.
8.  **Neutral Tone:** Present findings factually and objectively. Avoid investment advice or speculation.
</instructions>

<output_format>
Generate a well-structured report synthesizing the web search results for "{stock_info}", focusing on information relevant to an investor. Ensure an 'Upcoming Events' section is included if applicable.
</output_format>
"""
    return prompt