import streamlit as st
import json
import pandas as pd
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_wtt_json(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate the WTT JSON structure"""
    try:
        # Check if it's a dictionary
        if not isinstance(data, dict):
            return False, "Invalid JSON structure: Root must be a dictionary"
        
        # Check each station
        for station, station_data in data.items():
            # Validate station name
            if not isinstance(station, str):
                return False, f"Invalid station name: {station}"
            
            # Check Dep structure
            if not isinstance(station_data, dict):
                return False, f"Invalid structure for station {station}"
            if 'Dep' not in station_data:
                return False, f"Missing 'Dep' key for station {station}"
            
            dep_data = station_data['Dep']
            if not isinstance(dep_data, dict):
                return False, f"Invalid 'Dep' structure for station {station}"
            
            # Check times structure
            if 'times' not in dep_data:
                return False, f"Missing 'times' key for station {station}"
            
            times_data = dep_data['times']
            if not isinstance(times_data, dict):
                return False, f"Invalid 'times' structure for station {station}"
            
            # Validate time format
            for train_no, time in times_data.items():
                if not isinstance(train_no, str):
                    return False, f"Invalid train number format for {train_no}"
                if time and not isinstance(time, str):
                    return False, f"Invalid time format for train {train_no}"
                if time:
                    try:
                        pd.to_datetime(time, format='%H:%M')
                    except ValueError:
                        return False, f"Invalid time format for train {train_no}: {time}"
        
        return True, "JSON structure is valid"
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False, f"Validation error: {str(e)}"

# Page configuration
st.set_page_config(
    page_title="WTT Upload",
    page_icon="📤",
    layout="wide"
)

st.title("Working Time Table (WTT) Uploader")
st.write("Upload and validate your WTT JSON file")

# File uploader
uploaded_file = st.file_uploader("Choose a JSON file", type=['json'])

if uploaded_file is not None:
    try:
        # Read and parse JSON
        content = uploaded_file.read()
        data = json.loads(content)
        
        # Validate JSON structure
        is_valid, message = validate_wtt_json(data)
        
        if is_valid:
            st.success("✅ File validation successful!")
            
            # Enable save button only if validation passes
            if st.button("Save WTT Data"):
                try:
                    with open('bhanu.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    st.success("🎉 WTT data saved successfully!")
                    logger.info("WTT data saved to bhanu.json")
                except Exception as e:
                    st.error(f"Error saving file: {str(e)}")
                    logger.error(f"Error saving WTT data: {str(e)}")
        else:
            st.error(f"❌ Validation failed: {message}")
            logger.warning(f"WTT validation failed: {message}")
        
        # Display JSON preview
        st.subheader("File Preview")
        st.json(data)
        
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON file: {str(e)}")
        logger.error(f"JSON decode error: {str(e)}")
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        logger.error(f"File processing error: {str(e)}")
else:
    st.info("👆 Upload a JSON file to get started")

# Add some helpful information
st.markdown("""
### Expected JSON Structure
```json
{
  "STATION_CODE": {
    "Dep": {
      "times": {
        "TRAIN_NUMBER": "HH:MM",
        ...
      }
    }
  },
  ...
}
```
""")
