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
    layout="wide",
    initial_sidebar_state="collapsed"  # Better for mobile
)

# Initialize ML predictor in session state
if 'predictor' not in st.session_state:
    st.session_state.predictor = TrainDelayPredictor()

# Initialize session states
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

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

# Control Panel
st.markdown("<div class='control-panel'>", unsafe_allow_html=True)

# Simple refresh button
if st.button("Refresh Now", use_container_width=True):
    st.session_state.last_refresh = time.time()

# Status filters
status_filter = st.selectbox(
    "Filter by Status",
    ["All", "TER", "HO"]
)

running_status_filter = st.selectbox(
    "Filter by Running Status",
    ["All", "EARLY", "ON TIME", "LATE"],
    index=3  # Default to "LATE"
)

# ML Training controls
with st.expander("🤖 ML Model Control", expanded=False):
    if st.button("Train Model", use_container_width=True):
        with st.spinner("Training ML model..."):
            try:
                os.makedirs('models', exist_ok=True)
                st.session_state.predictor.train(st.session_state.get('current_data'))
                st.success("Model trained successfully!")
            except Exception as e:
                st.error(f"Error training model: {str(e)}")

    if st.button("Load Saved Model", use_container_width=True):
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
    # Check if it's time to refresh (every 60 seconds)
    current_time = time.time()
    if current_time - st.session_state.last_refresh >= 60:
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

        # Display statistics in a mobile-friendly grid
        st.subheader("📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Trains", len(df))
            st.metric("Early", len(df[df['Running Status'] == 'EARLY']))
            st.metric("On Time", len(df[df['Running Status'] == 'ON TIME']))
        with col2:
            st.metric("Late", len(df[df['Running Status'] == 'LATE']))
            avg_predicted_delay = df['Predicted Delay'].mean()
            st.metric("Avg. Predicted Delay", f"{avg_predicted_delay:.1f} min")

        # Data table with mobile-optimized columns
        st.subheader("🚂 Train Status")
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Train Name": st.column_config.TextColumn(
                    "Train",
                    help="Train number and name",
                    width="small"
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
                    "Time",
                    help="Actual time",
                    width="small"
                ),
                "WTT TIME": st.column_config.TextColumn(
                    "Scheduled",
                    help="Scheduled time",
                    width="small"
                ),
                "Time Difference": st.column_config.TextColumn(
                    "Delay",
                    help="Current delay in minutes"
                ),
                "Predicted Delay": st.column_config.NumberColumn(
                    "Predicted",
                    help="ML-predicted delay",
                    format="%d"
                ),
                "Running Status": st.column_config.TextColumn(
                    "Status",
                    help="Early/On Time/Late",
                    width="small"
                )
            }
        )

        # Map visualization
        st.subheader("🗺️ Train Locations")
        display_train_map(df)

    else:
        st.error("Unable to fetch data from Google Sheets")
else:
    st.error("Failed to initialize Google Sheets connection")

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 0.8rem;'>Railway Tracking Dashboard © 2024</p>", 
    unsafe_allow_html=True
)