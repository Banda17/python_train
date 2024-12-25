import streamlit as st
import folium
from streamlit_folium import folium_static
import json
import pandas as pd
from typing import Dict, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="GPS Coordinate Manager",
    page_icon="📍",
    layout="wide"
)

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
    """Validate latitude and longitude values."""
    try:
        if not -90 <= lat <= 90:
            return False, "Latitude must be between -90 and 90 degrees"
        if not -180 <= lon <= 180:
            return False, "Longitude must be between -180 and 180 degrees"
        return True, ""
    except Exception as e:
        return False, str(e)

def load_coordinates() -> Dict[str, Tuple[float, float]]:
    """Load station coordinates from file."""
    try:
        with open('stations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        st.error(f"Error loading coordinates: {str(e)}")
        return {}

def save_coordinates(coordinates: Dict[str, Tuple[float, float]]) -> bool:
    """Save station coordinates to file."""
    try:
        with open('stations.json', 'w') as f:
            json.dump(coordinates, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving coordinates: {str(e)}")
        return False

def preview_coordinates(coordinates: Dict[str, Tuple[float, float]]):
    """Create a preview map with the current coordinates."""
    if not coordinates:
        st.warning("No coordinates to display")
        return

    # Calculate map center
    lats, lons = zip(*coordinates.values())
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

    # Add markers for each station
    for station, (lat, lon) in coordinates.items():
        folium.Marker(
            [lat, lon],
            popup=f"<b>{station}</b><br>Lat: {lat:.4f}<br>Lon: {lon:.4f}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

    # Add connecting lines between stations
    coordinates_list = list(coordinates.values())
    folium.PolyLine(
        coordinates_list,
        weight=2,
        color='blue',
        opacity=0.8
    ).add_to(m)

    return m

# Page header
st.markdown("""
    <div class='train-header'>
        <h1>GPS Coordinate Manager</h1>
        <p>Manage and validate station coordinates for precise train tracking</p>
    </div>
""", unsafe_allow_html=True)

# Load existing coordinates
coordinates = load_coordinates()

# Main interface
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📝 Coordinate Editor")
    
    # Add new station
    with st.form("new_station_form"):
        st.write("Add New Station")
        new_station = st.text_input(
            "Station Code",
            help="Enter 2-5 letter station code"
        ).upper()
        
        new_lat = st.number_input(
            "Latitude",
            value=0.0,
            format="%.6f",
            help="Enter latitude (-90 to 90)"
        )
        
        new_lon = st.number_input(
            "Longitude",
            value=0.0,
            format="%.6f",
            help="Enter longitude (-180 to 180)"
        )

        submit = st.form_submit_button("Add Station")
        
        if submit:
            if not new_station or not 2 <= len(new_station) <= 5:
                st.error("Invalid station code. Must be 2-5 letters.")
            else:
                is_valid, error_msg = validate_coordinates(new_lat, new_lon)
                if is_valid:
                    coordinates[new_station] = (new_lat, new_lon)
                    if save_coordinates(coordinates):
                        st.success(f"Added station {new_station}")
                        st.rerun()
                else:
                    st.error(error_msg)

    # Edit existing stations
    st.write("---")
    st.subheader("✏️ Edit Stations")
    
    if coordinates:
        station_to_edit = st.selectbox(
            "Select Station",
            options=list(coordinates.keys()),
            format_func=lambda x: f"{x} ({coordinates[x][0]:.4f}, {coordinates[x][1]:.4f})"
        )
        
        if station_to_edit:
            current_lat, current_lon = coordinates[station_to_edit]
            
            edit_lat = st.number_input(
                f"Latitude for {station_to_edit}",
                value=float(current_lat),
                format="%.6f"
            )
            
            edit_lon = st.number_input(
                f"Longitude for {station_to_edit}",
                value=float(current_lon),
                format="%.6f"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Update", use_container_width=True):
                    is_valid, error_msg = validate_coordinates(edit_lat, edit_lon)
                    if is_valid:
                        coordinates[station_to_edit] = (edit_lat, edit_lon)
                        if save_coordinates(coordinates):
                            st.success(f"Updated {station_to_edit}")
                            st.rerun()
                    else:
                        st.error(error_msg)
            
            with col2:
                if st.button("Delete", use_container_width=True):
                    if st.session_state.get('confirm_delete') != station_to_edit:
                        st.session_state.confirm_delete = station_to_edit
                        st.warning(f"Click delete again to confirm removing {station_to_edit}")
                    else:
                        del coordinates[station_to_edit]
                        if save_coordinates(coordinates):
                            st.success(f"Deleted {station_to_edit}")
                            st.session_state.confirm_delete = None
                            st.rerun()
    else:
        st.info("No stations configured yet")

with col2:
    st.subheader("🗺️ Preview Map")
    
    preview_map = preview_coordinates(coordinates)
    if preview_map:
        folium_static(preview_map)
    
    # Export/Import section
    st.write("---")
    st.subheader("📤 Export/Import")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export to CSV", use_container_width=True):
            if coordinates:
                df = pd.DataFrame([
                    {
                        'Station': station,
                        'Latitude': lat,
                        'Longitude': lon
                    }
                    for station, (lat, lon) in coordinates.items()
                ])
                
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "station_coordinates.csv",
                    "text/csv",
                    key='download-csv'
                )
            else:
                st.warning("No coordinates to export")
    
    with col2:
        uploaded_file = st.file_uploader("Import from CSV", type=['csv'])
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                new_coordinates = {
                    row['Station']: (row['Latitude'], row['Longitude'])
                    for _, row in df.iterrows()
                }
                
                # Validate all coordinates before saving
                all_valid = True
                for station, (lat, lon) in new_coordinates.items():
                    is_valid, error_msg = validate_coordinates(lat, lon)
                    if not is_valid:
                        st.error(f"Invalid coordinates for {station}: {error_msg}")
                        all_valid = False
                        break
                
                if all_valid:
                    coordinates.update(new_coordinates)
                    if save_coordinates(coordinates):
                        st.success("Coordinates imported successfully")
                        st.rerun()
            
            except Exception as e:
                st.error(f"Error importing coordinates: {str(e)}")

# Display current coordinates table
st.write("---")
st.subheader("📋 Current Coordinates")

if coordinates:
    df = pd.DataFrame([
        {
            'Station': station,
            'Latitude': lat,
            'Longitude': lon
        }
        for station, (lat, lon) in coordinates.items()
    ])
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            'Station': st.column_config.TextColumn(
                'Station Code',
                help='Station identifier'
            ),
            'Latitude': st.column_config.NumberColumn(
                'Latitude',
                help='Latitude in decimal degrees',
                format="%.6f"
            ),
            'Longitude': st.column_config.NumberColumn(
                'Longitude',
                help='Longitude in decimal degrees',
                format="%.6f"
            )
        }
    )
else:
    st.info("No coordinates configured yet")
