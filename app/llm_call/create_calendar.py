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
     - Include ongoing events that span multiple days or the entire month.

2. Weekly Calendar
   - Objective: Present the upcoming week’s events in a concise list.
   - Format:
     - Label the week (for example, "Week of [Date Range]").
     - List events by date or day (Monday, Tuesday, etc.).
     - For each event, include Event Type, Relevance Rating, and a short description.
   - Additional Notes:
     - Emphasize any unpredicted events or high-volatility events that occurred late in the prior week if they extend into the new week.
     - Include a preview of key events for the next week.

3. Daily Highlights
   - Objective: Provide a snapshot of the events happening today (and potentially tomorrow if needed).
   - Format:
     - Label the date clearly.
     - List the events for that day with a short explanation of each event.
     - Include any late-breaking changes or updates.
     - Provide a preview or note about the next day.
   - Additional Notes:
     - Keep it succinct—focus on what the user needs to know to start the trading day.
</instructions>
<output_requirements>
1. Accuracy: All events must be correctly placed in their respective monthly, weekly, or daily slots.
2. Clarity: Provide a clear and readable format. Each calendar should be easy to scan.
3. Relevance: Highlight events particularly important to the user’s portfolio or with a high market impact.
4. Structure: The output must strictly adhere to the provided JSON schema.
</output_requirements>
<output_format>
Use the following output schema:
{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Economic Calendar Schema",
  "type": "object",
  "properties": {{
    "title": {{
      "type": "string",
      "description": "The title of the economic calendar, typically indicating the period covered, e.g., 'Economic Calendar (February 2025 Edition)'"
    }},
    "monthlyCalendar": {{
      "type": "object",
      "description": "Monthly calendar section organizing events by date",
      "properties": {{
        "events": {{
          "type": "array",
          "items": {{
            "type": "object",
            "properties": {{
              "date": {{
                "type": "string",
                "description": "Date of the event in 'Month Day' format, e.g., 'February 7'. The year is assumed to be within the calendar's context.",
                "pattern": "^(January|February|March|April|May|June|July|August|September|October|November|December) \\d{{1,2}}$"
              }},
              "events": {{
                "type": "array",
                "items": {{
                  "type": "object",
                  "properties": {{
                    "title": {{
                      "type": "string",
                      "description": "Title of the event, succinctly identifying it, e.g., 'Nonfarm Payrolls', 'FOMC Meeting', or 'Earnings Report: Apple Inc.'"
                    }},
                    "relevance": {{
                      "type": "string",
                      "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"],
                      "description": "Indicates the event's significance to financial markets or economic outlook. 'Very High Relevance' denotes major impact (e.g., central bank decisions, key data releases); 'Low Relevance' suggests minimal market influence."
                    }},
                    "description": {{
                      "type": "string",
                      "description": "Detailed explanation of the event, including key details, potential market impact, or data points. Example: 'January 2025 report showed job growth below expectations, with a slight unemployment drop and strong wage gains, reducing Fed rate cut expectations.'"
                    }}
                  }},
                  "required": ["title", "relevance", "description"]
                }}
              }}
            }},
            "required": ["date", "events"]
          }}
        }},
        "ongoingEvents": {{
          "type": "array",
          "description": "Events spanning multiple days or the entire month",
          "items": {{
            "type": "object",
            "properties": {{
              "title": {{
                "type": "string",
                "description": "Title of the ongoing event, e.g., 'Corporate Earnings Season'"
              }},
              "relevance": {{
                "type": "string",
                "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"]
              }},
              "description": {{
                "type": "string",
                "description": "Details of the ongoing event and its significance"
              }}
            }},
            "required": ["title", "relevance", "description"]
          }}
        }}
      }},
      "required": ["events"]
    }},
    "monthlyPastEventsSummary": {{
      "type": "array",
      "description": "Summary of past events for the month, categorized flexibly",
      "items": {{
        "type": "object",
        "properties": {{
          "category": {{
            "type": "string",
            "description": "Category of the summary, e.g., 'Monetary Policy', 'Earnings Season', 'Economic Data', or 'Geopolitical Events'"
          }},
          "description": {{
            "type": "string",
            "description": "Summary of events or trends within this category for the past month"
          }}
        }},
        "required": ["category", "description"]
      }}
    }},
    "monthlyUpcomingEventsSummary": {{
      "type": "array",
      "description": "Summary of key upcoming events for the month",
      "items": {{
        "type": "object",
        "properties": {{
          "title": {{
            "type": "string",
            "description": "Title of the upcoming event"
          }},
          "relevance": {{
            "type": "string",
            "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"]
          }},
          "description": {{
            "type": "string",
            "description": "Overview of the upcoming event and its expected significance"
          }}
        }},
        "required": ["title", "relevance", "description"]
      }}
    }},
    "weeklyHighlights": {{
      "type": "object",
      "description": "Highlights for a specific week",
      "properties": {{
        "weekRange": {{
          "type": "string",
          "description": "Date range of the week, e.g., 'Week of February 24 – March 2, 2025'"
        }},
        "description": {{
          "type": "string",
          "description": "Brief overview of the week's key themes, e.g., 'Focus on economic data releases'"
        }},
        "pastEvents": {{
          "type": "array",
          "items": {{
            "type": "object",
            "properties": {{
              "date": {{
                "type": "string",
                "pattern": "^(January|February|March|April|May|June|July|August|September|October|November|December) \\d{{1,2}}$",
                "description": "Date of past events, e.g., 'February 19'"
              }},
              "events": {{
                "type": "array",
                "items": {{
                  "type": "object",
                  "properties": {{
                    "title": {{
                      "type": "string"
                    }},
                    "relevance": {{
                      "type": "string",
                      "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"]
                    }},
                    "description": {{
                      "type": "string"
                    }}
                  }},
                  "required": ["title", "relevance", "description"]
                }}
              }}
            }},
            "required": ["date", "events"]
          }}
        }},
        "upcomingEvents": {{
          "type": "array",
          "items": {{
            "type": "object",
            "properties": {{
              "date": {{
                "type": "string",
                "description": "Date or time frame for upcoming events, e.g., 'February 24 onwards' or 'Throughout the Week'"
              }},
              "events": {{
                "type": "array",
                "items": {{
                  "type": "object",
                  "properties": {{
                    "title": {{
                      "type": "string"
                    }},
                    "relevance": {{
                      "type": "string",
                      "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"]
                    }},
                    "description": {{
                      "type": "string"
                    }}
                  }},
                  "required": ["title", "relevance", "description"]
                }}
              }}
            }},
            "required": ["date", "events"]
          }}
        }},
        "nextWeekPreview": {{
          "type": "array",
          "items": {{
            "type": "object",
            "properties": {{
              "date": {{
                "type": "string",
                "pattern": "^(January|February|March|April|May|June|July|August|September|October|November|December) \\d{{1,2}}$",
                "description": "Date in the next week, e.g., 'March 3'"
              }},
              "events": {{
                "type": "array",
                "items": {{
                  "type": "object",
                  "properties": {{
                    "title": {{
                      "type": "string"
                    }},
                    "relevance": {{
                      "type": "string",
                      "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"]
                    }},
                    "description": {{
                      "type": "string"
                    }}
                  }},
                  "required": ["title", "relevance", "description"]
                }}
              }}
            }},
            "required": ["date", "events"]
          }}
        }}
      }},
      "required": ["weekRange", "description"]
    }},
    "dailyHighlights": {{
      "type": "object",
      "description": "Highlights for a specific day",
      "properties": {{
        "date": {{
          "type": "string",
          "description": "Full date, including day of week, e.g., 'Saturday, February 22, 2025'"
        }},
        "todaysKeyEvents": {{
          "type": "array",
          "items": {{
            "type": "object",
            "properties": {{
              "title": {{
                "type": "string"
              }},
              "relevance": {{
                "type": "string",
                "enum": ["Very High Relevance", "High Relevance", "Moderate Relevance", "Low Relevance"]
              }},
              "description": {{
                "type": "string"
              }}
            }},
            "required": ["title", "relevance", "description"]
          }}
        }},
        "nextDayPreview": {{
          "type": "object",
          "properties": {{
            "date": {{
              "type": "string",
              "pattern": "^(January|February|March|April|May|June|July|August|September|October|November|December) \\d{{1,2}}, \\d{{4}}$",
              "description": "Next day's date, e.g., 'February 23, 2025'"
            }},
            "description": {{
              "type": "string",
              "description": "Preview or note about the next day, e.g., 'No specific events listed, but monitor late-breaking news.'"
            }}
          }},
          "required": ["date", "description"]
        }}
      }},
      "required": ["date", "todaysKeyEvents", "nextDayPreview"]
    }}
  }},
  "required": ["title", "monthlyCalendar", "monthlyPastEventsSummary", "monthlyUpcomingEventsSummary", "weeklyHighlights", "dailyHighlights"]
}}
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