import folium
import streamlit as st
from streamlit_folium import folium_static
import numpy as np
from folium import plugins

# Dictionary of station coordinates (latitude, longitude)
STATION_COORDINATES = {
    'GDR': (21.5200, 86.8800),  # Gundadhara
    'MBL': (21.9300, 86.7400),  # Mumbai Local
    'KMLP': (22.4800, 88.3200),  # Kamalpur
    'VKT': (22.5800, 88.3600),  # Vikramshila
    'VDE': (22.6200, 88.4000),  # Vidyasagar
    'NLS': (22.6700, 88.4300),  # New Lines
    'NLR': (22.7000, 88.4500),  # North Line
    'PGU': (22.7400, 88.4700)   # Pragati
}

def generate_heatmap_data(df):
    """Generate heatmap data from train locations."""
    heat_data = []
    for station, count in df['Location'].value_counts().items():
        if station in STATION_COORDINATES:
            # Add coordinates with weight based on number of trains
            coords = STATION_COORDINATES[station]
            heat_data.append([coords[0], coords[1], count])
    return heat_data

def create_train_map(df):
    """Create a folium map with train locations and heatmap."""
    # Create a map centered on the average position of all stations
    center_lat = sum(pos[0] for pos in STATION_COORDINATES.values()) / len(STATION_COORDINATES)
    center_lon = sum(pos[1] for pos in STATION_COORDINATES.values()) / len(STATION_COORDINATES)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

    # Add heatmap layer
    heat_data = generate_heatmap_data(df)
    if heat_data:
        plugins.HeatMap(heat_data, radius=25).add_to(m)

    # Add station markers
    for station, coords in STATION_COORDINATES.items():
        # Filter trains at this station
        station_trains = df[df['Location'] == station]

        if not station_trains.empty:
            # Create popup text with train information
            popup_text = f"<b>{station}</b><br>"
            for _, train in station_trains.iterrows():
                # Get color from session state based on status
                status_color = (
                    st.session_state.color_scheme['TER'] if train['Status'] == 'TER' else
                    st.session_state.color_scheme['HO'] if train['Status'] == 'HO' else
                    'blue'
                )
                # Remove '#' from hex color for HTML
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
        train_map = create_train_map(df)
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