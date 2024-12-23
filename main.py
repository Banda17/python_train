import streamlit as st
import pandas as pd
from utils import (
    initialize_google_sheets,
    get_sheet_data,
    apply_filters,
    TrainDelayPredictor
)
from utils.map_utils import display_train_map
import time
import os

# Page configuration
st.set_page_config(
    page_title="Railway Tracking Dashboard",
    page_icon="🚂",
    layout="wide"
)

# Initialize ML predictor in session state
if 'predictor' not in st.session_state:
    st.session_state.predictor = TrainDelayPredictor()

# Initialize color scheme in session state
if 'color_scheme' not in st.session_state:
    st.session_state.color_scheme = {
        'TER': '#28a745',
        'HO': '#dc3545',
        'EARLY': '#28a745',
        'ON_TIME': '#17a2b8',
        'LATE': '#dc3545'
    }

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class='train-header'>
        <h1>Railway Tracking Dashboard</h1>
        <p>Real-time train monitoring system with ML-powered delay predictions</p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state for refresh
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Control Panel
st.markdown("<div class='control-panel'>", unsafe_allow_html=True)

# Main controls
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    auto_refresh = st.checkbox("Enable Auto Refresh", value=True)
    if st.button("Refresh Data"):
        st.session_state.last_refresh = time.time()

with col2:
    refresh_interval = st.slider(
        "Refresh Interval (seconds)",
        min_value=30,
        max_value=300,
        value=60
    )

with col3:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "TER", "HO"]
    )

with col4:
    running_status_filter = st.selectbox(
        "Filter by Running Status",
        ["All", "EARLY", "ON TIME", "LATE"],
        index=3  # Set default to "LATE" (index 3 in the list)
    )

# ML Training section
with st.expander("🤖 ML Model Control", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Train Model"):
            with st.spinner("Training ML model..."):
                try:
                    # Create models directory if it doesn't exist
                    os.makedirs('models', exist_ok=True)
                    # Train model with current data
                    st.session_state.predictor.train(st.session_state.get('current_data'))
                    st.success("Model trained successfully!")
                except Exception as e:
                    st.error(f"Error training model: {str(e)}")

    with col2:
        if st.button("Load Saved Model"):
            with st.spinner("Loading saved model..."):
                try:
                    st.session_state.predictor.load_model()
                    st.success("Model loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading model: {str(e)}")

st.markdown("</div>", unsafe_allow_html=True)

# Initialize Google Sheets client
client = initialize_google_sheets()

if client:
    # Check if it's time to refresh
    current_time = time.time()
    if auto_refresh and current_time - st.session_state.last_refresh > refresh_interval:
        st.session_state.last_refresh = current_time
        st.rerun()

    # Default spreadsheet ID
    sheet_id = "1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4"
    df = get_sheet_data(client, sheet_id)

    if df is not None:
        # Store current data in session state for ML training
        st.session_state.current_data = df.copy()

        # Get delay predictions
        try:
            predictions = st.session_state.predictor.predict(df)
            df['Predicted Delay'] = predictions
        except Exception as e:
            st.warning(f"Could not generate predictions: {str(e)}")
            df['Predicted Delay'] = 0

        # Apply filters
        if status_filter != "All":
            df = df[df['Status'] == status_filter]
        if running_status_filter != "All":
            df = df[df['Running Status'] == running_status_filter]

        # Display last update time
        st.write(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Create a styled dataframe using custom colors
        def style_status(val):
            if val == 'TER':
                return f'background-color: {st.session_state.color_scheme["TER"]}; color: white'
            elif val == 'HO':
                return f'background-color: {st.session_state.color_scheme["HO"]}; color: white'
            return ''

        def style_running_status(val):
            if val == 'EARLY':
                return f'background-color: {st.session_state.color_scheme["EARLY"]}; color: white'
            elif val == 'ON TIME':
                return f'background-color: {st.session_state.color_scheme["ON_TIME"]}; color: white'
            elif val == 'LATE':
                return f'background-color: {st.session_state.color_scheme["LATE"]}; color: white'
            return ''

        styled_df = df.style\
            .map(style_status, subset=['Status'])\
            .map(style_running_status, subset=['Running Status'])

        # Display the styled dataframe
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Train Name": st.column_config.TextColumn(
                    "Train Name",
                    help="Train number and name",
                    width="medium"
                ),
                "Location": st.column_config.TextColumn(
                    "Location",
                    help="Current station",
                    width="small"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Train status (TER/HO)",
                    width="small"
                ),
                "JUST TIME": st.column_config.TextColumn(
                    "JUST Time",
                    help="Actual time",
                    width="small"
                ),
                "WTT TIME": st.column_config.TextColumn(
                    "WTT Time",
                    help="Scheduled time",
                    width="small"
                ),
                "Time Difference": st.column_config.TextColumn(
                    "Current Delay (min)",
                    help="Current difference between JUST and WTT times"
                ),
                "Predicted Delay": st.column_config.NumberColumn(
                    "Predicted Delay (min)",
                    help="ML-predicted delay in minutes",
                    format="%d"
                ),
                "Running Status": st.column_config.TextColumn(
                    "Running Status",
                    help="Early/On Time/Late status",
                    width="small"
                )
            }
        )

        # Display statistics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Trains", len(df))
        with col2:
            st.metric("Early", len(df[df['Running Status'] == 'EARLY']))
        with col3:
            st.metric("On Time", len(df[df['Running Status'] == 'ON TIME']))
        with col4:
            st.metric("Late", len(df[df['Running Status'] == 'LATE']))
        with col5:
            avg_predicted_delay = df['Predicted Delay'].mean()
            st.metric("Avg. Predicted Delay", f"{avg_predicted_delay:.1f} min")

        # Add map visualization
        st.markdown("---")
        display_train_map(df)

    else:
        st.error("Unable to fetch data from Google Sheets")
else:
    st.error("Failed to initialize Google Sheets connection")

# Footer
st.markdown("---")
st.markdown("Railway Tracking Dashboard © 2024")