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
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Ensure required columns exist
        required_columns = ['Serial Number', 'Train Name', 'Date', 'Locomotive Number',
                          'Location', 'Status', 'JUST TIME', 'WTT TIME']

        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            st.error(f"Missing required columns in sheet: {', '.join(missing_cols)}")
            return None

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