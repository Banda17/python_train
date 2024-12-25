import streamlit as st
import pandas as pd  # Added import
from utils.notification_service import notification_service
from utils.map_utils import load_station_coordinates
import json
import uuid
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Train Alerts",
    page_icon="🔔",
    layout="wide"
)

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class='train-header'>
        <h1>Train Delay Alerts</h1>
        <p>Configure and manage your train delay notifications</p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state for user ID
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# Notification subscription section
st.subheader("📱 Push Notifications")

# Check if push notifications are supported
if st.toggle("Enable Push Notifications", key="notifications_enabled"):
    st.info("Click 'Allow' in your browser's permission prompt to enable notifications")

    # JavaScript for push notification setup
    st.markdown("""
    <script>
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        navigator.serviceWorker.register('/service-worker.js')
        .then(function(registration) {
            return registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: 'YOUR_PUBLIC_VAPID_KEY'
            });
        })
        .then(function(subscription) {
            fetch('/api/subscribe', {
                method: 'POST',
                body: JSON.stringify(subscription),
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        })
        .catch(function(error) {
            console.error('Push notification error:', error);
        });
    }
    </script>
    """, unsafe_allow_html=True)

# Alert configuration section
st.subheader("⚙️ Alert Settings")

col1, col2 = st.columns(2)

with col1:
    delay_threshold = st.number_input(
        "Delay Threshold (minutes)",
        min_value=5,
        max_value=120,
        value=15,
        step=5,
        help="Get notified when trains are delayed by this many minutes"
    )

with col2:
    alert_types = st.multiselect(
        "Alert Types",
        ["Delays", "Early Arrivals", "Status Changes", "Terminations"],
        default=["Delays"],
        help="Select the types of alerts you want to receive"
    )

# Station selection
selected_stations = st.multiselect(
    "Monitor Stations",
    ["All Stations"] + list(load_station_coordinates().keys()),
    default=["All Stations"],
    help="Select stations to monitor for delays"
)

# Save preferences
if st.button("Save Alert Preferences", type="primary"):
    # Save preferences logic here
    st.success("Alert preferences saved successfully!")

# Alert history
st.subheader("📜 Recent Alerts")

# Create sample alert history (replace with actual data later)
alert_history = [
    {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "train": "12345",
        "message": "15 minutes delay at Station ABC",
        "status": "LATE"
    }
]

# Display alert history in a table
if alert_history:
    alert_df = pd.DataFrame(alert_history)
    st.dataframe(
        alert_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "timestamp": st.column_config.TextColumn(
                "Time",
                help="Alert timestamp",
                width="small"
            ),
            "train": st.column_config.TextColumn(
                "Train",
                help="Train number",
                width="small"
            ),
            "message": st.column_config.TextColumn(
                "Alert",
                help="Alert message"
            ),
            "status": st.column_config.TextColumn(
                "Status",
                help="Train status",
                width="small"
            )
        }
    )
else:
    st.info("No recent alerts")

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 0.8rem;'>Train Delay Alerts © 2024</p>",
    unsafe_allow_html=True
)