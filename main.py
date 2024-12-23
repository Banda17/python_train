import streamlit as st
import pandas as pd
from utils import (
    initialize_google_sheets,
    get_sheet_data,
    process_dataframe,
    apply_filters
)
import time

# Page configuration
st.set_page_config(
    page_title="Railway Tracking Dashboard",
    page_icon="🚂",
    layout="wide"
)

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class='train-header'>
        <h1>Railway Tracking Dashboard</h1>
        <p>Real-time train monitoring system</p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state for refresh
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Sidebar
st.sidebar.title("Dashboard Controls")

# Auto-refresh settings
auto_refresh = st.sidebar.checkbox("Enable Auto Refresh", value=True)
refresh_interval = st.sidebar.slider(
    "Refresh Interval (seconds)",
    min_value=30,
    max_value=300,
    value=60
)

# Status filter
status_filter = st.sidebar.selectbox(
    "Filter by Status",
    ["All", "TER", "HO"]
)

# Manual refresh button
if st.sidebar.button("Refresh Data"):
    st.session_state.last_refresh = time.time()

# Initialize Google Sheets client
client = initialize_google_sheets()

# Main content area
if client:
    # Check if it's time to refresh
    current_time = time.time()
    if (auto_refresh and 
        current_time - st.session_state.last_refresh > refresh_interval):
        st.session_state.last_refresh = current_time
        st.experimental_rerun()

    # Default spreadsheet ID from the service account
    sheet_id = "1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4"
    df = get_sheet_data(client, sheet_id)

    if df is not None:
        # Process the dataframe
        df = process_dataframe(df)

        if df is not None:
            # Apply filters
            filtered_df = apply_filters(df, status_filter)

            # Display last update time
            st.write(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Display the data table
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn(
                        "Status",
                        help="Train status (TER/HO)",
                        width="small"
                    ),
                    "Time Difference": st.column_config.TextColumn(
                        "Time Difference (min)",
                        help="Difference between JUST and WTT times"
                    )
                }
            )

            # Display statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Trains", len(filtered_df))
            with col2:
                st.metric("TER Count", len(filtered_df[filtered_df['Status'] == 'TER']))
            with col3:
                st.metric("HO Count", len(filtered_df[filtered_df['Status'] == 'HO']))
    else:
        st.error("Unable to fetch data from Google Sheets")
else:
    st.error("Failed to initialize Google Sheets connection")

# Footer
st.markdown("---")
st.markdown("Railway Tracking Dashboard © 2024")