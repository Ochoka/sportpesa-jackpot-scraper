# Import needed libraries
import requests
import random
import time
import json
import pandas as pd
from datetime import datetime, timezone
from tqdm import tqdm
from fake_useragent import UserAgent

# Function to generate random headers
failed_headers = set()  # Store headers that resulted in failed requests


def get_random_headers():
    """
    Generates a random User-Agent header.
    Ensures it doesn't pick a previously failed header.
    """
    ua = UserAgent()
    while True:
        new_header = {"User-Agent": ua.random}
        if new_header["User-Agent"] not in failed_headers:
            return new_header  # Use only if not in failed set


# Define function for creating timestamp
def timestamps(year, month):
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    last_millisecond_utc = int((next_month.timestamp() - 0.001) * 1000)
    last_millisecond_eat = last_millisecond_utc - (
                3 * 60 * 60 * 1000)  # Adjust for UTC+3 (EAT)
    return last_millisecond_eat


# Define function for generating timestamp list
def generate_timestamps(start_year, end_year, start_month, end_month):
    timestamps_for = []
    for year in range(start_year, end_year + 1):
        month_range_start = start_month if year == start_year else 1
        month_range_end = end_month if year == end_year else 12
        for month in range(month_range_start, month_range_end + 1):
            timestamps_for.append(timestamps(year, month))
    return timestamps_for


# Convert timestamp to date (YYYY-MM)
def convert_timestamp_to_date(timestamp):
    timestamp = int(timestamp)
    datetime_obj_eat = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
    return datetime_obj_eat.strftime('%Y-%m')


# Initialize storage
jackpot_data = []
scraped_jackpot_ids = set()
failed_timestamps = []  # List of failed timestamp URLs
failed_jackpots = []  # List of failed jackpot URLs

# Generate timestamps
start_year, end_year = 2023, 2023
start_month, end_month = 1, 6
timestamps_for = generate_timestamps(start_year, end_year, start_month,
                                     end_month)

# Loop through the archives
for timestamp in tqdm(timestamps_for, desc="Fetching Jackpot Archives"):
    url_archive = (f"https://jackpot-betslip.ke.sportpesa.com/"
                   f"api/jackpots/history?to={timestamp}&pageNum=0&pageSize=20")
    success = False  # Track success status

    for attempt in range(1, 11):  # Try up to 10 headers
        headers = get_random_headers()
        response = requests.get(url_archive, headers=headers)

        if response.status_code == 200:
            success = True
            break  # Exit loop if successful
        else:
            failed_headers.add(headers["User-Agent"])  # Store failed header

        time.sleep(random.uniform(3, 5))

    if not success:
        print(
            f"All 10 header attempts failed for jackpot played on: "
            f"{convert_timestamp_to_date(timestamp)}")
        failed_timestamps.append(url_archive)  # Store failed timestamp URL
        continue  # Skip to next timestamp

    jackpot_ids = [item["jackpotId"] for item in response.json()]
    unique_jackpot_ids = [jid for jid in jackpot_ids if
                          jid not in scraped_jackpot_ids]

    time.sleep(random.uniform(3, 5))  # Delay before next request

    # Fetch jackpot details
    for i, jackpot in enumerate(unique_jackpot_ids):
        url_details = (f"https://jackpot-betslip.ke.sportpesa.com/api"
                       f"/jackpots/history/{jackpot}/details")
        success = False  # Reset success flag

        for attempt in range(1, 11):  # Try up to 10 headers again
            headers = get_random_headers()
            response_details = requests.get(url_details, headers=headers)

            if response_details.status_code == 200:
                success = True
                break  # Exit loop if successful
            else:
                failed_headers.add(
                    headers["User-Agent"])  # Store failed header

        if not success:
            print(
                f"All 10 header attempts failed for jackpot "
                f"({jackpot}) played on week {i} of "
                f"{convert_timestamp_to_date(timestamp)}")
            failed_jackpots.append(url_details)  # Store failed jackpot URL
            continue  # Skip to next jackpot

        scraped_jackpot_ids.add(jackpot)  # Mark jackpot as scraped

        data = response_details.json()
        events = data.get("events", [])

        # Append event data
        for event in events:
            jackpot_data.append({
                "jackpotId": jackpot,
                "eventNumber": event["eventNumber"],
                "kickoffTime": event["kickoffTime"],
                "competitorHome": event["competitorHome"],
                "competitorAway": event["competitorAway"],
                "resultPick": event.get("resultPick", ""),
                "score": event.get("score", "")
            })

        time.sleep(random.uniform(3, 7))  # Delay before next request

# Convert data to DataFrame and save
historical_jackpots = pd.DataFrame(jackpot_data)
historical_jackpots.to_csv('hist_jackport17.csv', index=False)

# Save failed URLs for later debugging
with open("failed_timestamps.json", "w") as f:
    json.dump(failed_timestamps, f, indent=4)

with open("failed_jackpots.json", "w") as f:
    json.dump(failed_jackpots, f, indent=4)

print("\nScraping complete.")
print(f"Total failed timestamp URLs: {len(failed_timestamps)}")
print(f"Total failed jackpot URLs: {len(failed_jackpots)}")
