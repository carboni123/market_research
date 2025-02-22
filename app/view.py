from flask import Flask, Response, render_template, request, redirect, url_for
from user_database import UserDatabase
import json
from calendar_parser import CalendarParser

app = Flask(__name__)
db = UserDatabase()

@app.route('/')
def index():
    # For demonstration, assume user_id 1; in production, use session data.
    user_id = 1
    summaries = db.get_summary_results(user_id)
    calendars = db.get_calendar_results(user_id)
    return render_template('index.html', summaries=summaries, calendars=calendars)

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
            return "Error adding user", 400
    return render_template('add_user.html')

@app.route('/portfolio/<int:user_id>', methods=['GET', 'POST'])
def portfolio(user_id):
    if request.method == 'POST':
        portfolio_data = request.form['portfolio_data']
        db.update_portfolio(user_id, portfolio_data)
        return redirect(url_for('portfolio', user_id=user_id))
    portfolio_info = db.get_portfolio(user_id)
    return render_template('portfolio.html', portfolio=portfolio_info)

@app.route('/view_summaries')
def view_summaries():
    # Using default user_id=1 for demonstration purposes.
    user_id = 1
    summaries = db.get_summary_results(user_id)
    return render_template('view_summaries.html', summaries=summaries)

@app.route('/view_calendar')
def view_calendar():
    # Using default user_id=1 for demonstration purposes.
    user_id = 1
    calendars = db.get_calendar_results(user_id)
    return render_template('view_calendar.html', calendars=calendars)

# Optional endpoints to add new summary and calendar entries
@app.route('/add_summary', methods=['GET', 'POST'])
def add_summary():
    if request.method == 'POST':
        user_id = int(request.form['user_id'])  # In production, use session data
        summary_type = request.form['summary_type']
        keyword = request.form['keyword']
        summary_text = request.form['summary']
        db.add_summary_result(user_id, summary_type, keyword, summary_text)
        return redirect(url_for('view_summaries'))
    return render_template('add_summary.html')

@app.route('/add_calendar', methods=['GET', 'POST'])
def add_calendar():
    if request.method == 'POST':
        user_id = int(request.form['user_id'])  # In production, use session data
        calendar_result = request.form['calendar_result']
        db.add_calendar_result(user_id, calendar_result)
        return redirect(url_for('view_calendar'))
    return render_template('add_calendar.html')

@app.route('/download_summary/<int:summary_index>')
def download_summary(summary_index):
    # Using default user_id=1 for demonstration purposes
    user_id = 1
    summaries = db.get_summary_results(user_id)
    if not summaries or summary_index < 0 or summary_index >= len(summaries):
        return "Summary not found", 404

    # Retrieve the JSON schema stored in the summary (assumed at index 2)
    summary_text = summaries[summary_index][2]
    try:
        schema_data = json.loads(summary_text)
    except Exception as e:
        return f"Error parsing JSON schema: {e}", 400

    # Generate Markdown using the MarkdownGenerator class
    generator = CalendarParser(schema_data)
    md_lines = generator.generate_markdown()
    markdown_output = "\n".join(md_lines)

    return Response(
        markdown_output,
        mimetype='text/plain',
        headers={"Content-Disposition": "attachment; filename=summary.md"}
    )

@app.route('/download_calendar/<int:calendar_index>')
def download_calendar(calendar_index):
    # Using default user_id=1 for demonstration purposes
    user_id = 1
    calendars = db.get_calendar_results(user_id)
    if not calendars or calendar_index < 0 or calendar_index >= len(calendars):
        return "Calendar event not found", 404

    # Retrieve the JSON schema stored in the calendar event (assumed at index 0)
    calendar_text = calendars[calendar_index][0]
    # Generate Markdown using the MarkdownGenerator class
    generator = CalendarParser(calendar_text)
    md_lines = generator.generate_markdown()
    markdown_output = "\n".join(md_lines)

    return Response(
        markdown_output,
        mimetype='text/plain',
        headers={"Content-Disposition": "attachment; filename=calendar_event.md"}
    )


if __name__ == '__main__':
    app.run(debug=True)
