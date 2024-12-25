import folium
import streamlit as st
from streamlit_folium import folium_static
import numpy as np
from folium import plugins
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_station_coordinates():
    """
    Load station coordinates from stations.json file.
    If file doesn't exist, use default coordinates.
    """
    try:
        if os.path.exists('stations.json'):
            with open('stations.json', 'r') as f:
                return json.load(f)
        else:
            # Default coordinates - you can modify these or create stations.json
            return {
                'GDR': (21.5200, 86.8800),  # Gundadhara
                'MBL': (21.9300, 86.7400),  # Mumbai Local
                'KMLP': (22.4800, 88.3200),  # Kamalpur
                'VKT': (22.5800, 88.3600),  # Vikramshila
                'VDE': (22.6200, 88.4000),  # Vidyasagar
                'NLS': (22.6700, 88.4300),  # New Lines
                'NLR': (22.7000, 88.4500),  # North Line
                'PGU': (22.7400, 88.4700)   # Pragati
            }
    except Exception as e:
        logger.error(f"Error loading station coordinates: {str(e)}")
        return {}

def save_station_coordinates(coordinates):
    """Save station coordinates to stations.json file."""
    try:
        with open('stations.json', 'w') as f:
            json.dump(coordinates, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving station coordinates: {str(e)}")
        return False

def update_station_coordinates():
    """Streamlit interface to update station coordinates."""
    st.subheader("📍 Update Station Coordinates")

    # Load current coordinates
    current_coords = load_station_coordinates()

    # Create input fields for each station
    updated_coords = {}
    st.write("Enter new coordinates for each station (latitude, longitude):")

    for station, (lat, lon) in current_coords.items():
        col1, col2 = st.columns(2)
        with col1:
            new_lat = st.number_input(
                f"{station} Latitude",
                value=float(lat),
                format="%.4f",
                key=f"lat_{station}"
            )
        with col2:
            new_lon = st.number_input(
                f"{station} Longitude",
                value=float(lon),
                format="%.4f",
                key=f"lon_{station}"
            )
        updated_coords[station] = (new_lat, new_lon)

    if st.button("Save Coordinates"):
        if save_station_coordinates(updated_coords):
            st.success("✅ Coordinates updated successfully!")
        else:
            st.error("❌ Failed to save coordinates")

def generate_heatmap_data(df):
    """Generate heatmap data from train locations."""
    heat_data = []
    station_coords = load_station_coordinates()

    for station, count in df['Location'].value_counts().items():
        if station in station_coords:
            coords = station_coords[station]
            heat_data.append([coords[0], coords[1], count])
    return heat_data

def create_train_map(df):
    """Create a folium map with train locations and heatmap."""
    station_coords = load_station_coordinates()

    if not station_coords:
        st.error("No station coordinates available. Please update coordinates first.")
        return None

    # Create a map centered on the average position of all stations
    center_lat = sum(pos[0] for pos in station_coords.values()) / len(station_coords)
    center_lon = sum(pos[1] for pos in station_coords.values()) / len(station_coords)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

    # Add heatmap layer
    heat_data = generate_heatmap_data(df)
    if heat_data:
        plugins.HeatMap(heat_data, radius=25).add_to(m)

    # Add station markers
    for station, coords in station_coords.items():
        # Filter trains at this station
        station_trains = df[df['Location'] == station]

        if not station_trains.empty:
            # Create popup text with train information
            popup_text = f"<b>{station}</b><br>"
            for _, train in station_trains.iterrows():
                status_color = (
                    st.session_state.color_scheme['TER'] if train['Status'] == 'TER' else
                    st.session_state.color_scheme['HO'] if train['Status'] == 'HO' else
                    'blue'
                )
                status_color = status_color.lstrip('#')

                popup_text += f"""
                    <div style='color:#{status_color}'>
                        {train['Train Name']} - {train['Status']}
                        <br>Time: {train['JUST TIME']}
                        <br>Status: {train['Running Status']}
                    </div><br>
                """

            # Add marker with custom icon based on whether there are trains
            icon_color = 'green' if 'TER' in station_trains['Status'].values else 'red'
            folium.Marker(
                coords,
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=icon_color, icon='info-sign'),
            ).add_to(m)
        else:
            # Add station marker with no trains
            folium.Marker(
                coords,
                popup=f"<b>{station}</b><br>No trains currently at this station",
                icon=folium.Icon(color='gray', icon='info-sign'),
            ).add_to(m)

    return m

def display_train_map(df):
    """Display the train map in Streamlit."""
    try:
        # Add coordinate update interface
        with st.expander("📍 Update Station Coordinates", expanded=False):
            update_station_coordinates()

        train_map = create_train_map(df)
        if train_map:
            st.subheader("Train Location Map")
            # Add map description
            st.markdown("""
            🗺️ **Map Legend:**
            - 🔴 Red markers: Stations with trains held
            - 🟢 Green markers: Stations with trains terminated
            - ⚪ Gray markers: Stations with no trains
            - 🔥 Heat intensity: Shows concentration of trains
            """)
            folium_static(train_map)
    except Exception as e:
        st.error(f"Error displaying map: {str(e)}")