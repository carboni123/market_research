from datetime import datetime, date

def weekday():
    current_date = datetime.now()
    day_of_week = current_date.strftime('%A')
    return day_of_week

def create_calendar():
    prompt = f"""
<context> 
Today is {weekday()}, {date.today()}.
You have received a comprehensive list of events. Each event is structured with the following details:
- Event Type (for example, Nonfarm Payrolls, Earnings Release, etc.)
- Relevance Rating (Low, Moderate, High, Very High)
- Event Date
- Key Details / Summary
</context> 
<objective>
Your task is to generate and distribute three types of calendars based on this list:
1. Monthly Calendar
2. Weekly Calendar
3. Daily Highlights
</objective>
<instructions>
1. Monthly Calendar
   - Objective: Provide an overview of all events occurring within the month.
   - Format:
     - Clearly label the month.
     - List each relevant event chronologically by date.
     - Include Event Type, Date, Relevance Rating, and a brief summary (why it matters).
   - Additional Notes:
     - If there are portfolio-relevant events (for example, earnings for a company the user holds), highlight them.
     - Summarize the month’s major market themes where relevant (optional, but recommended).

2. Weekly Calendar
   - Objective: Present the upcoming week’s events in a concise list.
   - Format:
     - Label the week (for example, "Week of [Date Range]").
     - List events by date or day (Monday, Tuesday, etc.).
     - For each event, include Event Type, Relevance Rating, and a short description.
   - Additional Notes:
     - Emphasize any unpredicted events or high-volatility events that occurred late in the prior week if they extend into the new week.

3. Daily Highlights
   - Objective: Provide a snapshot of the events happening today (and potentially tomorrow if needed).
   - Format:
     - Label the date clearly.
     - List the events for that day with a short explanation of each event.
     - Include any late-breaking changes or updates.
   - Additional Notes:
     - Keep it succinct—focus on what the user needs to know to start the trading day.
</instructions>
<output_requirements>
1. Accuracy: All events must be correctly placed in their respective monthly, weekly, or daily slots.
2. Clarity: Provide a clear and readable format. Each calendar should be easy to scan.
3. Relevance: Highlight events particularly important to the user’s portfolio or with a high market impact.
</output_requirements>
<output_format>
# Example Output Structure (for illustration)
Monthly Calendar (March Edition)
- March 3 - Nonfarm Payrolls (Very High): Key labor market indicator, likely to impact Fed policy.
- March 8 - Company ABC Earnings (High): User holds ABC; potential price volatility.
- and so on for the month.

Weekly Calendar (Week of March 5 – 11)
- Monday, March 6 - PMI Data (High)
- Wednesday, March 8 - Company ABC Earnings (High)
- Thursday, March 9 - Initial Jobless Claims (Moderate)
- list of events for each day of the week.

Daily Highlights (March 6)
- PMI Data (High): Expectations versus last month’s reading.
- Any unexpected overnight developments.
</output_format>
<remember>
What You Should Not Include:
- Previous LLM prompts or instructions: All you need is the final consolidated event list.
- Redundant information: Focus on clarity and brevity.
- Analysis beyond event descriptions: You may add brief context or significance, but do not include unrelated commentary.
</remember>
"""
    return prompt

if __name__ == "__main__":
    print(create_calendar())