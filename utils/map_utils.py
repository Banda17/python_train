import folium
import streamlit as st
from streamlit_folium import st_folium
import numpy as np
from folium import plugins
import json
import os
import logging
from folium.plugins import MarkerCluster
import pandas as pd # Added pandas import

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

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, min_zoom=7)

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
                # Create smaller offset (reduced from 0.001 to 0.0002) to keep trains closer together
                angle = (idx * 360 / num_trains) * (np.pi / 180)  # Convert to radians
                radius = 0.0002  # Reduced radius for tighter grouping
                offset_lat = coords[0] + radius * np.cos(angle)
                offset_lon = coords[1] + radius * np.sin(angle)

                # Get color based on train status and running status
                status_color = None

                # First check Status (TER/HO)
                if train['Status'] == 'TER':
                    status_color = st.session_state.color_scheme['TER'].lstrip('#')
                elif train['Status'] == 'HO':
                    status_color = st.session_state.color_scheme['HO'].lstrip('#')
                # Then check Running Status if no Status match
                elif train['Running Status'] == 'EARLY':
                    status_color = st.session_state.color_scheme['EARLY'].lstrip('#')
                elif train['Running Status'] == 'ON TIME':
                    status_color = st.session_state.color_scheme['ON_TIME'].lstrip('#')
                elif train['Running Status'] == 'LATE':
                    status_color = st.session_state.color_scheme['LATE'].lstrip('#')
                else:
                    status_color = '3186cc'  # Default blue

                # Create train icon with status color
                train_icon = folium.Icon(
                    color='white',  # Use white as base
                    icon='subway',
                    prefix='fa',
                    icon_color=f'#{status_color}'  # Apply status color to icon
                )

                # Create detailed popup content with colored header
                popup_content = f"""
                    <div style='min-width: 200px'>
                        <div style='background-color: #{status_color}; color: white; padding: 5px; border-radius: 3px;'>
                            <h4 style='margin: 0;'>{train['Train Name']}</h4>
                        </div>
                        <div style='padding: 5px;'>
                            <b>Status:</b> {train['Status']}<br>
                            <b>Running Status:</b> {train['Running Status']}<br>
                            <b>Current Time:</b> {train['JUST TIME']}<br>
                            <b>Scheduled Time:</b> {train['WTT TIME']}<br>
                            <b>Delay:</b> {train['Time Difference']} minutes
                        </div>
                    </div>
                """

                # Add train marker
                folium.Marker(
                    [offset_lat, offset_lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=train_icon,
                    tooltip=f"Train: {train['Train Name']} ({train['Status']} - {train['Running Status']})"
                ).add_to(train_cluster)

    # Add clusters to map
    station_cluster.add_to(m)
    train_cluster.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m

def display_train_map(df):
    """Display the train map in Streamlit."""
    try:
        # Add coordinate update interface
        with st.expander("📍 Update Station Coordinates", expanded=False):
            update_station_coordinates()

        train_map = create_train_map(df)
        if train_map:
            st.subheader("🗺️ Train Location Map")

            # Create a container for the table first
            st.markdown("### 🚂 Trains at Station")

            # Initialize table data
            clicked_location = None
            display_df = pd.DataFrame(columns=['Train Name', 'Status', 'Running Status', 'Time Difference'])
            st.markdown("*Click on a station on the map below to view trains*")

            # Display map
            map_data = st_folium(train_map, height=600)

            # Process clicked location
            if map_data is not None and 'last_clicked' in map_data:
                clicked = map_data['last_clicked']
                if clicked:
                    # Find nearest station to clicked point
                    clicked_lat, clicked_lon = clicked['lat'], clicked['lng']
                    station_coords = load_station_coordinates()
                    min_dist = float('inf')
                    for station, (lat, lon) in station_coords.items():
                        dist = ((lat - clicked_lat) ** 2 + (lon - clicked_lon) ** 2) ** 0.5
                        if dist < min_dist:
                            min_dist = dist
                            clicked_location = station

            # Update table based on clicked location
            if clicked_location:
                display_df = df[df['Location'] == clicked_location][
                    ['Train Name', 'Status', 'Running Status', 'Time Difference']
                ].copy()
                st.markdown(f"**Selected Station: {clicked_location}**")

            # Style and display the table
            display_df.columns = ['Train', 'Status', 'Running', 'Delay']

            def style_row(row):
                color = None
                if row['Status'] == 'TER':
                    color = st.session_state.color_scheme['TER']
                elif row['Status'] == 'HO':
                    color = st.session_state.color_scheme['HO']
                elif row['Running'] == 'EARLY':
                    color = st.session_state.color_scheme['EARLY']
                elif row['Running'] == 'ON TIME':
                    color = st.session_state.color_scheme['ON_TIME']
                elif row['Running'] == 'LATE':
                    color = st.session_state.color_scheme['LATE']

                return [f'background-color: {color}; color: white' if color else '' for _ in row]

            styled_df = display_df.style.apply(style_row, axis=1)

            # Display the table
            st.dataframe(
                styled_df,
                hide_index=True,
                height=200,  # Reduced height since it's above the map
                use_container_width=True
            )

            # Add map legend below the map
            st.markdown("""
            ---
            **Map Legend:**
            - 🚉 Gray markers: Railway Stations
            - 🚂 Train Status Colors:
                - 🟢 Green: Terminated (TER)
                - 🔴 Red: Held (HO)
                - 🟢 Green: Running Early
                - 🔵 Blue: Running On Time
                - 🔴 Red: Running Late
            """)

    except Exception as e:
        logger.error(f"Error displaying map: {str(e)}")
        st.error(f"Error displaying map: {str(e)}")

def generate_heatmap_data(df):
    """Generate heatmap data from train locations."""
    heat_data = []
    station_coords = load_station_coordinates()

    for station, count in df['Location'].value_counts().items():
        if station in station_coords:
            coords = station_coords[station]
            heat_data.append([coords[0], coords[1], count])
    return heat_data