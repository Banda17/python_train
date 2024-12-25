import streamlit as st
import pandas as pd
import plotly.express as px
from utils import initialize_google_sheets, get_sheet_data
from utils.history_manager import TrainHistoryManager
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Train History Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class='train-header'>
        <h1>Train History Analysis</h1>
        <p>Comprehensive historical data and performance analytics</p>
    </div>
""", unsafe_allow_html=True)

# Initialize history manager
if 'history_manager' not in st.session_state:
    st.session_state.history_manager = TrainHistoryManager()

# Get data from Google Sheets for train selection
client = initialize_google_sheets()
if client:
    sheet_id = "1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4"
    current_data = get_sheet_data(client, sheet_id)

    if current_data is not None:
        # Train selection
        st.subheader("🚂 Select Train")
        selected_train = st.selectbox(
            "Choose a train to view its history",
            options=current_data['Train Name'].unique(),
            help="Select a train to analyze its historical performance"
        )

        # Get historical data and patterns
        hist_data = st.session_state.history_manager.get_train_history(selected_train)
        patterns_data = st.session_state.history_manager.get_delay_patterns(selected_train)

        if not hist_data.empty:
            # Overview metrics
            st.subheader("📊 Performance Overview")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                avg_delay = hist_data['delay_minutes'].mean()
                st.metric(
                    "Average Delay",
                    f"{avg_delay:.1f} min",
                    delta=None
                )

            with col2:
                max_delay = hist_data['delay_minutes'].max()
                st.metric(
                    "Maximum Delay",
                    f"{max_delay:.0f} min",
                    delta=None
                )

            with col3:
                min_delay = hist_data['delay_minutes'].min()
                st.metric(
                    "Minimum Delay",
                    f"{min_delay:.0f} min",
                    delta=None
                )

            with col4:
                on_time_count = len(hist_data[hist_data['delay_minutes'] <= 5])
                on_time_percentage = (on_time_count / len(hist_data)) * 100
                st.metric(
                    "On-Time Performance",
                    f"{on_time_percentage:.1f}%",
                    delta=None
                )

            # Delay Pattern Analysis
            st.subheader("🔍 Delay Pattern Analysis")
            if not patterns_data.empty:
                # Create pattern visualization
                fig_pattern = go.Figure()

                # Add scatter plot for delay patterns
                fig_pattern.add_trace(go.Scatter(
                    x=patterns_data['recorded_at'],
                    y=patterns_data['delay_minutes'],
                    mode='markers+lines',
                    name='Delay Pattern',
                    marker=dict(
                        size=10,
                        color=patterns_data['confidence'],
                        colorscale='RdYlGn_r',
                        showscale=True
                    )
                ))

                fig_pattern.update_layout(
                    title=f'Delay Patterns Over Time for {selected_train}',
                    xaxis_title="Date",
                    yaxis_title="Delay (minutes)",
                    height=400,
                    showlegend=True,
                    plot_bgcolor='rgba(255,255,255,0.9)',
                    paper_bgcolor='rgba(255,255,255,0.9)'
                )

                st.plotly_chart(fig_pattern, use_container_width=True)

                # Pattern details table
                st.markdown("### 📋 Identified Patterns")
                pattern_display = patterns_data[['location', 'pattern_type', 'delay_minutes', 'confidence', 'description', 'recorded_at']]
                pattern_display.columns = ['Station', 'Pattern Type', 'Delay (min)', 'Confidence', 'Description', 'Recorded At']

                st.dataframe(
                    pattern_display.sort_values('Recorded At', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Station": st.column_config.TextColumn(
                            "Station",
                            help="Location where pattern was detected",
                            width="small"
                        ),
                        "Pattern Type": st.column_config.TextColumn(
                            "Type",
                            help="Type of delay pattern",
                            width="small"
                        ),
                        "Delay (min)": st.column_config.NumberColumn(
                            "Delay",
                            help="Delay in minutes",
                            format="%.0f min"
                        ),
                        "Confidence": st.column_config.ProgressColumn(
                            "Confidence",
                            help="Pattern confidence score",
                            format="%.0f%%",
                            min_value=0,
                            max_value=100
                        ),
                        "Description": st.column_config.TextColumn(
                            "Description",
                            help="Pattern description",
                            width="medium"
                        ),
                        "Recorded At": st.column_config.DatetimeColumn(
                            "Recorded",
                            help="When pattern was recorded",
                            format="D MMM YYYY, HH:mm"
                        )
                    }
                )
            else:
                st.info("No delay patterns have been detected yet. Patterns will appear as they are identified.")

            # Historical delay trend
            st.subheader("📈 Delay Trend Analysis")
            fig_trend = px.line(
                hist_data,
                x='recorded_date',
                y='delay_minutes',
                title=f'7-Day Delay History for {selected_train}',
                labels={
                    'recorded_date': 'Date',
                    'delay_minutes': 'Delay (minutes)'
                }
            )
            fig_trend.update_layout(
                height=400,
                showlegend=True,
                xaxis_title="Date",
                yaxis_title="Delay (minutes)",
                plot_bgcolor='rgba(255,255,255,0.9)',
                paper_bgcolor='rgba(255,255,255,0.9)'
            )
            st.plotly_chart(fig_trend, use_container_width=True)

            # Station-wise performance
            st.subheader("🚉 Station Performance")
            station_stats = hist_data.groupby('location').agg({
                'delay_minutes': ['mean', 'max', 'min', 'count']
            }).reset_index()
            station_stats.columns = ['Station', 'Avg Delay', 'Max Delay', 'Min Delay', 'Total Records']

            # Station performance chart
            fig_station = px.bar(
                station_stats,
                x='Station',
                y='Avg Delay',
                title=f'Average Delay by Station for {selected_train}',
                color='Avg Delay',
                color_continuous_scale='RdYlGn_r'
            )
            fig_station.update_layout(
                height=400,
                showlegend=False,
                xaxis_title="Station",
                yaxis_title="Average Delay (minutes)",
                plot_bgcolor='rgba(255,255,255,0.9)',
                paper_bgcolor='rgba(255,255,255,0.9)'
            )
            st.plotly_chart(fig_station, use_container_width=True)

            # Historical data table
            st.subheader("📋 Detailed History")
            st.dataframe(
                hist_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "train_name": st.column_config.TextColumn(
                        "Train",
                        help="Train number",
                        width="small"
                    ),
                    "location": st.column_config.TextColumn(
                        "Station",
                        help="Station name",
                        width="small"
                    ),
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="Train status",
                        width="small"
                    ),
                    "running_status": st.column_config.TextColumn(
                        "Running Status",
                        help="Current running status",
                        width="small"
                    ),
                    "delay_minutes": st.column_config.NumberColumn(
                        "Delay",
                        help="Delay in minutes",
                        format="%.0f min"
                    ),
                    "recorded_date": st.column_config.DateColumn(
                        "Date",
                        help="Record date",
                        width="small"
                    )
                }
            )

            # Download options
            st.subheader("📥 Download Data")
            col1, col2 = st.columns(2)

            with col1:
                csv = hist_data.to_csv(index=False)
                st.download_button(
                    "Download History Data",
                    csv,
                    f"{selected_train}_history.csv",
                    "text/csv",
                    key='download-history'
                )

            with col2:
                if not patterns_data.empty:
                    patterns_csv = patterns_data.to_csv(index=False)
                    st.download_button(
                        "Download Pattern Analysis",
                        patterns_csv,
                        f"{selected_train}_patterns.csv",
                        "text/csv",
                        key='download-patterns'
                    )
        else:
            st.info("No historical data available for this train yet. Data will appear as it's collected over time.")
    else:
        st.error("Unable to fetch current train data")
else:
    st.error("Failed to initialize Google Sheets connection")

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 0.8rem;'>Train History Analysis © 2024</p>",
    unsafe_allow_html=True
)