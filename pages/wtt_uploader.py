import streamlit as st
import json
import pandas as pd
from typing import Dict, Any, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_station_code(code: str) -> Tuple[bool, str]:
    """Validate station code format"""
    if not code or not isinstance(code, str):
        return False, "Station code must be a non-empty string"
    if not code.isalpha():
        return False, "Station code must contain only letters"
    if not 2 <= len(code) <= 5:
        return False, "Station code must be between 2 and 5 characters"
    return True, ""

def validate_train_number(number: str) -> Tuple[bool, str]:
    """Validate train number format"""
    if not number or not isinstance(number, str):
        return False, "Train number must be a non-empty string"
    if not number.isdigit():
        return False, "Train number must contain only digits"
    if not 4 <= len(number) <= 5:
        return False, "Train number must be between 4 and 5 digits"
    return True, ""

def validate_time_format(time: str) -> Tuple[bool, str]:
    """Validate time format (HH:MM)"""
    if not time:
        return True, ""  # Empty time is allowed
    try:
        pd.to_datetime(time, format='%H:%M')
        return True, ""
    except ValueError:
        return False, "Time must be in HH:MM format"

def validate_wtt_json(data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate the WTT JSON structure and collect statistics"""
    errors = []
    warnings = []
    stats = {
        'total_stations': 0,
        'total_trains': 0,
        'empty_times': {'Arr': 0, 'Dep': 0},
        'invalid_times': {'Arr': 0, 'Dep': 0},
        'station_stats': {},
        'time_range': {
            'Arr': {'earliest': '23:59', 'latest': '00:00'},
            'Dep': {'earliest': '23:59', 'latest': '00:00'}
        }
    }

    try:
        # Check if it's a dictionary
        if not isinstance(data, dict):
            errors.append("Invalid JSON structure: Root must be a dictionary")
            return False, errors, stats

        # Check each station
        for station, station_data in data.items():
            # Validate station code
            is_valid, msg = validate_station_code(station)
            if not is_valid:
                errors.append(f"Station {station}: {msg}")
                continue

            # Initialize station statistics
            stats['total_stations'] += 1
            stats['station_stats'][station] = {
                'total_trains': 0,
                'empty_times': {'Arr': 0, 'Dep': 0},
                'invalid_times': {'Arr': 0, 'Dep': 0}
            }

            # Check if station data is a dictionary
            if not isinstance(station_data, dict):
                errors.append(f"Invalid structure for station {station}")
                continue

            # Validate both Arr and Dep sections
            for section in ['Arr', 'Dep']:
                if section not in station_data:
                    if section == 'Dep':  # Dep is mandatory
                        errors.append(f"Missing '{section}' key for station {station}")
                    continue

                section_data = station_data[section]
                if not isinstance(section_data, dict):
                    errors.append(f"Invalid '{section}' structure for station {station}")
                    continue

                # Check times structure
                if 'times' not in section_data:
                    errors.append(f"Missing 'times' key in {section} for station {station}")
                    continue

                times_data = section_data['times']
                if not isinstance(times_data, dict):
                    errors.append(f"Invalid 'times' structure in {section} for station {station}")
                    continue

                # Validate times
                for train_no, time in times_data.items():
                    # Validate train number
                    is_valid, msg = validate_train_number(train_no)
                    if not is_valid:
                        errors.append(f"Station {station}, {section}, {msg}")
                        continue

                    stats['total_trains'] += 1
                    stats['station_stats'][station]['total_trains'] += 1

                    if not time:
                        stats['empty_times'][section] += 1
                        stats['station_stats'][station]['empty_times'][section] += 1
                        continue

                    # Validate time format
                    is_valid, msg = validate_time_format(time)
                    if not is_valid:
                        stats['invalid_times'][section] += 1
                        stats['station_stats'][station]['invalid_times'][section] += 1
                        errors.append(f"Station {station}, {section}, Train {train_no}: {msg}")
                        continue

                    # Update time range
                    if time < stats['time_range'][section]['earliest']:
                        stats['time_range'][section]['earliest'] = time
                    if time > stats['time_range'][section]['latest']:
                        stats['time_range'][section]['latest'] = time

            # Add warnings for stations with high empty times
            for section in ['Arr', 'Dep']:
                section_stats = stats['station_stats'][station]['empty_times'][section]
                total_trains = stats['station_stats'][station]['total_trains']
                if total_trains > 0 and section_stats > total_trains * 0.5:
                    warnings.append(f"Warning: Station {station} has more than 50% empty {section} times")

        return len(errors) == 0, errors + warnings, stats

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        errors.append(f"Validation error: {str(e)}")
        return False, errors, stats

# Page configuration
st.set_page_config(
    page_title="WTT Upload",
    page_icon="📤",
    layout="wide"
)

st.title("Working Time Table (WTT) Uploader")
st.write("Upload and validate your WTT JSON file")

# Validation rules section
with st.expander("📋 Validation Rules", expanded=False):
    st.markdown("""
    ### JSON Structure Rules
    - Root must be a dictionary
    - Each station must have a 'Dep' key (mandatory)
    - 'Arr' key is optional but follows the same structure if present
    - Each section must have a 'times' dictionary

    ### Station Code Rules
    - Must be 2-5 uppercase letters
    - Must contain only alphabetic characters

    ### Train Number Rules
    - Must be 4-5 digits
    - Must contain only numeric characters

    ### Time Format Rules
    - Must be in HH:MM format
    - Hours must be between 00-23
    - Minutes must be between 00-59
    - Empty times are allowed but will be flagged
    """)

# File uploader
uploaded_file = st.file_uploader("Choose a JSON file", type=['json'])

if uploaded_file is not None:
    try:
        # Read and parse JSON
        content = uploaded_file.read()
        data = json.loads(content)

        # Validate JSON structure
        is_valid, messages, stats = validate_wtt_json(data)

        # Display validation results
        st.subheader("Validation Results")
        if is_valid:
            st.success("✅ File validation successful!")

            # Display statistics
            st.subheader("📊 File Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Stations", stats['total_stations'])
                st.metric("Total Trains", stats['total_trains'])
            with col2:
                st.write("Empty Times:")
                st.write(f"- Arrivals: {stats['empty_times']['Arr']}")
                st.write(f"- Departures: {stats['empty_times']['Dep']}")

            st.write("Time Ranges:")
            st.write(f"- Arrivals: {stats['time_range']['Arr']['earliest']} - {stats['time_range']['Arr']['latest']}")
            st.write(f"- Departures: {stats['time_range']['Dep']['earliest']} - {stats['time_range']['Dep']['latest']}")

            # Station-wise statistics
            st.subheader("📈 Station Statistics")
            station_data = []
            for station, stat in stats['station_stats'].items():
                station_data.append({
                    'Station': station,
                    'Total Trains': stat['total_trains'],
                    'Empty Arrivals': stat['empty_times']['Arr'],
                    'Empty Departures': stat['empty_times']['Dep'],
                    'Invalid Arrivals': stat['invalid_times']['Arr'],
                    'Invalid Departures': stat['invalid_times']['Dep']
                })
            station_df = pd.DataFrame(station_data)
            st.dataframe(station_df.set_index('Station'))

            # Enable save button only if validation passes
            if st.button("Save WTT Data", type="primary"):
                try:
                    with open('bhanu.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    st.success("🎉 WTT data saved successfully!")
                    logger.info("WTT data saved to bhanu.json")
                except Exception as e:
                    st.error(f"Error saving file: {str(e)}")
                    logger.error(f"Error saving WTT data: {str(e)}")
        else:
            st.error("❌ Validation failed!")

            # Display errors and warnings
            with st.expander("⚠️ Validation Messages", expanded=True):
                for msg in messages:
                    if msg.startswith("Warning"):
                        st.warning(msg)
                    else:
                        st.error(msg)

        # Display JSON preview
        with st.expander("🔍 File Preview", expanded=False):
            st.json(data)

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON file: {str(e)}")
        logger.error(f"JSON decode error: {str(e)}")
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        logger.error(f"File processing error: {str(e)}")
else:
    st.info("👆 Upload a JSON file to get started")

# Sample JSON Structure
with st.expander("📝 Sample JSON Structure", expanded=False):
    st.code("""
{
  "GDR": {
    "Arr": {
      "times": {
        "12345": "09:15",
        "67890": "14:30"
      }
    },
    "Dep": {
      "times": {
        "12345": "09:30",
        "67890": "14:45"
      }
    }
  },
  "MBL": {
    "Arr": {
      "times": {
        "12345": "10:00",
        "67890": "15:15"
      }
    },
    "Dep": {
      "times": {
        "12345": "10:15",
        "67890": "15:30"
      }
    }
  }
}
""", language="json")