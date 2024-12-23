import pandas as pd
from datetime import datetime
import streamlit as st
from google.oauth2 import service_account
import gspread
import json

def initialize_google_sheets():
    """Initialize Google Sheets connection using service account."""
    try:
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
        return client
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets: {str(e)}")
        return None

def get_sheet_data(client, sheet_id):
    """Fetch data from Google Sheets."""
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        # Get all values as a list of lists
        values = sheet.get_all_values()

        if len(values) < 3:  # Need at least header row and one data row
            st.error("Sheet is empty or has insufficient data")
            return None

        # Define column headers based on sheets.ts reference
        headers = [
            'timestamp', 'empty_col', 'BD No', 'Sl No', 'Train Name', 
            'LOCO', 'Station', 'Status', 'Time', 'Remarks', 'FOISID', 'uid'
        ]

        # Start from row 3 (index 2) as per sheets.ts
        data_rows = values[2:]

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
                # Try parsing the time string and format to HH:MM
                parsed_time = pd.to_datetime(time_str, format='%H:%M').strftime('%H:%M')
                return parsed_time
            except:
                return time_str

        df['JUST TIME'] = df['JUST TIME'].apply(format_time)
        df['WTT TIME'] = df['WTT TIME'].apply(format_time)

        # Filter trains starting with numbers
        df = df[df['Train Name'].str.match(r'^\d.*', na=False)]

        return df
    except Exception as e:
        st.error(f"Failed to fetch sheet data: {str(e)}")
        return None

def calculate_time_difference(just_time, wtt_time):
    """Calculate time difference in minutes between JUST and WTT times."""
    try:
        just = datetime.strptime(just_time, "%H:%M")
        wtt = datetime.strptime(wtt_time, "%H:%M")
        diff = (just - wtt).total_seconds() / 60
        return f"+{int(diff)}" if diff >= 0 else str(int(diff))
    except:
        return "N/A"

def process_dataframe(df):
    """Process the dataframe to add calculated columns and format data."""
    if df is None or df.empty:
        return None

    # Calculate time difference
    df['Time Difference'] = df.apply(
        lambda x: calculate_time_difference(x['JUST TIME'], x['WTT TIME']),
        axis=1
    )

    # Format status for display
    df['Status'] = df['Status'].str.upper()

    return df

def apply_filters(df, status_filter):
    """Apply filters to the dataframe."""
    if status_filter != "All":
        df = df[df['Status'] == status_filter]
    return df