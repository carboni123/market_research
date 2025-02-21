from datetime import date

def combine_scrape_prompt(query):
    """
    Generates a prompt for synthesizing aggregated web pages into a comprehensive report.

    Parameters:
        query (str): The keyword or topic based on which the web pages were aggregated.

    Returns:
        str: A formatted prompt that instructs an LLM to synthesize the aggregated data.
    """
    prompt = f"""
Today is {date.today()}.
You are provided with a collection of aggregated web pages from various news sources containing information on {query}. Your task is to synthesize this content into one comprehensive and coherent report. Please follow these guidelines:

1. Keep Track of Dates: Prioritize the most recent information and note dates where applicable to maintain relevance. If future dates are mentioned (e.g., upcoming events, deadlines, or scheduled announcements), identify these as future events and list them separately under a section like ‘Upcoming Events’ for easy reference.
2. Preserve Details: Include every key fact or unique insight from the sources, ensuring no relevant information is omitted.
3. Structured Report: Organize the report into clear sections or headings based on themes or topics (e.g., 'Overview,' 'Key Findings,' 'Supporting Details,' 'Conclusion'). For evolving stories, consider a chronological structure to show the progression of events.
4. Conciseness with Completeness: Compress information to avoid redundancy. For less critical details, provide brief summaries, but ensure key events, statements, or data points are presented in full.
5. Balanced Integration: Merge similar points from different sources into a coherent narrative, noting any variations or nuances. If there are conflicting reports or discrepancies, highlight these differences and, if possible, indicate which sources might be more reliable based on reputation or recency.
6. Unbiased Tone: Present the information factually and objectively, without favoring one source over another.

Using these instructions, please generate a report that accurately reflects the aggregated data.
"""
    return prompt