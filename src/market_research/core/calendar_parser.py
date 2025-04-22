# src/market_research/core/calendar_parser.py
import argparse
import json
import re
import sys
import logging
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def format_key(key):
    """Convert a key into a formatted, readable name."""
    # Simple version: Replace underscores, Title Case
    return key.replace('_', ' ').title()
    # More complex version if needed (like splitting camelCase):
    # parts = re.split(r'(?=[A-Z])', key)
    # words = [part.capitalize() for part in parts if part] # Skip empty strings
    # return ' '.join(words) if words else key.title()


class MarkdownParser(ABC):
    def __init__(self, data):
        """Base class for markdown parsing"""
        self.data = self.extract_json_from_md(data)
        if isinstance(self.data, str):
            # If it's still a string, JSON parsing likely failed
            logging.warning(f"MarkdownParser data might not be valid JSON. Type: {type(self.data)}. Data preview: {str(data)[:200]}")
            # Keep the string data for potential direct rendering if needed
        elif not isinstance(self.data, (dict, list)):
            logging.warning(f"MarkdownParser data is not a dict or list after parsing. Type: {type(self.data)}. Data: {self.data}")


    def extract_json_from_md(self, markdown_response: str):
        """
        Extract JSON content from a Markdown response or parse directly if no markdown found.
        """
        if not isinstance(markdown_response, str):
            # If input is already parsed (e.g., dict/list), return it
            return markdown_response

        # Attempt to find JSON within markdown code block first
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", markdown_response, re.DOTALL | re.IGNORECASE)
        json_content_str = ""
        if match:
            json_content_str = match.group(1).strip()
            logging.debug("Extracted JSON content from Markdown block.")
        else:
            # If no block found, assume the entire string might be JSON
            json_content_str = markdown_response.strip()
            logging.debug("No Markdown block found, attempting to parse entire string as JSON.")

        if not json_content_str:
            logging.warning("Empty string provided for JSON parsing.")
            return markdown_response # Return original empty/whitespace string

        try:
            # Try parsing the extracted/original string
            return json.loads(json_content_str)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse string as JSON: {e}. String preview: {json_content_str[:200]}...")
            # Return the original raw string in case it was meant to be literal markdown
            return markdown_response
        except Exception as e:
            logging.error(f"Unexpected error during JSON parsing: {e}")
            # Return the original raw string
            return markdown_response

    @abstractmethod
    def generate_markdown(self):
        """Generate Markdown from the data."""
        pass

    def generate_table(self, list_of_dicts, indent=0):
        """Generate a Markdown table from a list of dictionaries."""
        lines = []
        indent_str = "  " * indent
        if not list_of_dicts or not isinstance(list_of_dicts, list) or not all(isinstance(item, dict) for item in list_of_dicts):
            return [] # Cannot generate table

        # Use keys from the first item as headers
        keys = list(list_of_dicts[0].keys())
        formatted_keys = [format_key(k) for k in keys]

        headers = "| " + " | ".join(formatted_keys) + " |"
        separator = "|-" + "-|-".join(["-" * len(fk) for fk in formatted_keys]) + "-|"
        lines.append(f"{indent_str}{headers}")
        lines.append(f"{indent_str}{separator}")

        for item in list_of_dicts:
            # Ensure row values match the header keys, handle missing keys gracefully
            row_values = [str(item.get(k, "")) for k in keys]
            row = "| " + " | ".join(row_values) + " |"
            lines.append(f"{indent_str}{row}")

        return lines

