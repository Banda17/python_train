import os
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainHistoryManager:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set")

    def save_current_data(self, df):
        """Save current train data to history table"""
        try:
            # Prepare data for insertion
            records = []
            for _, row in df.iterrows():
                delay = row['Time Difference'].replace('+', '') if row['Time Difference'] != 'N/A' else '0'
                record = (
                    row['Train Name'],
                    row['Location'],
                    row['Status'],
                    row['Running Status'],
                    row['WTT TIME'],
                    row['JUST TIME'],
                    int(delay),
                    datetime.now().date()
                )
                records.append(record)

            # Insert into database
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO train_history 
                        (train_name, location, status, running_status, 
                         scheduled_time, actual_time, delay_minutes, recorded_date)
                        VALUES %s
                        """,
                        records
                    )
            logger.info(f"Saved {len(records)} records to history")
            return True
        except Exception as e:
            logger.error(f"Error saving history: {str(e)}")
            return False

    def get_train_history(self, train_name, days=7):
        """Get historical data for a specific train"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                query = """
                SELECT * FROM train_history 
                WHERE train_name = %s 
                AND recorded_date >= CURRENT_DATE - interval '%s days'
                ORDER BY recorded_date DESC, actual_time DESC
                """
                return pd.read_sql_query(
                    query, 
                    conn, 
                    params=(train_name, days)
                )
        except Exception as e:
            logger.error(f"Error retrieving history: {str(e)}")
            return pd.DataFrame()

    def get_location_history(self, location, days=7):
        """Get historical data for a specific location"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                query = """
                SELECT * FROM train_history 
                WHERE location = %s 
                AND recorded_date >= CURRENT_DATE - interval '%s days'
                ORDER BY recorded_date DESC, actual_time DESC
                """
                return pd.read_sql_query(
                    query, 
                    conn, 
                    params=(location, days)
                )
        except Exception as e:
            logger.error(f"Error retrieving location history: {str(e)}")
            return pd.DataFrame()

    def get_delay_statistics(self, train_name=None, location=None, days=7):
        """Get delay statistics for analysis"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                conditions = []
                params = [days]
                
                if train_name:
                    conditions.append("train_name = %s")
                    params.append(train_name)
                if location:
                    conditions.append("location = %s")
                    params.append(location)
                
                where_clause = " AND ".join(
                    ["recorded_date >= CURRENT_DATE - interval '%s days'"] + 
                    conditions
                )
                
                query = f"""
                SELECT 
                    recorded_date,
                    AVG(delay_minutes) as avg_delay,
                    MAX(delay_minutes) as max_delay,
                    MIN(delay_minutes) as min_delay,
                    COUNT(*) as total_records
                FROM train_history 
                WHERE {where_clause}
                GROUP BY recorded_date
                ORDER BY recorded_date DESC
                """
                
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            logger.error(f"Error retrieving statistics: {str(e)}")
            return pd.DataFrame()

    def cleanup_old_records(self, days_to_keep=30):
        """Remove records older than specified days"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM train_history 
                        WHERE recorded_date < CURRENT_DATE - interval '%s days'
                        """,
                        (days_to_keep,)
                    )
            logger.info("Cleaned up old records")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up records: {str(e)}")
            return False
