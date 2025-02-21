PROMPT = """
https://www.investing.com/equities/nvidia-corp-historical-data
You are provided with input representing a historical data page for a stock. The input may be either an HTML version of the webpage or a JPG screenshot containing the historical data table. Your task is to extract the relevant numerical data for three different time intervals:

Last 30 Days
Last 48 Weeks
Last 60 Months
For each period, please extract the following fields (if available):

Date
Open Price
High Price
Low Price
Close Price
Volume
Requirements:

Output the results in JSON format with three top-level keys: "last_30_days", "last_48_weeks", and "last_60_months".
Under each key, provide an array of objects. Each object should represent one data record with keys: "date", "open", "high", "low", "close", and "volume".
If a particular data field is missing for any record, set its value to null.
Focus solely on extracting data relevant to these periods and fields—do not include any additional commentary.
**Example Output Format:**

```json
{
  "last_30_days": [
    {
      "date": "2025-02-14",
      "open": 150.25,
      "high": 152.00,
      "low": 149.50,
      "close": 151.10,
      "volume": 1200000,
      "change": 1.00
    },
    ...
  ],
  "last_48_weeks": [
    {
      "date": "2024-03-31",
      "open": 140.00,
      "high": 142.50,
      "low": 139.00,
      "close": 141.00,
      "volume": 1100000,
      "change": 1.00
    },
    ...
  ],
  "last_60_months": [
    {
      "date": "2020-02-28",
      "open": 100.00,
      "high": 105.00,
      "low": 98.00,
      "close": 103.50,
      "volume": 1500000,
      "change": 5.00
    },
    ...
  ]
}
```
"""