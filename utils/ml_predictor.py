import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainDelayPredictor:
    def __init__(self):
        """Initialize the delay predictor with necessary encoders and model"""
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.station_encoder = LabelEncoder()
        self.train_encoder = LabelEncoder()
        self.is_trained = False

    def _extract_time_features(self, time_str: str) -> Dict[str, int]:
        """Extract hour and minute from time string"""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            return {
                'hour': time_obj.hour,
                'minute': time_obj.minute,
            }
        except:
            return {'hour': -1, 'minute': -1}

    def _process_time_difference(self, value: str) -> float:
        """Process time difference string to numeric value"""
        try:
            if pd.isna(value) or value == 'N/A':
                return 0.0
            # Remove '+' prefix if present and convert to float
            return float(str(value).replace('+', ''))
        except Exception as e:
            logger.warning(f"Error processing time difference '{value}': {str(e)}")
            return 0.0

    def _preprocess_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess the data for training/prediction"""
        try:
            # Create a copy to avoid modifying original dataframe
            df = df.copy()

            # Handle missing values
            df['Location'] = df['Location'].fillna('UNKNOWN')
            df['Train Name'] = df['Train Name'].fillna('UNKNOWN')
            df['WTT TIME'] = df['WTT TIME'].fillna('00:00')
            df['JUST TIME'] = df['JUST TIME'].fillna('00:00')

            # Encode categorical variables
            df['station_encoded'] = self.station_encoder.fit_transform(df['Location'])
            df['train_encoded'] = self.train_encoder.fit_transform(df['Train Name'])

            # Extract time features from WTT and JUST times
            wtt_times = df['WTT TIME'].apply(self._extract_time_features).apply(pd.Series)
            just_times = df['JUST TIME'].apply(self._extract_time_features).apply(pd.Series)

            # Create feature matrix
            X = pd.concat([
                df[['station_encoded', 'train_encoded']],
                wtt_times.add_prefix('wtt_'),
                just_times.add_prefix('just_')
            ], axis=1)

            # Process time differences for y
            y = df['Time Difference'].apply(self._process_time_difference)

            return X.to_numpy(), y.to_numpy()

        except Exception as e:
            logger.error(f"Error preprocessing data: {str(e)}")
            raise

    def train(self, train_data: pd.DataFrame) -> None:
        """Train the model using historical data"""
        try:
            logger.info("Starting model training...")

            # Preprocess data
            X, y = self._preprocess_data(train_data)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Train model
            self.model.fit(X_train, y_train)

            # Evaluate model
            train_score = self.model.score(X_train, y_train)
            test_score = self.model.score(X_test, y_test)

            logger.info(f"Model trained successfully. Train R2: {train_score:.3f}, Test R2: {test_score:.3f}")
            self.is_trained = True

            # Save the model
            self.save_model()

        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise

    def predict(self, new_data: pd.DataFrame) -> List[int]:
        """Predict delays for new data"""
        try:
            if not self.is_trained:
                self.load_model()

            X, _ = self._preprocess_data(new_data)
            predictions = self.model.predict(X)

            # Round predictions to nearest integer
            return np.round(predictions).astype(int).tolist()

        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            logger.debug(f"Input data shape: {new_data.shape if hasattr(new_data, 'shape') else 'unknown'}")
            return [0] * len(new_data)

    def save_model(self, path: str = 'models/delay_predictor.joblib') -> None:
        """Save the trained model and encoders"""
        try:
            model_data = {
                'model': self.model,
                'station_encoder': self.station_encoder,
                'train_encoder': self.train_encoder,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, path)
            logger.info(f"Model saved successfully to {path}")
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")

    def load_model(self, path: str = 'models/delay_predictor.joblib') -> None:
        """Load a trained model and encoders"""
        try:
            model_data = joblib.load(path)
            self.model = model_data['model']
            self.station_encoder = model_data['station_encoder']
            self.train_encoder = model_data['train_encoder']
            self.is_trained = model_data['is_trained']
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.is_trained = False