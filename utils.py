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

        # Select only needed columns
        required_columns = ['Serial Number', 'Train Name', 'Date', 'Locomotive Number',
                          'Location', 'Status', 'JUST TIME', 'WTT TIME']

        # Add Date column from timestamp if needed
        if 'Date' not in df.columns and 'timestamp' in df.columns:
            df['Date'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')

        # Filter columns and handle missing ones
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]

        # Check if we have all required columns
        missing_columns = set(required_columns) - set(available_columns)
        if missing_columns:
            st.warning(f"Missing columns in sheet: {', '.join(missing_columns)}")
            # Add missing columns with empty values
            for col in missing_columns:
                df[col] = ''

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

    # Convert date column if needed
    if 'Date' in df.columns:
        try:
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        except:
            pass

    return df

def apply_filters(df, status_filter):
    """Apply filters to the dataframe."""
    if status_filter != "All":
        df = df[df['Status'] == status_filter]
    return df