# calendar_parser.py
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
    parts = re.split(r'(?=[A-Z])', key)
    words = [part.capitalize() for part in parts if part]  # Skip empty strings
    return ' '.join(words)

class MarkdownParser(ABC):
    def __init__(self, data):
        """Base class for markdown parsing"""
        self.data = self.extract_json_from_md(data)

    def extract_json_from_md(self, markdown_response: str):
        """
        Extract JSON content from a Markdown response and clean it.
        """
        if not isinstance(markdown_response, str):
            return markdown_response
        match = re.search(r"```json\s*\n(.*?)```", markdown_response, re.DOTALL)
        if match:
            json_content = match.group(1).strip()
            try:
                return json.loads(json_content)
            except Exception as e:
                logging.error(f"Error parsing extracted JSON: {e}")
                raise e
        try:
            return markdown_response
        except Exception as e:
            logging.error(f"Error parsing markdown response as JSON: {e}")
            raise e
        
    @abstractmethod
    def generate_markdown(self):
        """Generate Markdown from the JSON data."""
        pass
    
    @abstractmethod
    def generate_data_markdown(self, obj, indent=0):
        """Generate Markdown lines from JSON data with formatted keys."""
        pass

    def is_uniform_object_list(self, arr):
        """Check if an array is a list of objects with identical keys."""
        if not arr or not isinstance(arr, list) or not all(isinstance(item, dict) for item in arr):
            return False
        keys = set(arr[0].keys())
        return all(set(item.keys()) == keys for item in arr)

    def generate_table(self, arr, indent=0):
        """Generate a Markdown table with formatted headers."""
        lines = []
        indent_str = "  " * indent
        if arr:
            keys = list(arr[0].keys())
            formatted_keys = [format_key(k) for k in keys]  # Format headers
            headers = "| " + " | ".join(formatted_keys) + " |"
            separator = "|-" + "-|-".join(["-" * len(fk) for fk in formatted_keys]) + "-|"
            lines.append(f"{indent_str}{headers}")
            lines.append(f"{indent_str}{separator}")
            for item in arr:
                row = "| " + " | ".join(str(item.get(k, "")) for k in keys) + " |"
                lines.append(f"{indent_str}{row}")
        return lines

class CalendarParser(MarkdownParser):
    def __init__(self, data):
        super().__init__(data)

    def generate_markdown(self):
        """Generate Markdown from the JSON data."""
        if isinstance(self.data, str):
            return [self.data]
        lines = []
        if "title" in self.data:
            lines.append(f"# {self.data['title']}\n")
        for section in ["monthlyCalendar", "monthlyPastEventsSummary", "monthlyUpcomingEventsSummary", "weeklyHighlights", "dailyHighlights"]:
            if section in self.data:
                section_title = format_key(section)
                lines.append(f"## {section_title}\n")
                lines.extend(self.generate_data_markdown(self.data[section]))
                lines.append("")
        return lines

    def generate_data_markdown(self, obj, indent=0):
        """Generate Markdown lines from JSON data with formatted keys."""
        lines = []
        indent_str = "  " * indent

        if isinstance(obj, dict):
            for key, value in obj.items():
                formatted_key = format_key(key)
                lines.append(f"{indent_str}- **{formatted_key}**:")
                lines.extend(self.generate_data_markdown(value, indent + 1))
        elif isinstance(obj, list):
            if all(isinstance(item, dict) and "date" in item and "events" in item for item in obj):
                # Handle arrays of date-based events (e.g., in weeklyHighlights)
                for item in obj:
                    date = item.get("date", "Unknown Date")
                    lines.append(f"{indent_str}### {date}\n")
                    events = item.get("events", [])
                    if events and isinstance(events[0], dict):
                        lines.extend(self.generate_table(events, indent + 1))
                    else:
                        lines.extend(self.generate_data_markdown(events, indent + 1))
            elif obj and isinstance(obj[0], dict):
                # Handle uniform lists as tables
                lines.extend(self.generate_table(obj, indent))
            else:
                # Fallback for simple lists
                for item in obj:
                    lines.extend(self.generate_data_markdown(item, indent))
        else:
            # Scalar values
            lines.append(f"{indent_str}{obj}")

        return lines
    
class SummaryParser(MarkdownParser):
    def __init__(self, data):
        super().__init__(data)

    def generate_markdown(self):
        """Generate Markdown from the JSON data."""
        if isinstance(self.data, str):
            return [self.data]
        lines = []
        if "title" in self.data:
            lines.append(f"# {self.data['title']}\n")
        for section in ["monthlyCalendar", "monthlyPastEventsSummary", "monthlyUpcomingEventsSummary", "weeklyHighlights", "dailyHighlights"]:
            if section in self.data:
                section_title = format_key(section)
                lines.append(f"## {section_title}\n")
                lines.extend(self.generate_data_markdown(self.data[section]))
                lines.append("")
        return lines

    def generate_data_markdown(self, obj, indent=0):
        """Generate Markdown lines from JSON data with formatted keys."""
        lines = []
        indent_str = "  " * indent

        if isinstance(obj, dict):
            for key, value in obj.items():
                formatted_key = format_key(key)
                lines.append(f"{indent_str}- **{formatted_key}**:")
                lines.extend(self.generate_data_markdown(value, indent + 1))
        elif isinstance(obj, list):
            if all(isinstance(item, dict) and "date" in item and "events" in item for item in obj):
                # Handle arrays of date-based events (e.g., in weeklyHighlights)
                for item in obj:
                    date = item.get("date", "Unknown Date")
                    lines.append(f"{indent_str}### {date}\n")
                    events = item.get("events", [])
                    if events and isinstance(events[0], dict):
                        lines.extend(self.generate_table(events, indent + 1))
                    else:
                        lines.extend(self.generate_data_markdown(events, indent + 1))
            elif obj and isinstance(obj[0], dict):
                # Handle uniform lists as tables
                lines.extend(self.generate_table(obj, indent))
            else:
                # Fallback for simple lists
                for item in obj:
                    lines.extend(self.generate_data_markdown(item, indent))
        else:
            # Scalar values
            lines.append(f"{indent_str}{obj}")

        return lines
    
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
