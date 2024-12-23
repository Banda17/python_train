import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import initialize_google_sheets, get_sheet_data
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Train Performance Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
    <div class='train-header'>
        <h1>Train Performance Analytics</h1>
        <p>Comprehensive analysis of train performance metrics and trends</p>
    </div>
""", unsafe_allow_html=True)

# Initialize Google Sheets client
client = initialize_google_sheets()

if client:
    # Get data
    sheet_id = "1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4"
    df = get_sheet_data(client, sheet_id)

    if df is not None:
        # Add timestamp column for time-based analysis
        df['Timestamp'] = pd.to_datetime('today').date()

        # Metrics Overview
        st.subheader("📈 Performance Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_delay = df['Time Difference'].apply(
                lambda x: float(x.replace('+', '')) if x != 'N/A' else 0
            ).mean()
            st.metric(
                "Average Delay",
                f"{avg_delay:.1f} min",
                delta=None
            )

        with col2:
            on_time_percentage = (
                len(df[df['Running Status'] == 'ON TIME']) / len(df) * 100
            )
            st.metric(
                "On-Time Performance",
                f"{on_time_percentage:.1f}%",
                delta=None
            )

        with col3:
            total_late = len(df[df['Running Status'] == 'LATE'])
            st.metric(
                "Total Late Trains",
                total_late,
                delta=None
            )

        # Performance Distribution
        st.subheader("📊 Delay Distribution")
        delays = df['Time Difference'].apply(
            lambda x: float(x.replace('+', '')) if x != 'N/A' else 0
        )
        
        fig = px.histogram(
            delays,
            title="Distribution of Delays",
            labels={'value': 'Delay (minutes)', 'count': 'Number of Trains'},
            color_discrete_sequence=['#2c3e50']
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Station Performance
        st.subheader("🚉 Station Performance")
        station_metrics = []
        
        for station in df['Location'].unique():
            station_data = df[df['Location'] == station]
            total_trains = len(station_data)
            late_trains = len(station_data[station_data['Running Status'] == 'LATE'])
            avg_delay = station_data['Time Difference'].apply(
                lambda x: float(x.replace('+', '')) if x != 'N/A' else 0
            ).mean()
            
            station_metrics.append({
                'Station': station,
                'Total Trains': total_trains,
                'Late Trains': late_trains,
                'Average Delay': avg_delay,
                'On-Time %': ((total_trains - late_trains) / total_trains * 100)
            })

        station_df = pd.DataFrame(station_metrics)
        
        # Station comparison chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='On-Time %',
            x=station_df['Station'],
            y=station_df['On-Time %'],
            marker_color='#28a745'
        ))
        fig.add_trace(go.Bar(
            name='Average Delay',
            x=station_df['Station'],
            y=station_df['Average Delay'],
            marker_color='#dc3545',
            yaxis='y2'
        ))

        fig.update_layout(
            title='Station Performance Metrics',
            yaxis=dict(title='On-Time Percentage', ticksuffix='%'),
            yaxis2=dict(
                title='Average Delay (minutes)',
                overlaying='y',
                side='right'
            ),
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Station metrics table
        st.dataframe(
            station_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Station': st.column_config.TextColumn(
                    'Station',
                    help='Station name',
                    width='small'
                ),
                'Total Trains': st.column_config.NumberColumn(
                    'Total Trains',
                    help='Total number of trains at this station'
                ),
                'Late Trains': st.column_config.NumberColumn(
                    'Late Trains',
                    help='Number of late trains'
                ),
                'Average Delay': st.column_config.NumberColumn(
                    'Avg Delay',
                    help='Average delay in minutes',
                    format='%.1f min'
                ),
                'On-Time %': st.column_config.NumberColumn(
                    'On-Time %',
                    help='Percentage of trains on time',
                    format='%.1f%%'
                )
            }
        )

        # Train Performance Analysis
        st.subheader("🚂 Train Performance Analysis")
        train_metrics = []
        
        for train in df['Train Name'].unique():
            train_data = df[df['Train Name'] == train]
            delays = train_data['Time Difference'].apply(
                lambda x: float(x.replace('+', '')) if x != 'N/A' else 0
            )
            
            train_metrics.append({
                'Train': train,
                'Average Delay': delays.mean(),
                'Max Delay': delays.max(),
                'Min Delay': delays.min(),
                'Status Distribution': train_data['Running Status'].value_counts().to_dict()
            })

        train_df = pd.DataFrame(train_metrics)
        
        # Train delay comparison
        fig = px.scatter(
            train_df,
            x='Train',
            y='Average Delay',
            size=train_df['Max Delay'].apply(lambda x: abs(x) + 5),  # Convert to absolute value and add minimum size
            color='Average Delay',
            title='Train Delay Analysis',
            labels={
                'Train': 'Train Number',
                'Average Delay': 'Average Delay (minutes)',
                'Max Delay': 'Maximum Delay (minutes)'
            },
            color_continuous_scale='RdYlGn_r'  # Red for high delays, green for low delays
        )

        # Update layout for better readability
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=True,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        # Export functionality
        st.subheader("📥 Export Analytics")
        if st.button("Export Analytics to CSV"):
            # Prepare export data
            export_df = pd.concat([
                station_df.add_prefix('Station_'),
                train_df.add_prefix('Train_')
            ], axis=1)
            
            # Convert to CSV
            csv = export_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "train_analytics.csv",
                "text/csv",
                key='download-csv'
            )

    else:
        st.error("Unable to fetch data from Google Sheets")
else:
    st.error("Failed to initialize Google Sheets connection")

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 0.8rem;'>Train Performance Analytics Dashboard © 2024</p>",
    unsafe_allow_html=True
)