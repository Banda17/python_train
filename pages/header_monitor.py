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

st.title("Google Sheet Headers Monitor")
st.write("This page monitors the headers of the Google Sheet every 3 minutes.")

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
        # Get sheet and headers
        sheet = client.open_by_key(sheet_id).sheet1
        headers = sheet.row_values(1)  # First row
        subheaders = sheet.row_values(2)  # Second row
        
        # Display headers
        st.subheader("Current Sheet Headers")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Main Headers (Row 1)")
            st.dataframe(
                pd.DataFrame({'Column': list(range(1, len(headers) + 1)), 'Header': headers}),
                hide_index=True
            )
        
        with col2:
            st.write("Sub-Headers (Row 2)")
            st.dataframe(
                pd.DataFrame({'Column': list(range(1, len(subheaders) + 1)), 'Header': subheaders}),
                hide_index=True
            )
        
        # Display last update time
        st.write(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        st.error(f"Error fetching headers: {str(e)}")
else:
    st.error("Failed to initialize Google Sheets connection")
