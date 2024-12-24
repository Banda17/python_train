import streamlit as st
import pandas as pd
import plotly.express as px # Added import for plotly express
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

# Initialize Google Sheets client and get data first
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

        # Display statistics in a mobile-friendly grid
        st.subheader("📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Trains", len(df) if 'df' in locals() else 0)
            st.metric("Early", len(df[df['Running Status'] == 'EARLY']) if 'df' in locals() else 0)
            st.metric("On Time", len(df[df['Running Status'] == 'ON TIME']) if 'df' in locals() else 0)
        with col2:
            st.metric("Late", len(df[df['Running Status'] == 'LATE']) if 'df' in locals() else 0)
            if 'df' in locals():
                avg_predicted_delay = df['Predicted Delay'].mean()
                st.metric("Avg. Predicted Delay", f"{avg_predicted_delay:.1f} min")

        # Interactive Prediction Section
        st.subheader("🤖 Delay Predictions")

        # Create two columns for the prediction interface
        pred_col1, pred_col2 = st.columns(2)

        with pred_col1:
            selected_train = st.selectbox(
                "Select Train",
                options=df['Train Name'].unique(),
                help="Choose a train to predict delays"
            )

            selected_station = st.selectbox(
                "Select Station",
                options=df['Location'].unique(),
                help="Choose a station for prediction"
            )

        with pred_col2:
            # Get current time and WTT time for the selected train and station
            train_data = df[
                (df['Train Name'] == selected_train) & 
                (df['Location'] == selected_station)
            ]

            if not train_data.empty:
                current_delay = train_data['Time Difference'].iloc[0]
                wtt_time = train_data['WTT TIME'].iloc[0]
                actual_time = train_data['JUST TIME'].iloc[0]

                st.metric(
                    "Current Delay",
                    f"{current_delay} min",
                    delta=None
                )

                # Make prediction for this specific train
                try:
                    prediction_data = pd.DataFrame({
                        'Train Name': [selected_train],
                        'Location': [selected_station],
                        'WTT TIME': [wtt_time],
                        'JUST TIME': [actual_time]
                    })

                    predicted_delay = st.session_state.predictor.predict(prediction_data)[0]

                    st.metric(
                        "Predicted Delay",
                        f"{predicted_delay:.0f} min",
                        delta=f"{predicted_delay - float(current_delay.replace('+', ''))}",
                        delta_color="inverse"
                    )

                    # Add prediction insights
                    if abs(predicted_delay) > 15:
                        st.warning("⚠️ High delay risk detected!")
                    elif abs(predicted_delay) > 5:
                        st.info("ℹ️ Moderate delay expected")
                    else:
                        st.success("✅ Train likely to run on time")

                except Exception as e:
                    st.error(f"Could not generate prediction: {str(e)}")
            else:
                st.info("No current data available for selected train and station")

        # Display historical performance
        if not train_data.empty:
            st.subheader("📈 Historical Performance")
            historical_data = df[df['Train Name'] == selected_train]

            if not historical_data.empty:
                fig = px.line(
                    historical_data,
                    x='Location',
                    y=['Time Difference', 'Predicted Delay'],
                    title=f"Delay Trend for {selected_train}",
                    labels={
                        'Location': 'Station',
                        'value': 'Delay (minutes)',
                        'variable': 'Type'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)


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

        # Apply filters
        if status_filter != "All":
            df = df[df['Status'] == status_filter]
        if running_status_filter != "All":
            df = df[df['Running Status'] == running_status_filter]

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

        # Map visualization
        st.subheader("🗺️ Train Locations")
        display_train_map(df)

    else:
        st.error("Unable to fetch data from Google Sheets")
else:
    st.error("Failed to initialize Google Sheets connection")

st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 0.8rem;'>Railway Tracking Dashboard © 2024</p>", 
    unsafe_allow_html=True
)