# --- CalendarParser (Keep the existing one from previous step) ---
class CalendarParser(MarkdownParser):
    def __init__(self, data):
        super().__init__(data)

    def generate_markdown(self):
        """Generate Markdown from the JSON data."""
        if not isinstance(self.data, dict):
            # Handle cases where data isn't the expected dict structure
            logging.warning(f"CalendarParser: Data is not a dictionary. Cannot generate standard calendar markdown. Type: {type(self.data)}")
            # Fallback: try to represent the data generically or return raw string
            if isinstance(self.data, str):
                return [self.data] # Return raw string if parsing failed
            else:
                 # Try a generic representation (might be complex)
                 return self.generate_generic_markdown(self.data)


        lines = []
        # Title
        title = self.data.get("title", "Economic Calendar")
        lines.append(f"# {title}\n")

        # Monthly Calendar Section
        monthly_calendar = self.data.get("monthlyCalendar")
        if monthly_calendar and isinstance(monthly_calendar, dict):
            lines.append("## Monthly Calendar\n")
            # Events by date
            events_by_date = monthly_calendar.get("events", [])
            if events_by_date:
                 lines.append("### Events by Date\n")
                 for date_group in events_by_date:
                     date = date_group.get("date", "Unknown Date")
                     lines.append(f"#### {date}\n")
                     events_list = date_group.get("events", [])
                     if events_list and isinstance(events_list[0], dict):
                         # Try generating a table if items have consistent keys
                         # Check if keys are mostly consistent first
                         keys = events_list[0].keys()
                         if all(isinstance(item, dict) and item.keys() == keys for item in events_list):
                             lines.extend(self.generate_table(events_list, indent=1))
                         else: # Fallback to list format
                            for event in events_list:
                                 lines.append(f"- **{event.get('title', 'Event')}** ({event.get('relevance', 'N/A')}):")
                                 lines.append(f"  - {event.get('description', 'No details.')}")
                     elif events_list: # List of strings?
                         for event_str in events_list:
                              lines.append(f"- {event_str}")
                     lines.append("") # Add space after date group
            else:
                 lines.append("No specific events listed for the month.\n")

            # Ongoing Events
            ongoing_events = monthly_calendar.get("ongoingEvents", [])
            if ongoing_events:
                 lines.append("### Ongoing Events\n")
                 for event in ongoing_events:
                     lines.append(f"- **{event.get('title', 'Event')}** ({event.get('relevance', 'N/A')}): {event.get('description', 'No details.')}")
                 lines.append("")

        # Monthly Past Events Summary
        past_summary = self.data.get("monthlyPastEventsSummary", [])
        if past_summary:
            lines.append("## Monthly Past Events Summary\n")
            for item in past_summary:
                lines.append(f"- **{item.get('category', 'Summary')}**: {item.get('description', 'N/A')}")
            lines.append("")

        # Monthly Upcoming Events Summary
        upcoming_summary = self.data.get("monthlyUpcomingEventsSummary", [])
        if upcoming_summary:
            lines.append("## Monthly Upcoming Events Summary\n")
            for item in upcoming_summary:
                 lines.append(f"- **{item.get('title', 'Event')}** ({item.get('relevance', 'N/A')}): {item.get('description', 'N/A')}")
            lines.append("")

        # Weekly Highlights
        weekly = self.data.get("weeklyHighlights")
        if weekly and isinstance(weekly, dict):
            week_range = weekly.get('weekRange', 'This Week')
            lines.append(f"## Weekly Highlights ({week_range})\n")
            lines.append(f"{weekly.get('description', '')}\n")
            # Process weekly past, upcoming, next week preview similarly if needed
            # Example for upcoming:
            weekly_upcoming = weekly.get("upcomingEvents", [])
            if weekly_upcoming:
                lines.append("### Upcoming This Week\n")
                for date_group in weekly_upcoming:
                     date = date_group.get("date", "Upcoming")
                     lines.append(f"#### {date}\n")
                     events_list = date_group.get("events", [])
                     # Format events_list as needed (table or list)
                     for event in events_list:
                         lines.append(f"- **{event.get('title', 'Event')}** ({event.get('relevance', 'N/A')}): {event.get('description', 'N/A')}")
                     lines.append("")
            lines.append("")

        # Daily Highlights
        daily = self.data.get("dailyHighlights")
        if daily and isinstance(daily, dict):
            date = daily.get('date', 'Today')
            lines.append(f"## Daily Highlights ({date})\n")
            # Todays Events
            todays_events = daily.get("todaysKeyEvents", [])
            if todays_events:
                 lines.append("### Today's Key Events\n")
                 for event in todays_events:
                     lines.append(f"- **{event.get('title', 'Event')}** ({event.get('relevance', 'N/A')}): {event.get('description', 'N/A')}")
                 lines.append("")
            else:
                 lines.append("No specific key events listed for today.\n")

            # Next Day Preview
            next_day = daily.get("nextDayPreview")
            if next_day and isinstance(next_day, dict):
                 lines.append("### Next Day Preview\n")
                 lines.append(f"- **Date**: {next_day.get('date', 'Tomorrow')}")
                 lines.append(f"- **Outlook**: {next_day.get('description', 'N/A')}")
                 lines.append("")

        return lines

    def generate_generic_markdown(self, obj, indent=0):
        """Fallback to generate generic Markdown for unknown structures."""
        lines = []
        indent_str = "  " * indent
        if isinstance(obj, dict):
            for key, value in obj.items():
                formatted_key = format_key(key)
                lines.append(f"{indent_str}- **{formatted_key}**:")
                lines.extend(self.generate_generic_markdown(value, indent + 1))
        elif isinstance(obj, list):
             # Attempt to generate table for uniform lists of objects
            if obj and all(isinstance(item, dict) for item in obj):
                keys = obj[0].keys()
                if all(item.keys() == keys for item in obj):
                    lines.extend(self.generate_table(obj, indent))
                else: # Fallback for non-uniform lists of dicts
                    for i, item in enumerate(obj):
                         lines.append(f"{indent_str}- Item {i+1}:")
                         lines.extend(self.generate_generic_markdown(item, indent + 1))
            else: # Simple list
                for item in obj:
                    lines.extend(self.generate_generic_markdown(item, indent))
        else:
            lines.append(f"{indent_str}{obj}")
        return lines

