# Market Research Automation Project

## Overview

This project automates the process of gathering, analyzing, and summarizing market research data. It leverages external APIs (specifically OpenAI with web search capabilities) to fetch real-time information based on predefined market keywords and user-specific portfolio holdings. The system generates structured summaries, analyzes the combined data, and creates daily/weekly/monthly event calendars. Results are cached, stored in a user database, and can be viewed through a simple Flask web interface.

## Features

*   **Automated Data Gathering:** Fetches market news and data using API calls based on general market keywords and user portfolio specifics.
*   **LLM-Powered Analysis:** Uses OpenAI's models (like GPT-4o mini) to synthesize search results, analyze data, and generate summaries.
*   **Portfolio Integration:** Extracts keywords from a user's portfolio (`user_portfolio.txt`) to fetch relevant company news and earnings information.
*   **Calendar Generation:** Creates structured monthly, weekly, and daily event calendars based on the analyzed data.
*   **Caching:** Implements a local cache (`cache.db`) to avoid redundant API calls and speed up processing.
*   **User Data Persistence:** Stores user information, summaries, and calendars in a SQLite database (`user_data.db`).
*   **Web Viewer:** A basic Flask application (`viewer/`) to display summaries and calendars stored in the database and allow downloads.
*   **Tool Integration:** Designed to use OpenAI's built-in web search tool and potentially custom tools via `ApiToolFactory`.

## Project Structure

```
market_research/
├── data/                 # Databases and user data files
│   ├── cache.db          # Cache for API results
│   ├── user_data.db      # User accounts, summaries, calendars
│   └── user_portfolio.txt # User's stock portfolio (JSON format)
├── docs/                 # Documentation, prompts, examples
├── scripts/              # Utility scripts (e.g., db conversion)
├── src/
│   └── market_research/
│       ├── api/          # API interaction modules (OpenAI, tools)
│       ├── core/         # Core logic (parsing, keywords, db interaction)
│       ├── prompts/      # LLM prompt generation functions
│       ├── __init__.py
│       └── main.py       # Main execution script
├── tests/                # Unit and integration tests
│   └── test_api.py       # Tests for the API modules
├── viewer/               # Flask web application for viewing results
│   ├── static/           # CSS, JS files (if any)
│   ├── templates/        # HTML templates
│   └── view.py           # Flask app routes
├── README.md             # This file
└── requirements.txt      # Project dependencies
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd market_research
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up Environment Variables:**
    Create a `.env` file in the project root directory (`market_research/`) and add your OpenAI API key:
    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    ```
5.  **Prepare User Portfolio:**
    Edit the `data/user_portfolio.txt` file with your stock holdings in the specified JSON format. See `docs/user_portfolio_example.md` for guidance.

## Usage

1.  **Run the Main Analysis Script:**
    This script will fetch data, generate summaries, perform analysis, create a calendar, and store results in `data/user_data.db`.
    ```bash
    python src/market_research/main.py
    ```
    *Note: The script currently defaults to processing for a user named "alice". Modify `main.py` if needed.*
    Analysis outputs (summaries, calendar) are also saved as `.txt` files in the `analysis/` directory.

2.  **Run the Web Viewer:**
    This allows you to view the summaries and calendars stored in the database.
    ```bash
    python viewer/view.py
    ```
    Open your web browser and navigate to `http://127.0.0.1:5000`.

## Key Components

*   **`src/market_research/main.py`:** Orchestrates the data fetching, analysis, and calendar generation process.
*   **`src/market_research/api/openai_api.py`:** Handles interactions with the OpenAI API, including using the web search tool.
*   **`src/market_research/core/keywords.py`:** Defines market keywords and extracts portfolio-specific keywords.
*   **`src/market_research/core/user_database.py`:** Manages the SQLite database for users, summaries, and calendars.
*   **`src/market_research/prompts/`:** Contains functions that generate the specific prompts used for LLM calls (analysis, calendar creation, data synthesis).
*   **`viewer/view.py`:** Flask application serving the web interface.

## Testing

Unit tests are located in the `tests/` directory. To run the tests:

```bash
pytest tests/
```

*Note: Tests currently focus on the API layer and use mocking to avoid actual API calls.*

## Contributing

Contributions are welcome! Please follow standard Gitflow practices (fork, feature branch, pull request). Ensure new code includes relevant tests.

## License

(Specify your license here, e.g., MIT License)
