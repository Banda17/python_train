import streamlit as st
import logging
from typing import Dict, List
import json
from datetime import datetime
from twilio.rest import Client
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        """Initialize notification manager with default settings"""
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        if 'notification_settings' not in st.session_state:
            st.session_state.notification_settings = {
                'delay_threshold': 15,  # minutes
                'notify_early': True,
                'notify_late': True,
                'notify_status_change': True,
                'sms_enabled': False,
                'phone_number': ''  # User's phone number to receive notifications
            }

        # Initialize Twilio client if credentials are available
        self.twilio_client = None
        try:
            account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
            auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
            self.twilio_phone = os.environ.get('TWILIO_PHONE_NUMBER')

            if account_sid and auth_token and self.twilio_phone:
                self.twilio_client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Twilio client: {str(e)}")

    def send_sms(self, message: str, phone_number: str) -> bool:
        """Send SMS notification using Twilio"""
        try:
            if not self.twilio_client:
                logger.warning("Twilio client not initialized")
                return False

            if not phone_number:
                logger.warning("No phone number provided for SMS")
                return False

            message = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=phone_number
            )
            logger.info(f"SMS sent successfully: {message.sid}")
            return True

        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

    def add_notification(self, train_name: str, message: str, severity: str = 'info'):
        """Add a new notification and send SMS if enabled"""
        try:
            notification = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'train_name': train_name,
                'message': message,
                'severity': severity,
                'read': False
            }
            st.session_state.notifications.insert(0, notification)

            # Send SMS for important notifications if enabled
            if (st.session_state.notification_settings['sms_enabled'] and 
                severity in ['warning', 'error'] and
                st.session_state.notification_settings['phone_number']):
                self.send_sms(
                    message,
                    st.session_state.notification_settings['phone_number']
                )

            logger.info(f"Added notification for train {train_name}: {message}")

            # Keep only last 50 notifications
            if len(st.session_state.notifications) > 50:
                st.session_state.notifications = st.session_state.notifications[:50]

        except Exception as e:
            logger.error(f"Error adding notification: {str(e)}")

    def check_delays(self, df) -> List[Dict]:
        """Check for delays that exceed the threshold"""
        try:
            threshold = st.session_state.notification_settings['delay_threshold']
            new_alerts = []

            for _, row in df.iterrows():
                try:
                    time_diff = row['Time Difference']
                    if time_diff == 'N/A':
                        continue

                    delay = int(time_diff.replace('+', ''))
                    train_name = row['Train Name']
                    status = row['Running Status']
                    location = row['Location']

                    # Check for significant delays
                    if abs(delay) >= threshold:
                        if delay > 0 and st.session_state.notification_settings['notify_late']:
                            message = f"Train {train_name} is {delay} minutes late at {location}"
                            self.add_notification(train_name, message, 'warning')
                            new_alerts.append({'train': train_name, 'message': message})
                        elif delay < 0 and st.session_state.notification_settings['notify_early']:
                            message = f"Train {train_name} is {abs(delay)} minutes early at {location}"
                            self.add_notification(train_name, message, 'info')
                            new_alerts.append({'train': train_name, 'message': message})

                    # Check for status changes
                    if st.session_state.notification_settings['notify_status_change']:
                        if status != row.get('previous_status', status):
                            message = f"Train {train_name} status changed to {status} at {location}"
                            self.add_notification(train_name, message, 'info')
                            new_alerts.append({'train': train_name, 'message': message})

                except Exception as e:
                    logger.warning(f"Error processing delay check for train: {str(e)}")
                    continue

            return new_alerts

        except Exception as e:
            logger.error(f"Error checking delays: {str(e)}")
            return []

    def display_notifications(self):
        """Display notifications in the sidebar"""
        try:
            st.sidebar.title("🔔 Notifications")

            # Settings expander
            with st.sidebar.expander("⚙️ Notification Settings"):
                st.session_state.notification_settings['delay_threshold'] = st.slider(
                    "Delay Threshold (minutes)",
                    min_value=5,
                    max_value=60,
                    value=st.session_state.notification_settings['delay_threshold']
                )

                # SMS notification settings
                st.session_state.notification_settings['sms_enabled'] = st.checkbox(
                    "Enable SMS Notifications",
                    value=st.session_state.notification_settings['sms_enabled']
                )

                if st.session_state.notification_settings['sms_enabled']:
                    phone = st.text_input(
                        "Phone Number (E.164 format)",
                        value=st.session_state.notification_settings['phone_number'],
                        help="Enter your phone number in E.164 format (e.g., +1234567890)"
                    )
                    if phone != st.session_state.notification_settings['phone_number']:
                        st.session_state.notification_settings['phone_number'] = phone
                        if phone:
                            # Send test message
                            if self.send_sms("Test notification from Railway Tracking System", phone):
                                st.success("Test message sent successfully!")
                            else:
                                st.error("Failed to send test message. Please check your phone number.")

                st.session_state.notification_settings['notify_late'] = st.checkbox(
                    "Notify Late Trains",
                    value=st.session_state.notification_settings['notify_late']
                )
                st.session_state.notification_settings['notify_early'] = st.checkbox(
                    "Notify Early Trains",
                    value=st.session_state.notification_settings['notify_early']
                )
                st.session_state.notification_settings['notify_status_change'] = st.checkbox(
                    "Notify Status Changes",
                    value=st.session_state.notification_settings['notify_status_change']
                )

            # Display notifications
            if not st.session_state.notifications:
                st.sidebar.info("No notifications yet")
            else:
                for idx, notif in enumerate(st.session_state.notifications):
                    with st.sidebar.expander(
                        f"🔔 {notif['train_name']} - {notif['timestamp']}",
                        expanded=not notif['read']
                    ):
                        st.write(notif['message'])
                        if st.button("Mark as Read", key=f"read_{idx}"):
                            notif['read'] = True

                if st.sidebar.button("Clear All"):
                    st.session_state.notifications = []

        except Exception as e:
            logger.error(f"Error displaying notifications: {str(e)}")
            st.sidebar.error("Error displaying notifications")