# --- NEW/REVISED SummaryParser ---
class SummaryParser(MarkdownParser):
    def __init__(self, data):
        super().__init__(data)

    def generate_markdown(self):
        """Generate Markdown specifically for the 'report' JSON structure."""
        lines = []

        # Check if data parsing was successful and resulted in a dictionary
        if not isinstance(self.data, dict):
            logging.error(f"SummaryParser: Input data is not a dictionary after parsing. Type: {type(self.data)}")
            if isinstance(self.data, str):
                # If it's still a string, JSON parsing failed, return the raw string
                 return [f"## Raw Data (Parsing Failed)\n\n```\n{self.data}\n```"]
            else:
                return ["## Error: Could not process summary data."]

        # Access the main 'report' object
        report_data = self.data.get("report")
        if not isinstance(report_data, dict):
             logging.error(f"SummaryParser: 'report' key not found or is not a dictionary.")
             # Fallback to generic rendering of the whole data structure
             lines.append("# Summary Data (Unexpected Format)\n")
             lines.extend(self.generate_generic_markdown(self.data))
             return lines

        # Process Title
        title = report_data.get("title", "Market Summary")
        lines.append(f"# {title}\n")

        # Process Sections
        sections = report_data.get("sections", [])
        if not isinstance(sections, list):
            logging.warning("SummaryParser: 'sections' is not a list.")
            sections = []

        for section in sections:
            if not isinstance(section, dict):
                logging.warning(f"Skipping invalid section item: {section}")
                continue

            heading = section.get("heading", "Details")
            lines.append(f"## {heading}\n")

            content = section.get("content")

            if isinstance(content, list) and content:
                # Check if it's a list of event-like dicts or portfolio dicts
                first_item = content[0]
                if isinstance(first_item, dict):
                    if "Event Type" in first_item: # Heuristic for events
                        for item in content:
                            event_type = item.get("Event Type", "Event")
                            lines.append(f"### {event_type}\n")
                            for key, value in item.items():
                                if key != "Event Type": # Don't repeat the subheading
                                    formatted_key = format_key(key)
                                    lines.append(f"- **{formatted_key}**: {value}")
                            lines.append("") # Add space between events
                    elif "Holding" in first_item: # Heuristic for portfolio
                         for item in content:
                             holding = item.get("Holding", "Portfolio Item")
                             lines.append(f"### {holding}\n")
                             for key, value in item.items():
                                 if key != "Holding":
                                     formatted_key = format_key(key)
                                     lines.append(f"- **{formatted_key}**: {value}")
                             lines.append("") # Add space between portfolio items
                    else: # Generic list of dicts - use table or list
                        lines.extend(self.generate_generic_markdown(content, indent=1)) # Use fallback

                else: # List of simple items (strings, numbers)
                    for item in content:
                        lines.append(f"- {item}")
                    lines.append("")

            elif isinstance(content, str):
                # Handle simple string content
                lines.append(f"{content}\n")
            elif content is not None:
                # Handle other non-list, non-string content (e.g., a single dict)
                lines.extend(self.generate_generic_markdown(content, indent=1))
                lines.append("")
            else:
                lines.append("No content provided for this section.\n")

        # Process Date Generated
        date_generated = report_data.get("date_generated")
        if date_generated:
            lines.append(f"**Date Generated**: {date_generated}\n")

        return lines

    def generate_generic_markdown(self, obj, indent=0):
            """Fallback to generate generic Markdown for unknown structures within content."""
            # This is similar to the CalendarParser's fallback, can be reused or specialized
            lines = []
            indent_str = "  " * indent
            if isinstance(obj, dict):
                for key, value in obj.items():
                    formatted_key = format_key(key)
                    lines.append(f"{indent_str}- **{formatted_key}**: {value}") # Simplified for summary content
            elif isinstance(obj, list):
                if obj and all(isinstance(item, dict) for item in obj):
                    # Maybe table is too much here, just list dicts
                     for i, item in enumerate(obj):
                         lines.append(f"{indent_str}- Item {i+1}:")
                         lines.extend(self.generate_generic_markdown(item, indent + 1))
                else: # Simple list
                    for item in obj:
                        lines.append(f"{indent_str}- {item}")
            else:
                lines.append(f"{indent_str}{obj}")
            return lines

# --- Helper functions
def write_markdown(content, output_file):
    """Write the Markdown content to a file."""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        logging.info(f"Markdown file written to {output_file}")
    except Exception as e:
        logging.error(f"Error writing file {output_file}: {e}")
        sys.exit(1)

def main():
    argparser = argparse.ArgumentParser(
        description="Convert JSON data to Markdown documentation."
    )
    argparser.add_argument("input_json", help="Input JSON file containing the data.")
    argparser.add_argument("output_markdown", help="Output Markdown file to write the documentation.")
    args = argparser.parse_args()

    try:
        with open(args.input_json, "r", encoding="utf-8") as infile:
            data = json.load(infile)
    except Exception as e:
        logging.error(f"Error reading input JSON file: {e}")
        sys.exit(1)

    generator = CalendarParser(data)
    md_lines = generator.generate_markdown()
    write_markdown(md_lines, args.output_markdown)

if __name__ == "__main__":
    main()
