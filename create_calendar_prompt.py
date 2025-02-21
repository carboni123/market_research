PROMPT ="""
## Prompt: Calendar Compilation & Distribution

<Context>   
You have received a   comprehensive list of events   from a previous LLM call. Each event is structured with the following details:
-   Event Type   (e.g., Nonfarm Payrolls, Earnings Release, etc.)  
-   Relevance Rating   (Low, Moderate, High, Very High)  
-   Event Date(s)    
-   Key Details / Summary    
<Objective> 
Your task is to   generate and distribute three types of calendars based on this list:
1. Monthly Calendar : Published on the first day of each month.  
2. Weekly Calendar : Published on Sundays.  
3. Daily Highlights : Published every day.

You are provided with tools (e.g., a calendar tool) to properly schedule and format these calendars. Use these tools to ensure the calendars are accurately compiled, formatted, and distributed to the user.

<Instructions>
1. Monthly Calendar (Distributed on the First Day of Each Month)    
   - Objective : Provide an overview of   all events occurring within the month  .  
   -   Format :  
     - Clearly label the month.  
     - List each relevant event chronologically by date.  
     - Include Event Type, Date, Relevance Rating, and a brief summary (why it matters).  
   -   Additional Notes  :  
     - If there are portfolio-relevant events (e.g., earnings for a company the user holds), highlight them.  
     - Summarize the month’s major market themes where relevant (optional, but recommended).

2. Weekly Calendar (Distributed on Sundays)    
   - Objective : Present the   upcoming week’s events   in a concise list.  
   - Format :  
     - Label the week (e.g., “Week of [Date Range]”).  
     - List events by date/day (Monday, Tuesday, etc.).  
     - For each event, include Event Type, Relevance Rating, and a short description.  
   -   Additional Notes  :  
     - Emphasize any unpredicted events or high-volatility events that occurred late in the prior week if they extend into the new week.  

3. Daily Highlights (Distributed Every Day)    
   -   Objective  : Provide a   snapshot of the events   happening   today   (and potentially tomorrow if needed).  
   -   Format  :  
     - Label the date clearly.  
     - List the events for that day with a short explanation of each event.  
     - Include any late-breaking changes or updates.  
   -   Additional Notes  :  
     - Keep it succinct—focus on what the user needs to know to start the trading day.  


<Calendar Management & Tool Usage>
- You have access to a   Calendar Tool   (or similar utility) to help manage publication dates (e.g., scheduling the monthly calendar on the 1st of each month, the weekly calendar every Sunday, and the daily highlights each morning).  
- Ensure that each calendar is   delivered on time   and that the data remains   accurate   even if events change. For example, if an event is rescheduled, update the final calendars accordingly.

<Final Output Requirements>
1.   Accuracy  : All events must be correctly placed in their respective monthly, weekly, or daily slots.  
2.   Clarity  : Provide a clear and readable format. Each calendar should be easy to scan.  
3.   Relevance  : Highlight events particularly important to the user’s portfolio or with a high market impact.  
4.   Timeliness  :  
   - Monthly calendar on the   1st day   of each month.  
   - Weekly calendar on   Sundays  .  
   - Daily highlights   each day   (e.g., in the morning).

<Example Output Structure (for illustration)>
Monthly Calendar (March 1st Edition)    
-   March 3   – Nonfarm Payrolls (Very High): Key labor market indicator, likely to impact Fed policy.  
-   March 8   – Company ABC Earnings (High): User holds ABC; potential price volatility.  
- … and so on for the month.

Weekly Calendar (Week of March 5 – 11)    
-   Monday, March 6   – PMI Data (High)  
-   Wednesday, March 8   – Company ABC Earnings (High)  
-   Thursday, March 9   – Initial Jobless Claims (Moderate)  
- … list of events for each day of the week.

Daily Highlights (March 6)    
- PMI Data (High): Expectations vs. last month’s reading.  
- Any unexpected overnight developments.

<What You Should Not Include>
-   Previous LLM prompts or instructions  : All you need is the final consolidated event list.  
-   Redundant information  : Focus on clarity and brevity.  
-   Analysis beyond event descriptions  : You may add brief context or significance, but do not include unrelated commentary.
"""