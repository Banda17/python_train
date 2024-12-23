import pandas as pd
from datetime import datetime
import streamlit as st
from google.oauth2 import service_account
import gspread
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_google_sheets():
    """Initialize Google Sheets connection using service account."""
    try:
        logger.info("Initializing Google Sheets connection...")
        # Read credentials from JSON file
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
        # Get all values as a list of lists
        values = sheet.get_all_values()

        if len(values) < 3:  # Need at least header row and one data row
            logger.warning("Sheet is empty or has insufficient data")
            st.error("Sheet is empty or has insufficient data")
            return None

        # Define column headers based on sheets.ts reference
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
            'Sl No': 'Serial Number',
            'LOCO': 'Locomotive Number',
            'Station': 'Location',
            'Time': 'JUST TIME',
            'Remarks': 'WTT TIME'
        }

        df = df.rename(columns=column_mapping)

        # Select only needed columns and filter trains starting with numbers
        required_columns = ['Serial Number', 'Train Name', 'Locomotive Number',
                          'Location', 'Status', 'JUST TIME', 'WTT TIME']

        # Filter columns and handle missing ones
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]

        # Format time columns to HH:MM
        def format_time(time_str):
            try:
                if not isinstance(time_str, str) or not time_str.strip():
                    return ''
                # Try parsing the time string and format to HH:MM
                parsed_time = pd.to_datetime(time_str, format='%H:%M').strftime('%H:%M')
                return parsed_time
            except Exception as e:
                logger.warning(f"Failed to parse time: {time_str}, error: {str(e)}")
                return time_str

        df['JUST TIME'] = df['JUST TIME'].apply(format_time)
        df['WTT TIME'] = df['WTT TIME'].apply(format_time)

        # Filter trains starting with numbers
        df = df[df['Train Name'].str.match(r'^\d.*', na=False)]
        logger.info(f"Processed {len(df)} rows after filtering")

        return df
    except Exception as e:
        logger.error(f"Failed to fetch sheet data: {str(e)}")
        st.error(f"Failed to fetch sheet data: {str(e)}")
        return None

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

def process_dataframe(df):
    """Process the dataframe to add calculated columns and format data."""
    if df is None or df.empty:
        logger.warning("No data to process in DataFrame")
        return None

    try:
        # Calculate time difference
        df['Time Difference'] = df.apply(
            lambda x: calculate_time_difference(x['JUST TIME'], x['WTT TIME']),
            axis=1
        )

        # Format status for display
        df['Status'] = df['Status'].str.upper()

        logger.info("DataFrame processed successfully")
        return df
    except Exception as e:
        logger.error(f"Error processing DataFrame: {str(e)}")
        return None

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