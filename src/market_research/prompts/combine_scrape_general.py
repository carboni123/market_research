# llm_call/combine_scrape_general.py
from datetime import date

def combine_scrape_prompt(query):
    """
    Generates a prompt instructing the LLM to perform a web search for a query
    and synthesize the results into a comprehensive report.
    """
    prompt = f"""
<objective>
Today is {date.today()}. Your primary task is to perform a web search based on the user's query: "{query}".
After retrieving the search results, synthesize the information into a comprehensive and coherent report.
</objective>

<instructions>
1.  **Perform Web Search:** Use the available web search tool to find relevant and up-to-date information regarding "{query}". Prioritize reputable news sources, official announcements, and reliable financial data providers.
2.  **Synthesize Results:** Combine the information gathered from the search results into a single report.
3.  **Track Dates:** Prioritize the most recent information. Note specific dates (e.g., "reported on YYYY-MM-DD", "event scheduled for YYYY-MM-DD") where available. Identify and list any future events or deadlines mentioned under a distinct 'Upcoming Events' section.
4.  **Preserve Key Details:** Include all significant facts, figures, statements, or unique insights found in the search results. Do not omit critical information.
5.  **Structure the Report:** Organize the report logically. Use clear headings (e.g., 'Overview', 'Key Findings', 'Recent Developments', 'Upcoming Events', 'Market Impact'). A chronological structure might be suitable for evolving stories.
6.  **Conciseness & Completeness:** Be concise but ensure all crucial information is covered. Summarize minor details where appropriate but present key data points fully. Avoid redundancy.
7.  **Attribute (If Possible):** While you don't need to list every source URL, mentioning the source type (e.g., "According to financial news outlets...", "An analyst report stated...") can add context if significant discrepancies exist.
8.  **Handle Conflicts:** If search results present conflicting information, acknowledge the discrepancies (e.g., "Reports differ on the exact figure...").
9.  **Maintain Neutrality:** Present information factually and objectively. Avoid speculation or biased language.
</instructions>

<output_format>
Generate a well-structured report based on the synthesis of the web search results for "{query}". Use clear language and headings. Ensure the 'Upcoming Events' section is clearly marked if applicable.
</output_format>
"""
    return prompt