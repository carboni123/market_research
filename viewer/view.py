# viewer/view.py
import os
import sys
import logging
from datetime import datetime, timezone
from flask import Flask, Response, render_template, request, redirect, url_for, abort
import mistune

# --- Setup Project Paths ---
# Assuming view.py is in market_research/viewer/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_PATH = os.path.join(BASE_DIR, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# --- Import Core Components ---
try:
    from market_research.core.user_database import UserDatabase
    # Adjust import path based on calendar_parser.py location
    from market_research.core.calendar_parser import SummaryParser, CalendarParser
    from market_research.config import config # Import config to get DB path if needed
except ImportError as e:
    logging.error(f"Error importing project modules: {e}")
    logging.error(f"BASE_DIR: {BASE_DIR}, SRC_PATH: {SRC_PATH}")
    sys.exit(f"Failed to import necessary modules. Check PYTHONPATH and file structure. Error: {e}")

# --- Flask App Setup ---
app = Flask(__name__)
# Get DB path from config, assuming UserDatabase uses it by default now
# If UserDatabase needs explicit path: db = UserDatabase(db_path=config.USER_DB_PATH)
db = UserDatabase() # Assumes UserDatabase correctly finds config.USER_DB_PATH

# --- Helper to get User ID (Replace with proper session/auth later) ---
def get_current_user_id():
    """Returns a hardcoded user ID for demonstration."""
    # In a real app, get this from flask session, login manager, etc.
    # Ensure this user exists (e.g., run user_database.py example once)
    user = db.get_user("alice")
    if user:
        return user[0] # Return the ID
    else:
        # Optionally create 'alice' if she doesn't exist
        user_id = db.add_user("alice", "alice@example.com", "hashedpassword123")
        if user_id:
            logging.info("Created demo user 'alice'")
            return user_id
        else:
            # Fallback or raise error if user cannot be found/created
            logging.error("Default user 'alice' not found and could not be created.")
            return 1 # Fallback to 1, but this might cause issues

# --- Routes ---
@app.context_processor
def inject_now():
    """Injects the 'now' variable into the template context."""
    return {'now': datetime.now(timezone.utc)}

@app.route('/')
def index():
    user_id = get_current_user_id()
    if not user_id:
         return "User 'alice' not found or could not be created. Cannot display data.", 500

    # Fetch results (now including ID as the first element)
    summaries = db.get_summary_results(user_id)
    calendars = db.get_calendar_results(user_id)
    # Pass user_id for links in template if needed elsewhere
    return render_template('index.html', summaries=summaries, calendars=calendars, user_id=user_id)

# --- Routes for Viewing Specific Items ---

@app.route('/view/summary/<int:summary_id>')
def view_summary(summary_id):
    user_id = get_current_user_id() # Optional: Check if this summary belongs to the current user
    summary_data = db.get_summary_by_id(summary_id)

    if not summary_data: # or summary_data[1] != user_id: # Add user check if needed
        abort(404, description="Summary not found or access denied.")

    # The actual JSON string is the 5th element (index 4)
    raw_json_string = summary_data[4]
    summary_type = summary_data[2]
    keyword = summary_data[3]
    created_at = summary_data[5]

    title = f"Summary: {summary_type} - {keyword} ({created_at})"
    html_content = "[Error: Could not parse content]" # Default error message

    try:
        # 1. Use the appropriate parser to generate Markdown lines
        parser = SummaryParser(raw_json_string) # Parser handles JSON extraction
        md_lines = parser.generate_markdown()
        markdown_string = "\n".join(md_lines)

        # 2. Convert Markdown string to HTML
        html_content = mistune.html(markdown_string)

    except Exception as e:
        logging.error(f"Error processing summary ID {summary_id}: {e}", exc_info=True)
        # html_content remains the error message

    return render_template('view_item.html', title=title, content=html_content)


@app.route('/view/calendar/<int:calendar_id>')
def view_calendar(calendar_id):
    user_id = get_current_user_id() # Optional: Check ownership
    calendar_data = db.get_calendar_by_id(calendar_id)

    if not calendar_data: # or calendar_data[1] != user_id:
        abort(404, description="Calendar not found or access denied.")

    # ... (rest of the view_calendar function remains the same) ...
    raw_json_string = calendar_data[2]
    created_at = calendar_data[3]

    title = f"Calendar Event ({created_at})"
    html_content = "[Error: Could not parse content]"

    try:
        parser = CalendarParser(raw_json_string)
        md_lines = parser.generate_markdown()
        markdown_string = "\n".join(md_lines)
        html_content = mistune.html(markdown_string)
    except Exception as e:
        logging.error(f"Error processing calendar ID {calendar_id}: {e}", exc_info=True)

    return render_template('view_item.html', title=title, content=html_content)


