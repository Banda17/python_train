import pandas as pd
from datetime import datetime
import streamlit as st
from google.oauth2 import service_account
import gspread
import json
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_wtt_times():
    """Load Working Time Table times from bhanu.json"""
    try:
        logger.info("Loading WTT times from bhanu.json")
        with open('bhanu.json', 'r') as f:
            wtt_data = json.load(f)
        return wtt_data
    except Exception as e:
        logger.error(f"Error loading WTT times: {str(e)}")
        return None

def get_wtt_time(train_number, station, wtt_data):
    """Get WTT time for a specific train and station"""
    try:
        if not wtt_data or not station in wtt_data:
            return ''
        station_data = wtt_data[station].get('Dep', {}).get('times', {})
        return station_data.get(str(train_number), '')
    except Exception as e:
        logger.warning(f"Error getting WTT time for train {train_number} at {station}: {str(e)}")
        return ''

def determine_train_status(time_diff):
    """Determine if train is early, on time, or late"""
    try:
        if not time_diff or time_diff == "N/A":
            return ""
        diff = int(time_diff.replace("+", ""))
        if diff < -5:  # More than 5 minutes early
            return "EARLY"
        elif diff > 5:  # More than 5 minutes late
            return "LATE"
        else:
            return "ON TIME"
    except Exception as e:
        logger.warning(f"Error determining train status: {str(e)}")
        return ""

def initialize_google_sheets():
    """Initialize Google Sheets connection using service account."""
    try:
        logger.info("Initializing Google Sheets connection...")
        with open('nimble-willow-433310-n1-f8d544889cfe.json', 'r') as f:
            credentials_info = json.load(f)

        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ],
        )
        client = gspread.authorize(credentials)
        logger.info("Google Sheets connection initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets: {str(e)}")
        st.error(f"Failed to initialize Google Sheets: {str(e)}")
        return None

def get_sheet_data(client, sheet_id):
    """Fetch data from Google Sheets."""
    try:
        logger.info(f"Fetching data from sheet: {sheet_id}")
        sheet = client.open_by_key(sheet_id).sheet1
        values = sheet.get_all_values()

        if len(values) < 3:
            logger.warning("Sheet is empty or has insufficient data")
            st.error("Sheet is empty or has insufficient data")
            return None

        # Define headers for the sheet data
        headers = [
            'timestamp', 'empty_col', 'BD No', 'Sl No', 'Train Name', 
            'LOCO', 'Station', 'Status', 'Time', 'Remarks', 'FOISID', 'uid'
        ]

        # Start from row 3 (index 2) as per sheets.ts
        data_rows = values[2:]
        logger.info(f"Retrieved {len(data_rows)} rows of data")

        # Create DataFrame with specified headers
        df = pd.DataFrame(data_rows, columns=headers)

        # Map columns to required format
        column_mapping = {
            'Train Name': 'Train Name',
            'Station': 'Location',
            'Status': 'Status',
            'Time': 'JUST TIME'
        }

        df = df.rename(columns=column_mapping)

        # Select only needed columns
        required_columns = ['Train Name', 'Location', 'Status', 'JUST TIME']
        df = df[required_columns]

        # Format time columns
        df['JUST TIME'] = df['JUST TIME'].apply(format_time)

        # Load WTT times
        wtt_data = load_wtt_times()

        # Extract train numbers and add WTT times
        def extract_train_number(train_name):
            try:
                if not isinstance(train_name, str):
                    return ''
                match = re.match(r'^\d+', train_name)
                return match.group() if match else ''
            except Exception as e:
                logger.warning(f"Error extracting train number from {train_name}: {str(e)}")
                return ''

        # Add WTT time and calculate differences
        df['WTT TIME'] = df.apply(
            lambda row: get_wtt_time(
                extract_train_number(row['Train Name']),
                row['Location'],
                wtt_data
            ),
            axis=1
        )

        # Calculate time differences
        df['Time Difference'] = df.apply(
            lambda x: calculate_time_difference(x['JUST TIME'], x['WTT TIME']),
            axis=1
        )

        # Add train running status
        df['Running Status'] = df['Time Difference'].apply(determine_train_status)

        # Filter out rows with empty train numbers or invalid data
        df = df[df.apply(lambda x: bool(extract_train_number(x['Train Name'])), axis=1)]

        return df
    except Exception as e:
        logger.error(f"Failed to fetch sheet data: {str(e)}")
        st.error(f"Failed to fetch sheet data: {str(e)}")
        return None

def format_time(time_str):
    """Format time string to show only HH:MM."""
    try:
        if not isinstance(time_str, str) or not time_str.strip():
            return ''

        # Skip header row
        if time_str.lower() == 'time':
            return ''

        # Extract time pattern (HH:MM or HH;MM) from the string
        time_pattern = re.search(r'(\d{1,2})[;:](\d{2})', time_str)
        if time_pattern:
            hours, minutes = time_pattern.groups()
            # Ensure hours are in 24-hour format
            hours = int(hours)
            if hours < 24:
                return f"{hours:02d}:{minutes}"
            return ''

        # If no pattern found, try direct parsing
        try:
            parsed_time = pd.to_datetime(time_str, format='%H:%M').strftime('%H:%M')
            return parsed_time
        except:
            return ''

    except Exception as e:
        logger.warning(f"Failed to parse time: {time_str}, error: {str(e)}")
        return ''

def calculate_time_difference(just_time, wtt_time):
    """Calculate time difference in minutes between JUST and WTT times."""
    try:
        if not just_time or not wtt_time:
            return "N/A"
        just = datetime.strptime(just_time, "%H:%M")
        wtt = datetime.strptime(wtt_time, "%H:%M")
        diff = (just - wtt).total_seconds() / 60
        return f"+{int(diff)}" if diff >= 0 else str(int(diff))
    except Exception as e:
        logger.warning(f"Failed to calculate time difference: {str(e)}")
        return "N/A"

def apply_filters(df, status_filter):
    """Apply filters to the dataframe."""
    try:
        if status_filter != "All":
            df = df[df['Status'] == status_filter]
            logger.info(f"Applied status filter: {status_filter}, {len(df)} rows remaining")
        return df
    except Exception as e:
        logger.error(f"Error applying filters: {str(e)}")
        return df