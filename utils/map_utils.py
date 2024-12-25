import folium
import streamlit as st
from streamlit_folium import st_folium
import numpy as np
from folium import plugins
import json
import os
import logging
from folium.plugins import MarkerCluster

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

    # Create marker clusters for stations and trains
    station_cluster = MarkerCluster(name="Stations")
    train_cluster = MarkerCluster(name="Trains")

    # Add station markers with trains
    for station, coords in station_coords.items():
        # Add station marker
        station_icon = folium.Icon(
            color='gray',
            icon='train',
            prefix='fa'
        )

        folium.Marker(
            coords,
            popup=f"<b>Station: {station}</b>",
            icon=station_icon,
        ).add_to(station_cluster)

        # Add individual train markers
        station_trains = df[df['Location'] == station]
        if not station_trains.empty:
            # Calculate offset for multiple trains at the same station
            num_trains = len(station_trains)
            for idx, (_, train) in enumerate(station_trains.iterrows()):
                # Create small offset to prevent overlap
                offset_lat = coords[0] + (idx - num_trains/2) * 0.001
                offset_lon = coords[1] + (idx - num_trains/2) * 0.001

                # Determine train icon color based on status
                if train['Status'] == 'TER':
                    color = 'green'
                elif train['Status'] == 'HO':
                    color = 'red'
                else:
                    color = 'blue'

                # Create train icon
                train_icon = folium.Icon(
                    color=color,
                    icon='subway',
                    prefix='fa'
                )

                # Create detailed popup content
                popup_content = f"""
                    <div style='min-width: 200px'>
                        <h4>{train['Train Name']}</h4>
                        <b>Status:</b> {train['Status']}<br>
                        <b>Running Status:</b> {train['Running Status']}<br>
                        <b>Current Time:</b> {train['JUST TIME']}<br>
                        <b>Scheduled Time:</b> {train['WTT TIME']}<br>
                        <b>Delay:</b> {train['Time Difference']} minutes
                    </div>
                """

                # Add train marker
                folium.Marker(
                    [offset_lat, offset_lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=train_icon,
                    tooltip=f"Train: {train['Train Name']}"
                ).add_to(train_cluster)

    # Add clusters to map
    station_cluster.add_to(m)
    train_cluster.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m

def generate_heatmap_data(df):
    """Generate heatmap data from train locations."""
    heat_data = []
    station_coords = load_station_coordinates()

    for station, count in df['Location'].value_counts().items():
        if station in station_coords:
            coords = station_coords[station]
            heat_data.append([coords[0], coords[1], count])
    return heat_data

def display_train_map(df):
    """Display the train map in Streamlit."""
    try:
        # Add coordinate update interface
        with st.expander("📍 Update Station Coordinates", expanded=False):
            update_station_coordinates()

        train_map = create_train_map(df)
        if train_map:
            st.subheader("Train Location Map")
            # Add map description with updated legend
            st.markdown("""
            🗺️ **Map Legend:**
            - 🚉 Gray markers: Railway Stations
            - 🚂 Colored markers: Individual Trains
                - 🟢 Green: Terminated trains (TER)
                - 🔴 Red: Held trains (HO)
                - 🔵 Blue: Other status

            Note: Trains at the same station are slightly offset for better visibility.
            Use the layer control ⚙️ to show/hide stations and trains.
            """)
            st_folium(train_map, height=600)
    except Exception as e:
        logger.error(f"Error displaying map: {str(e)}")
        st.error(f"Error displaying map: {str(e)}")