import json
import logging
from pywebpush import webpush, WebPushException
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class NotificationService:
    def __init__(self):
        """Initialize notification service with VAPID keys"""
        self.vapid_private_key = os.getenv('VAPID_PRIVATE_KEY')
        self.vapid_public_key = os.getenv('VAPID_PUBLIC_KEY')
        self.vapid_claims = {
            "sub": "mailto:railway@example.com"
        }
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    def add_subscription(self, user_id: str, subscription_info: Dict[str, Any]) -> None:
        """Store a new push subscription for a user"""
        try:
            self.subscriptions[user_id] = subscription_info
            logger.info(f"Added subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding subscription: {str(e)}")
            raise

    def remove_subscription(self, user_id: str) -> None:
        """Remove a user's push subscription"""
        try:
            if user_id in self.subscriptions:
                del self.subscriptions[user_id]
                logger.info(f"Removed subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing subscription: {str(e)}")
            raise

    def send_notification(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send a push notification to a specific user"""
        try:
            if user_id not in self.subscriptions:
                logger.warning(f"No subscription found for user {user_id}")
                return False

            subscription_info = self.subscriptions[user_id]
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(message),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            logger.info(f"Notification sent to user {user_id}")
            return True

        except WebPushException as e:
            logger.error(f"WebPush error: {str(e)}")
            if "410" in str(e):  # Subscription expired
                self.remove_subscription(user_id)
            return False
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    def broadcast_notification(self, message: Dict[str, Any]) -> List[str]:
        """Send a notification to all subscribed users"""
        failed_users = []
        for user_id in self.subscriptions.keys():
            if not self.send_notification(user_id, message):
                failed_users.append(user_id)
        return failed_users

    def create_delay_notification(
        self,
        train_name: str,
        location: str,
        delay: int,
        status: str
    ) -> Dict[str, Any]:
        """Create a formatted delay notification message"""
        return {
            "title": f"Train Delay Alert - {train_name}",
            "body": f"Train {train_name} is {delay} minutes {status} at {location}",
            "icon": "/icon.png",
            "badge": "/badge.png",
            "data": {
                "train": train_name,
                "location": location,
                "delay": delay,
                "status": status,
                "timestamp": str(pd.Timestamp.now())
            }
        }

# Initialize global notification service
notification_service = NotificationService()
