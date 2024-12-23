import streamlit as st
import pandas as pd
from utils import initialize_google_sheets
import time

# Page configuration
st.set_page_config(
    page_title="Headers Monitor",
    page_icon="📊",
    layout="wide"
)

# Initialize session state for refresh
if 'last_headers_refresh' not in st.session_state:
    st.session_state.last_headers_refresh = time.time()

st.title("Google Sheet Data Monitor")
st.write("This page monitors the data in the Google Sheet every 3 minutes.")

# Initialize Google Sheets client
client = initialize_google_sheets()

if client:
    # Default spreadsheet ID
    sheet_id = "1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4"

    # Auto refresh every 3 minutes
    current_time = time.time()
    if current_time - st.session_state.last_headers_refresh > 180:  # 3 minutes = 180 seconds
        st.session_state.last_headers_refresh = current_time
        st.experimental_rerun()

    try:
        # Get sheet and all data
        sheet = client.open_by_key(sheet_id).sheet1
        all_values = sheet.get_all_values()

        if len(all_values) > 0:
            # Create DataFrame with all data
            df = pd.DataFrame(all_values)

            # Set first row as headers if data exists
            if len(df.columns) > 0: # Added this check for robustness
                df.columns = df.iloc[0]
                df = df.iloc[1:]  # Remove the header row from data

            # Display all data
            st.subheader("Current Sheet Data")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            # Display metadata
            st.write(f"Total Rows: {len(df)}")
            st.write(f"Total Columns: {len(df.columns)}")

            # Display last update time
            st.write(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.error("No data found in the sheet")

    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
else:
    st.error("Failed to initialize Google Sheets connection")