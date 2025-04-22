# src/market_research/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
import enum

# --- Enums ---

class RelevanceRatingEnum(str, enum.Enum):
    VERY_HIGH = "Very High Relevance"
    HIGH = "High Relevance"
    MODERATE = "Moderate Relevance"
    LOW = "Low Relevance"

# --- Models for Analysis Report (analyze_data.py output) ---

class EventItem(BaseModel):
    """Represents a single event item within the analysis report."""
    event_type: str = Field(..., alias="Event Type", description="Type of the event (e.g., CPI Release, FOMC Meeting, Earnings Report).")
    relevance_rating: RelevanceRatingEnum = Field(..., alias="Relevance Rating", description="Relevance rating of the event.")
    event_dates: str = Field(..., alias="Event Date(s)", description="Date or date range of the event (e.g., '2025-04-10', 'March 18-19, 2025').")
    summary: str = Field(..., alias="General Overview and Summary", description="Explanation of the event's significance and details.")

    class Config:
        allow_population_by_field_name = True # Allow using Pythonic names too

class ReportSection(BaseModel):
    """Represents a section within the analysis report."""
    heading: str = Field(..., description="Heading for the section (e.g., 'Current Events', 'Future Events', 'Portfolio Summary').")
    content: Union[str, List[EventItem]] = Field(..., description="Content of the section, either a string summary or a list of event items.")

class AnalysisReportData(BaseModel):
    """The main data structure for the analysis report."""
    title: str = Field(..., description="Title of the market events analysis report.")
    sections: List[ReportSection] = Field(..., description="List of sections containing events or summaries.")
    date_generated: str = Field(
        ..., 
        description="Date when the report was generated (YYYY-MM-DD). Example 2025-04-22",
    )

class AnalysisReport(BaseModel):
    """Top-level model for the analysis report JSON output."""
    report: AnalysisReportData = Field(..., description="The main report object.")


# --- Models for Economic Calendar (create_calendar.py output) ---

class CalendarEvent(BaseModel):
    """Represents a single event within the economic calendar."""
    title: str = Field(..., description="Title of the event, succinctly identifying it.")
    relevance: RelevanceRatingEnum = Field(..., description="Indicates the event's significance.")
    description: str = Field(..., description="Detailed explanation of the event.")

class MonthlyEventGroup(BaseModel):
    """Groups events by a specific date within the monthly calendar."""
    date: str = Field(..., description="Date of the event in 'Month Day' format, e.g., 'April 10'.")
    events: List[CalendarEvent] = Field(..., description="List of events occurring on this date.")

class MonthlyCalendar(BaseModel):
    """Structure for the monthly calendar section."""
    events: List[MonthlyEventGroup] = Field(..., description="List of events grouped by date for the month.")
    ongoing_events: Optional[List[CalendarEvent]] = Field(None, alias="ongoingEvents", description="Events spanning multiple days or the entire month.")

    class Config:
        allow_population_by_field_name = True # Allow using Pythonic names too

class MonthlySummaryItem(BaseModel):
    """Represents a summary item for past or upcoming monthly events."""
    # For Past Events Summary
    category: Optional[str] = Field(None, description="Category of the summary (used in past events).")
    # For Upcoming Events Summary (reuse CalendarEvent structure where possible)
    title: Optional[str] = Field(None, description="Title of the upcoming event (used in upcoming summary).")
    relevance: Optional[RelevanceRatingEnum] = Field(None, description="Relevance of the upcoming event (used in upcoming summary).")
    # Common field
    description: str = Field(..., description="Summary description.")


class WeeklyEventGroup(BaseModel):
    """Groups events by a specific date or timeframe within the weekly calendar."""
    date: str = Field(..., description="Date or time frame for events within the week, e.g., 'April 24' or 'Throughout the Week'.")
    events: List[CalendarEvent] = Field(..., description="List of events for this date/timeframe.")

class WeeklyHighlights(BaseModel):
    """Structure for the weekly highlights section."""
    week_range: str = Field(..., alias="weekRange", description="Date range of the week, e.g., 'Week of April 21 – 27, 2025'.")
    description: str = Field(..., description="Brief overview of the week's key themes.")
    past_events: Optional[List[WeeklyEventGroup]] = Field(None, alias="pastEvents", description="Events that occurred earlier in the week (if applicable).")
    upcoming_events: Optional[List[WeeklyEventGroup]] = Field(None, alias="upcomingEvents", description="Events upcoming in the week.")
    next_week_preview: Optional[List[WeeklyEventGroup]] = Field(None, alias="nextWeekPreview", description="Preview of key events for the following week.")

    class Config:
        allow_population_by_field_name = True # Allow using Pythonic names too

class DailyNextDayPreview(BaseModel):
    """Structure for the preview of the next day's events."""
    date: str = Field(..., description="Next day's date, e.g., 'April 22, 2025'.")
    description: str = Field(..., description="Preview or note about the next day.")

class DailyHighlights(BaseModel):
    """Structure for the daily highlights section."""
    date: str = Field(..., description="Full date, including day of week, e.g., 'Monday, April 21, 2025'.")
    todays_key_events: List[CalendarEvent] = Field(..., alias="todaysKeyEvents", description="List of key events happening today.")
    next_day_preview: DailyNextDayPreview = Field(..., alias="nextDayPreview", description="Preview for the next day.")

    class Config:
        allow_population_by_field_name = True # Allow using Pythonic names too

class EconomicCalendar(BaseModel):
    """Top-level model for the economic calendar JSON output."""
    title: str = Field(..., description="The title of the economic calendar.")
    monthly_calendar: MonthlyCalendar = Field(..., alias="monthlyCalendar")
    monthly_past_events_summary: List[MonthlySummaryItem] = Field(..., alias="monthlyPastEventsSummary")
    monthly_upcoming_events_summary: List[CalendarEvent] = Field(..., alias="monthlyUpcomingEventsSummary", description="Summary uses CalendarEvent structure for upcoming items.") # Adjusted to match schema's use of title/relevance/desc
    weekly_highlights: WeeklyHighlights = Field(..., alias="weeklyHighlights")
    daily_highlights: DailyHighlights = Field(..., alias="dailyHighlights")

    class Config:
        allow_population_by_field_name = True # Allow using Pythonic names too