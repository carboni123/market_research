import time
import requests
import json


def call_scrape_api(
    query,
    api_secret_token="default_secret_token",
    depth=1,
    cache_type="dynamic",
    clear_cache=False,
):
    headers = {
        "Authorization": f"Bearer {api_secret_token}",
        "Content-Type": "application/json",
    }
    endpoint = "http://localhost:3002/api/v1/serp-scrape"

    # Initiate task
    response = requests.post(
        endpoint,
        headers=headers,
        json={
            "q": query,
            "depth": depth,
            "cache_type": cache_type,
            "clear_cache": clear_cache,
        },
    )
    if response.status_code != 202:
        print(f"Error: {response.status_code} - {response.text}")
        return "Error: Unable to initiate scrape task."
    task_id = response.json().get("task_id")
    status_url = f"{endpoint}/{task_id}/status"

    # Poll with timeout
    start_time = time.time()
    max_wait_time = 300  # 5 minutes
    while True:
        status_resp = requests.get(status_url, headers=headers)
        try:
            status_data = (
                status_resp.json()
                if status_resp.text.strip()
                else {"status": "unknown"}
            )
        except json.JSONDecodeError:
            print("Failed to parse status response")
            status_data = {"status": "error"}
        print(
            f"Current status: {status_data.get('status')} (elapsed: {time.time() - start_time:.2f}s)"
        )
        if status_data.get("status") == "completed":
            break
        if status_data.get("status") in ["failed", "error"]:
            print("Scrape failed or errored")
            return "Error: Scrape task failed or errored."
        if time.time() - start_time > max_wait_time:
            print("Timeout: Task did not complete within 5 minutes.")
            return "Error: Task did not complete within the maximum wait time."
        time.sleep(10)

    # Retrieve data
    data_url = f"{endpoint}/{task_id}/data"
    data_resp = requests.get(data_url, headers=headers)
    if data_resp.status_code != 200:
        print(f"Error retrieving data: {data_resp.status_code} - {data_resp.text}")
        return "Error: Unable to retrieve scraped data."
    return data_resp.json().get("data")
