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
from datetime import datetime
from utils.history_manager import TrainHistoryManager

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

# Initialize history manager in session state
if 'history_manager' not in st.session_state:
    st.session_state.history_manager = TrainHistoryManager()

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
        
        # Save current data to history
        st.session_state.history_manager.save_current_data(df)

        # Get delay predictions
        try:
            predictions = st.session_state.predictor.predict(df)
            df['Predicted Delay'] = predictions
        except Exception as e:
            st.warning(f"Could not generate predictions: {str(e)}")
            df['Predicted Delay'] = 0

        # Display last update time
        st.write(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

        # Create a filtered copy of the dataframe
        filtered_df = df.copy()

        # Apply filters
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Status'] == status_filter]
        if running_status_filter != "All":
            filtered_df = filtered_df[filtered_df['Running Status'] == running_status_filter]

        # Create a styled dataframe using custom colors
        def style_row(row):
            styles = [''] * len(row)  # Start with no colors for all cells

            # Get column indexes
            status_idx = filtered_df.columns.get_loc('Status')
            running_idx = filtered_df.columns.get_loc('Running Status')
            delay_idx = filtered_df.columns.get_loc('Time Difference')

            # Style Status column
            if row['Status'] == 'TER':
                styles[status_idx] = 'background-color: #E8F5E9; color: #1b1b1b'  # Lighter Green
            elif row['Status'] == 'HO':
                styles[status_idx] = 'background-color: #FFEBEE; color: #1b1b1b'  # Lighter Red

            # Style Running Status column
            if row['Running Status'] == 'EARLY':
                styles[running_idx] = 'background-color: #E8F5E9; color: #1b1b1b'  # Lighter Green
            elif row['Running Status'] == 'ON TIME':
                styles[running_idx] = 'background-color: #E3F2FD; color: #1b1b1b'  # Lighter Blue
            elif row['Running Status'] == 'LATE':
                styles[running_idx] = 'background-color: #ffcdd2; color: #1b1b1b'   # Lighter Red
                # Also style the delay column for late trains
                styles[delay_idx] = 'background-color: #DA0037; color: #ffffff' # Lighter Red

            return styles

        # Apply styles using a single row-wise function
        styled_df = filtered_df.style.apply(style_row, axis=1)

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

        # Train History Section - Make it more prominent
        st.markdown("---")
        st.subheader("📈 Train History Analysis")
        st.markdown("*View detailed performance history and statistics for selected train*")

        # Get historical data for the selected train
        hist_data = st.session_state.history_manager.get_train_history(selected_train)

        if not hist_data.empty:
            # Create historical delay trend
            fig = px.line(
                hist_data,
                x='recorded_date',
                y='delay_minutes',
                title=f'7-Day Delay History for {selected_train}',
                labels={
                    'recorded_date': 'Date',
                    'delay_minutes': 'Delay (minutes)'
                }
            )
            fig.update_layout(
                height=400,
                showlegend=True,
                xaxis_title="Date",
                yaxis_title="Delay (minutes)",
                plot_bgcolor='rgba(255,255,255,0.9)',
                paper_bgcolor='rgba(255,255,255,0.9)',
            )

            # Add current delay point
            if 'current_delay' in locals():
                fig.add_scatter(
                    x=[datetime.now().date()],
                    y=[float(current_delay.replace('+', ''))],
                    mode='markers',
                    name='Current Delay',
                    marker=dict(size=12, color='red')
                )

            st.plotly_chart(fig, use_container_width=True)

            # Show delay statistics
            stats = st.session_state.history_manager.get_delay_statistics(
                train_name=selected_train
            )

            if not stats.empty:
                st.subheader("📊 Historical Statistics")
                col1, col2, col3 = st.columns(3)

                with col1:
                    avg_delay = stats['avg_delay'].mean()
                    st.metric(
                        "Average Delay",
                        f"{avg_delay:.1f} min",
                        delta=float(current_delay.replace('+', '')) - avg_delay if 'current_delay' in locals() else None,
                        delta_color="inverse"
                    )

                with col2:
                    max_delay = stats['max_delay'].max()
                    st.metric("Maximum Delay", f"{max_delay:.0f} min")

                with col3:
                    min_delay = stats['min_delay'].min()
                    st.metric("Minimum Delay", f"{min_delay:.0f} min")

                # Add a line chart for daily average delays
                fig_avg = px.line(
                    stats,
                    x='recorded_date',
                    y='avg_delay',
                    title='Daily Average Delays',
                    labels={
                        'recorded_date': 'Date',
                        'avg_delay': 'Average Delay (minutes)'
                    }
                )
                fig_avg.update_layout(
                    height=300,
                    showlegend=False,
                    xaxis_title="Date",
                    yaxis_title="Average Delay (minutes)",
                    plot_bgcolor='rgba(255,255,255,0.9)',
                    paper_bgcolor='rgba(255,255,255,0.9)',
                )
                st.plotly_chart(fig_avg, use_container_width=True)
        else:
            st.info("No historical data available for this train yet. Data will appear as it's collected over time.")


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