import folium
import streamlit as st
from streamlit_folium import st_folium
import numpy as np
from folium import plugins
import json
import os
import logging
from folium.plugins import MarkerCluster
import pandas as pd
from typing import Dict, List, Tuple, Any
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=32)
def load_station_coordinates():
    """
    Load and cache station coordinates from stations.json file.
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

def filter_trains_in_viewport(df: pd.DataFrame, bounds: Dict[str, float]) -> pd.DataFrame:
    """Filter trains that are within the current map viewport."""
    station_coords = load_station_coordinates()
    filtered_trains = []

    for _, train in df.iterrows():
        station = train['Location']
        if station in station_coords:
            lat, lon = station_coords[station]
            if (bounds['south'] <= lat <= bounds['north'] and 
                bounds['west'] <= lon <= bounds['east']):
                filtered_trains.append(train)

    return pd.DataFrame(filtered_trains) if filtered_trains else pd.DataFrame()

def create_train_map(df: pd.DataFrame):
    """Create a folium map with optimized train locations and heatmap."""
    station_coords = load_station_coordinates()

    if not station_coords:
        st.error("No station coordinates available. Please update coordinates first.")
        return None

    # Calculate map center
    center_lat = sum(pos[0] for pos in station_coords.values()) / len(station_coords)
    center_lon = sum(pos[1] for pos in station_coords.values()) / len(station_coords)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        min_zoom=7,
        max_zoom=15,
        prefer_canvas=True
    )

    # Add tile layer with optimized settings
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='OpenStreetMap',
        name='Base Map',
        control=False,
        max_zoom=15,
        max_native_zoom=15,
        no_wrap=True,
        opacity=0.7
    ).add_to(m)

    # Create optimized marker clusters
    station_cluster = MarkerCluster(
        name="Stations",
        options={
            'maxClusterRadius': 30,
            'disableClusteringAtZoom': 10,
            'spiderfyOnMaxZoom': True,
            'chunkedLoading': True,
            'zoomToBoundsOnClick': True,
            'showCoverageOnHover': False,
            'animate': False
        }
    )

    # Add station markers
    for station, coords in station_coords.items():
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

    # Prepare train markers data
    train_markers = []
    for station, coords in station_coords.items():
        station_trains = df[df['Location'] == station]
        if not station_trains.empty:
            num_trains = len(station_trains)
            for idx, (_, train) in enumerate(station_trains.iterrows()):
                # Calculate optimized marker placement
                angle = (idx * 360 / num_trains) * (np.pi / 180)
                radius = 0.0002
                offset_lat = coords[0] + radius * np.cos(angle)
                offset_lon = coords[1] + radius * np.sin(angle)

                # Use cached status colors
                status_color = None
                delay_color = 'cc3232'  # Dark red for delays
                if train['Status'] == 'TER':
                    status_color = '90EE90'  # Light green
                elif train['Status'] == 'HO':
                    status_color = 'FFB6B6'  # Light red
                elif train['Running Status'] == 'EARLY':
                    status_color = '90EE90'  # Light green
                elif train['Running Status'] == 'ON TIME':
                    status_color = 'ADD8E6'  # Light blue
                elif train['Running Status'] == 'LATE':
                    status_color = delay_color  # Use dark red for late status
                else:
                    status_color = 'ADD8E6'  # Light blue default

                # Create marker data
                marker_data = {
                    'lat': offset_lat,
                    'lon': offset_lon,
                    'name': train['Train Name'],
                    'color': status_color,
                    'status': train['Status'],
                    'running_status': train['Running Status'],
                    'current_time': train['JUST TIME'],
                    'scheduled_time': train['WTT TIME'],
                    'delay': train['Time Difference']
                }
                train_markers.append(marker_data)

    # Create train cluster with marker data
    train_cluster = plugins.MarkerCluster(
        name="Trains",
        options={
            'maxClusterRadius': 40,
            'disableClusteringAtZoom': 11,
            'spiderfyOnMaxZoom': True,
            'chunkedLoading': True,
            'zoomToBoundsOnClick': True,
            'showCoverageOnHover': False,
            'animate': False
        }
    )

    # Add train markers to cluster
    for marker in train_markers:
        train_icon = folium.Icon(
            color='white',
            icon='subway',
            prefix='fa',
            icon_color=f'#{marker["color"]}'
        )

        # Add delay color to popup if train is late
        header_color = marker["color"]
        if marker["running_status"] == "LATE":
            header_color = delay_color

        popup_content = f"""
            <div class='train-popup' style='min-width: 200px'>
                <div style='background-color: #{header_color}; color: white; padding: 5px; border-radius: 3px;'>
                    <h4 style='margin: 0;'>{marker["name"]}</h4>
                </div>
                <div style='padding: 5px;'>
                    <b>Status:</b> {marker["status"]}<br>
                    <b>Running Status:</b> {marker["running_status"]}<br>
                    <b>Current Time:</b> {marker["current_time"]}<br>
                    <b>Scheduled Time:</b> {marker["scheduled_time"]}<br>
                    <b>Delay:</b> <span style="color: #{delay_color if marker["running_status"] == "LATE" else marker["color"]}">{marker["delay"]} minutes</span>
                </div>
            </div>
        """

        folium.Marker(
            [marker['lat'], marker['lon']],
            popup=folium.Popup(popup_content, max_width=300, lazy=True),
            icon=train_icon,
            tooltip=f"Train: {marker['name']}"
        ).add_to(train_cluster)

    # Add clusters to map
    station_cluster.add_to(m)
    train_cluster.add_to(m)

    # Add layer control and scale
    folium.LayerControl(collapsed=True, position='topright').add_to(m)
    plugins.MeasureControl(position='bottomleft').add_to(m)

    return m

def display_train_map(df: pd.DataFrame):
    """Display the optimized train map in Streamlit."""
    try:
        # Create map with initial data
        train_map = create_train_map(df)
        if not train_map:
            return

        # Create a container for the table
        st.markdown("### 🚂 Trains at Station")
        clicked_location = None
        display_df = pd.DataFrame(columns=['Train Name', 'Status', 'Running Status', 'WTT TIME', 'JUST TIME', 'Time Difference'])
        st.markdown("*Click on a station on the map below to view trains*")

        # Display map with optimized settings
        map_data = st_folium(
            train_map,
            height=600,
            use_container_width=True,
            returned_objects=["last_clicked", "bounds"],
            key="train_map"
        )

        # Process clicked location efficiently
        if map_data and 'last_clicked' in map_data and map_data['last_clicked']:
            clicked = map_data['last_clicked']
            clicked_lat, clicked_lon = clicked['lat'], clicked['lng']
            station_coords = load_station_coordinates()

            # Vectorized distance calculation
            coords = np.array(list(station_coords.values()))
            dists = np.sqrt((coords[:, 0] - clicked_lat)**2 + (coords[:, 1] - clicked_lon)**2)
            min_idx = np.argmin(dists)
            clicked_location = list(station_coords.keys())[min_idx]

        # Update table based on clicked location
        if clicked_location:
            display_df = df[df['Location'] == clicked_location][
                ['Train Name', 'Status', 'Running Status', 'WTT TIME', 'JUST TIME', 'Time Difference']
            ].copy()
            st.markdown(f"**Selected Station: {clicked_location}**")

        # Style and display the table
        display_df.columns = ['Train', 'Status', 'Running', 'Scheduled', 'Actual', 'Delay']

        def style_row(row):
            colors = [''] * len(row)  # Start with no colors for all cells
            status_idx = 1  # Index of Status column
            running_idx = 2  # Index of Running column

            # Colors for status cells
            if row['Status'] == 'TER':
                colors[status_idx] = 'background-color: #90EE90; color: white'  # Light Green
            elif row['Status'] == 'HO':
                colors[status_idx] = 'background-color: #FFB6B6; color: white'  # Light Red

            # Colors for running status cells
            delay_color = '#cc3232'  # Dark red for delays
            if row['Running'] == 'EARLY':
                colors[running_idx] = 'background-color: #90EE90; color: white'  # Light Green
            elif row['Running'] == 'ON TIME':
                colors[running_idx] = 'background-color: #ADD8E6; color: white'  # Light Blue
            elif row['Running'] == 'LATE':
                colors[running_idx] = f'background-color: {delay_color}; color: white'  # Dark Red

            return colors

        styled_df = display_df.style.apply(style_row, axis=1)

        st.dataframe(
            styled_df,
            hide_index=True,
            height=150,
            use_container_width=True,
            column_config={
                "Train": st.column_config.TextColumn(
                    "Train",
                    help="Train number and name",
                    width="small"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Train status (TER/HO)",
                    width="small"
                ),
                "Running": st.column_config.TextColumn(
                    "Running",
                    help="Running status",
                    width="small"
                ),
                "Scheduled": st.column_config.TextColumn(
                    "Sched",
                    help="Scheduled time (WTT)",
                    width="small"
                ),
                "Actual": st.column_config.TextColumn(
                    "Actual",
                    help="Actual time",
                    width="small"
                ),
                "Delay": st.column_config.TextColumn(
                    "Delay",
                    help="Time difference",
                    width="small"
                )
            }
        )

        # Add map legend as collapsible section
        with st.expander("🔍 Map Legend", expanded=False):
            st.markdown("""
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

@lru_cache(maxsize=128)
def generate_heatmap_data(df: pd.DataFrame) -> List[List[float]]:
    """Generate and cache heatmap data from train locations."""
    heat_data = []
    station_coords = load_station_coordinates()

    for station, count in df['Location'].value_counts().items():
        if station in station_coords:
            coords = station_coords[station]
            heat_data.append([coords[0], coords[1], count])
    return heat_data

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

def save_station_coordinates(coordinates):
    """Save station coordinates to stations.json file."""
    try:
        with open('stations.json', 'w') as f:
            json.dump(coordinates, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving station coordinates: {str(e)}")
        return False