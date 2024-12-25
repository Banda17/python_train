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
                # Handle empty time values
                scheduled_time = row['WTT TIME'] if pd.notna(row['WTT TIME']) else "00:00"
                actual_time = row['JUST TIME'] if pd.notna(row['JUST TIME']) else "00:00"

                # Handle delay calculation
                delay = 0
                if row['Time Difference'] != 'N/A' and row['Time Difference']:
                    try:
                        delay = int(row['Time Difference'].replace('+', ''))
                    except (ValueError, AttributeError):
                        delay = 0

                record = (
                    row['Train Name'],
                    row['Location'],
                    row['Status'],
                    row['Running Status'],
                    scheduled_time,
                    actual_time,
                    delay,
                    datetime.now().date()
                )
                records.append(record)

                # Analyze and save delay pattern
                if delay > 0:
                    self._analyze_and_save_pattern(
                        row['Train Name'],
                        row['Location'],
                        delay,
                        actual_time,
                        scheduled_time
                    )

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

    def _analyze_and_save_pattern(self, train_name, location, delay, actual_time, scheduled_time):
        """Analyze and save delay patterns"""
        try:
            # Get recent delays for this train and location
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Check for existing patterns
                    cur.execute("""
                        SELECT delay_minutes, frequency
                        FROM train_delay_patterns
                        WHERE train_name = %s AND location = %s
                        AND recorded_at >= CURRENT_TIMESTAMP - interval '7 days'
                        ORDER BY recorded_at DESC
                        """, (train_name, location))

                    recent_patterns = cur.fetchall()

                    # Calculate pattern confidence and type
                    pattern_type = "Irregular"
                    confidence = 0.5  # Default confidence
                    description = "Occasional delay detected"

                    if recent_patterns:
                        delays = [p[0] for p in recent_patterns]
                        frequencies = [p[1] for p in recent_patterns]

                        # Calculate average delay and frequency
                        avg_delay = sum(delays) / len(delays)
                        total_freq = sum(frequencies)

                        # Determine pattern type and confidence
                        if abs(delay - avg_delay) <= 5:
                            pattern_type = "Consistent"
                            confidence = min(0.9, 0.5 + (total_freq / 20))
                            description = f"Regular delay pattern of {int(avg_delay)} minutes"
                        elif delay > avg_delay + 10:
                            pattern_type = "Increasing"
                            confidence = 0.7
                            description = "Increasing delay trend detected"
                        elif delay < avg_delay - 10:
                            pattern_type = "Decreasing"
                            confidence = 0.7
                            description = "Decreasing delay trend detected"

                    # Insert or update pattern
                    cur.execute("""
                        INSERT INTO train_delay_patterns 
                        (train_name, location, delay_minutes, pattern_type, 
                         confidence, description, frequency)
                        VALUES (%s, %s, %s, %s, %s, %s, 1)
                        ON CONFLICT (train_name, location) 
                        DO UPDATE SET
                            delay_minutes = EXCLUDED.delay_minutes,
                            pattern_type = EXCLUDED.pattern_type,
                            confidence = EXCLUDED.confidence,
                            description = EXCLUDED.description,
                            frequency = train_delay_patterns.frequency + 1,
                            recorded_at = CURRENT_TIMESTAMP
                        """, (
                            train_name, location, delay, pattern_type,
                            confidence, description
                        ))

            return True
        except Exception as e:
            logger.error(f"Error analyzing pattern: {str(e)}")
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

    def get_delay_patterns(self, train_name):
        """Get delay patterns for a specific train"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                query = """
                SELECT * FROM train_delay_patterns
                WHERE train_name = %s
                AND recorded_at >= CURRENT_TIMESTAMP - interval '7 days'
                ORDER BY recorded_at DESC
                """
                return pd.read_sql_query(query, conn, params=(train_name,))
        except Exception as e:
            logger.error(f"Error retrieving patterns: {str(e)}")
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