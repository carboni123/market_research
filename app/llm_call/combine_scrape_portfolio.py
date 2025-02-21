from datetime import datetime, date

def weekday():
    current_date = datetime.now()
    day_of_week = current_date.strftime('%A')
    return day_of_week

def combine_portfolio_prompt(portfolio):
    prompt = f"""
Today is {weekday()} {date.today()}.
You are provided with a collection of aggregated web pages, including news articles, analyst reports, and financial updates, related to the stocks in the user's portfolio: {portfolio}. 
Your task is to combine this content into one comprehensive and coherent report. Please follow these guidelines:
1. Prioritize Recent Information: Focus on the most up-to-date information and clearly note the dates of key events or data points to maintain relevance. If future dates are mentioned (e.g., upcoming earnings reports, product launches, or regulatory deadlines), identify these as future events and list them separately under a section titled ‘Upcoming Events’ for easy reference.
2. Include All Key Details: Ensure that every significant fact, statistic, or unique insight from the sources is included. For example, this could include stock price changes, earnings results, analyst ratings, or major company announcements. Do not omit any relevant information that could impact the user's understanding of the portfolio.
3. Organize the Report Clearly: Structure the report into sections based on themes or topics. Suggested sections include:
   - Overview: A brief summary of the current state of the portfolio, including overall performance and major trends.
   - Key Findings: Highlight the most important insights, such as significant stock movements, changes in analyst sentiment, or major news events.
   - Supporting Details: Provide additional context or data that supports the key findings, such as historical performance, market comparisons, or detailed financial metrics.
   - Conclusion: Offer a final summary or outlook based on the information presented.
   For evolving stories (e.g., ongoing mergers, legal disputes, or product developments), use a chronological structure to show the progression of events.
4. Be Concise but Complete: Avoid redundancy by summarizing less critical details. For example, if multiple sources report the same event, provide a single, clear description rather than repeating similar information. Use bullet points or short paragraphs to present information clearly while ensuring all key events, statements, or data points are fully included.
5. Integrate Information Thoughtfully: Merge similar points from different sources into a coherent narrative. If there are conflicting reports or discrepancies (e.g., differing analyst opinions or contradictory data), highlight these differences and, if possible, indicate which sources might be more reliable based on their reputation or recency.
6. Maintain an Unbiased Tone: Present the information factually and objectively, without favoring one source over another. Avoid speculative language or personal opinions.
Using these instructions, please generate a report that accurately reflects the aggregated data.
"""
    return prompt