@app.route('/download_summary/<int:summary_id>') # Changed param to ID
def download_summary(summary_id):
    summary_data = db.get_summary_by_id(summary_id)
    if not summary_data:
        return "Summary not found", 404

    raw_json_string = summary_data[4]
    summary_type = summary_data[2]
    keyword = summary_data[3]
    filename = f"summary_{summary_type}_{keyword.replace(' ','_')}_{summary_id}.md"

    try:
        generator = SummaryParser(raw_json_string)
        md_lines = generator.generate_markdown()
        markdown_output = "\n".join(md_lines)
    except Exception as e:
        logging.error(f"Error generating markdown for download (Summary ID {summary_id}): {e}")
        return "Error generating file", 500

    return Response(
        markdown_output,
        mimetype='text/markdown', # Use text/markdown mimetype
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/download_calendar/<int:calendar_id>') # Changed param to ID
def download_calendar(calendar_id):
    calendar_data = db.get_calendar_by_id(calendar_id)
    if not calendar_data:
        return "Calendar not found", 404

    raw_json_string = calendar_data[2]
    created_at_str = calendar_data[3].replace(" ", "_").replace(":", "-")
    filename = f"calendar_{created_at_str}_{calendar_id}.md"

    try:
        generator = CalendarParser(raw_json_string)
        md_lines = generator.generate_markdown()
        markdown_output = "\n".join(md_lines)
    except Exception as e:
        logging.error(f"Error generating markdown for download (Calendar ID {calendar_id}): {e}")
        return "Error generating file", 500

    return Response(
        markdown_output,
        mimetype='text/markdown', # Use text/markdown mimetype
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# --- Management/Example Routes (Keep or adapt based on needs) ---

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']  # In production, hash the password!
        user_id = db.add_user(username, email, password)
        if user_id:
            return redirect(url_for('index'))
        else:
            # Provide more specific feedback if user exists
            existing_user = db.get_user(username)
            if existing_user:
                 error_msg = f"Error: Username '{username}' already exists."
            else:
                 error_msg = "Error adding user (check logs)."
            # Pass error to template or return simple error page
            return render_template('add_user.html', error=error_msg)
    return render_template('add_user.html') # Display form

@app.route('/portfolio') # Removed user_id from URL, get from helper
def portfolio():
    user_id = get_current_user_id()
    if not user_id:
         return "User not found.", 404
    portfolio_info = db.get_portfolio(user_id)
    portfolio_data = portfolio_info[0] if portfolio_info else ""
    # Pass user_id for form submission if needed, though not strictly necessary if using get_current_user_id() on POST
    return render_template('portfolio.html', portfolio_data=portfolio_data, user_id=user_id)

@app.route('/update_portfolio', methods=['POST']) # Specific route for POST
def update_portfolio():
    user_id = get_current_user_id()
    if not user_id:
         return "User not found.", 404
    portfolio_data = request.form['portfolio_data']
    db.update_portfolio(user_id, portfolio_data)
    return redirect(url_for('portfolio')) # Redirect back to portfolio view

@app.route('/view_summaries')
def view_summaries():
    user_id = get_current_user_id()
    if not user_id: return "User not found.", 404
    summaries = db.get_summary_results(user_id)
    # Render a specific template if you want a different layout than index
    return render_template('view_summaries.html', summaries=summaries)

@app.route('/view_calendar')
def view_calendar_list():
    user_id = get_current_user_id()
    if not user_id: return "User not found.", 404
    calendars = db.get_calendar_results(user_id)
    # Render a specific template if you want a different layout than index
    return render_template('view_calendar.html', calendars=calendars)

# Optional endpoints to add new summary and calendar entries (for testing/manual input)
@app.route('/add_summary', methods=['GET', 'POST'])
def add_summary():
    user_id = get_current_user_id()
    if not user_id: return "User not found.", 404

    if request.method == 'POST':
        summary_type = request.form['summary_type']
        keyword = request.form['keyword']
        summary_text = request.form['summary'] # Should be the raw JSON string here
        db.add_summary_result(user_id, summary_type, keyword, summary_text)
        return redirect(url_for('view_summaries'))
    # Pass user_id to pre-fill if needed, though get_current_user_id is used on POST
    return render_template('add_summary.html', user_id=user_id)

@app.route('/add_calendar', methods=['GET', 'POST'])
def add_calendar():
    user_id = get_current_user_id()
    if not user_id: return "User not found.", 404

    if request.method == 'POST':
        calendar_result = request.form['calendar_result'] # Should be the raw JSON string
        db.add_calendar_result(user_id, calendar_result)
        return redirect(url_for('view_calendar'))
    # Pass user_id to pre-fill if needed
    return render_template('add_calendar.html', user_id=user_id)


# --- Teardown ---
@app.teardown_appcontext
def close_connection(exception):
    # Ensure the database connection is closed when the app context ends
    # This is generally good practice, although UserDatabase might manage its own lifecycle
    # If db instance is per-request, this is more important. If it's global like here,
    # closing might be handled differently or on app shutdown.
    # For simplicity here, we won't explicitly close the global `db` instance on each request.
    # If using Flask patterns like application factories, db connection management would differ.
    pass

# --- Main Execution ---
if __name__ == '__main__':
    # Ensure the templates directory exists relative to this script
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.isdir(template_dir):
        print(f"Warning: Template directory not found at {template_dir}")

    # Ensure the static directory exists relative to this script
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not os.path.isdir(static_dir):
         print(f"Warning: Static directory not found at {static_dir}")
         # Create if it doesn't exist? Or just warn. Let's warn for now.
         # os.makedirs(static_dir, exist_ok=True)

    # Set template and static folders explicitly if needed
    app.template_folder = template_dir
    app.static_folder = static_dir

    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")

    # Add basic logging for Flask
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    # Ensure 'alice' user exists before starting
    _ = get_current_user_id()

    app.run(debug=True) # debug=True enables auto-reloading and detailed errors