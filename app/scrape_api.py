import requests
import json
import time

BASE_URL = "http://localhost:3002/api/v1/serp-scrape"


def call_scrape_api(
    query, api_secret_token="default_secret_token", depth=1, clear_cache=False
):
    """
    Test the SERP-SCRAPE endpoint and return the scraped data.

    Parameters:
        base_url (str): The base URL of the API endpoint.
        api_secret_token (str): The API secret token for authentication.
        query (str): The search query parameter.
        depth (int): The depth of the scrape.
        clear_cache (bool): Whether to clear cache (optional).

    Returns:
        dict or None: The scraped data as a dictionary if successful, otherwise None.
    """
    headers = {
        "Authorization": f"Bearer {api_secret_token}",
        "Content-Type": "application/json",
    }
    # Use the provided base_url as the endpoint.
    endpoint = BASE_URL

    # Define parameters for the request.
    params = {
        "q": query,
        "depth": depth,
        "clear_cache": clear_cache,
    }

    # Make a POST request to initiate the scrape task.
    response = requests.post(endpoint, headers=headers, json=params)
    if response.status_code != 202:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    data = response.json()
    task_id = data.get("task_id")

    # Poll the status endpoint until the task is completed or fails.
    status_url = f"{BASE_URL}/{task_id}/status"
    while True:
        status_resp = requests.get(status_url, headers=headers)
        if status_resp.text.strip() == "":
            print("Received an empty response")
        else:
            status_data = status_resp.json()
        print("Current status:", status_data.get("status"))
        if status_data.get("status") == "completed":
            break
        if status_data.get("status") == "failed":
            print("Scrape failed with error:", status_data.get("error"))
            return None
        time.sleep(10)

    # Retrieve the scraped data from the completed task.
    data_url = f"{BASE_URL}/{task_id}/data"
    data_resp = requests.get(data_url, headers=headers)
    scraped_data = data_resp.json()
    return scraped_data
