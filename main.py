import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import random
from datetime import datetime, timedelta
import pytz
from data_loader import load_data, calculate_distance

# Page Config (Must be first)
st.set_page_config(
    page_title="World Populated Cities",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("style.css")

# --- Header ---
st.markdown('<h1 class="big-title">Urban Pulpit</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Exploring the World\'s Most Populated Cities in 3D</p>', unsafe_allow_html=True)

# --- Data Loading ---
df = load_data()

if df.empty:
    st.error("Failed to load data. Please check your connection.")
    st.stop()

# --- Sidebar ---
st.sidebar.markdown("## 🎛️ Controls")

# Filter: Country
countries = sorted(df['country'].unique())
selected_countries = st.sidebar.multiselect(
    "Select Countries",
    countries,
    default=None,
    help="Filter the map and charts by country."
)

# Filter: Population Range
min_pop = int(df['population'].min())
max_pop = int(df['population'].max())

pop_range = st.sidebar.slider(
    "Population Range",
    min_value=min_pop,
    max_value=max_pop,
    value=(100_000, max_pop), # Default start at 100k to filter noise
    format="%d"
)

# Filter: Map Style & Surprise Me
st.sidebar.markdown("---")
map_style = st.sidebar.radio(
    "Map Layer",
    ["3D Columns", "Heatmap", "Scatter"],
    help="Choose how the cities are visualized."
)

if st.sidebar.button("🎲 Surprise Me!"):
    if not filtered_df.empty:
        random_city = filtered_df.sample(1).iloc[0]
        st.session_state['view_lat'] = random_city['lat']
        st.session_state['view_lon'] = random_city['lon']
        st.session_state['view_zoom'] = 10
        st.toast(f"Flying to {random_city['city']}, {random_city['country']}! ✈️")
    else:
        st.warning("No cities in current filter to fly to!")

# Filter: Time Machine
st.sidebar.markdown("---")
with st.sidebar.expander("⏳ Time Machine"):
    future_mode = st.toggle("Enable Future Projection")
    if future_mode:
        target_year = st.slider("Project Year", 2025, 2050, 2025)
        # Simple growth model: 1.1% annual growth (simplified global avg)
        current_year = datetime.now().year
        years_diff = target_year - current_year
        growth_rate = 1.011 
        
        # Apply projection
        df['population'] = (df['population'] * (growth_rate ** years_diff)).astype(int)
        st.sidebar.caption(f"Projecting population in {target_year} with 1.1% annual growth.")

# Apply Filters
filtered_df = df[
    (df['population'] >= pop_range[0]) &
    (df['population'] <= pop_range[1])
]


if selected_countries:
    filtered_df = filtered_df[filtered_df['country'].isin(selected_countries)]

# --- Metrics Section ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Cities", f"{len(filtered_df):,}")
with col2:
    total_pop = filtered_df['population'].sum()
    st.metric("Total Population", f"{total_pop/1_000_000:.1f} M")
with col3:
    if not filtered_df.empty:
        top_city = filtered_df.iloc[0]
        st.metric("Largest City", top_city['city'])
    else:
        st.metric("Largest City", "-")
with col4:
    if not filtered_df.empty:
        # Just an example stat: Avg Population
        avg_pop = filtered_df['population'].mean()
        st.metric("Avg City Pop", f"{avg_pop/1_000_000:.2f} M")
    else:
        st.metric("Avg City Pop", "-")

st.markdown("---")

# --- Comparison Arena ---
st.markdown("---")
st.markdown("### ⚔️ City Arena")

flight_data = []

if not filtered_df.empty and len(filtered_df) > 1:
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        city1_name = st.selectbox("Select Contender 1", filtered_df['city'].unique(), index=0, key="c1")
    with c_col2:
        # Default to 2nd city if available
        default_idx = 1 if len(filtered_df['city'].unique()) > 1 else 0
        city2_name = st.selectbox("Select Contender 2", filtered_df['city'].unique(), index=default_idx, key="c2")

    if city1_name and city2_name:
        city1 = filtered_df[filtered_df['city'] == city1_name].iloc[0]
        city2 = filtered_df[filtered_df['city'] == city2_name].iloc[0]
        
        # Calculate Distance
        dist_km = calculate_distance(city1['lat'], city1['lon'], city2['lat'], city2['lon'])
        
        # Prepare Flight Data for Map (ArcLayer)
        flight_data = [{
            "source": [city1['lon'], city1['lat']],
            "target": [city2['lon'], city2['lat']],
            "source_name": city1['city'],
            "target_name": city2['city']
        }]
        
        # Calculate Time Difference
        time_diff_str = "N/A"
        try:
            tz1 = pytz.timezone(city1['timezone']) if city1['timezone'] else pytz.utc
            tz2 = pytz.timezone(city2['timezone']) if city2['timezone'] else pytz.utc
            
            now = datetime.now(pytz.utc)
            t1 = now.astimezone(tz1)
            t2 = now.astimezone(tz2)
            
            offset_diff = (t1.utcoffset() - t2.utcoffset()).total_seconds() / 3600
            time_diff_str = f"{abs(offset_diff)}h"
            
            c1_time_str = t1.strftime("%I:%M %p")
            c2_time_str = t2.strftime("%I:%M %p")
        except:
             c1_time_str = "--:--"
             c2_time_str = "--:--"

        # Determine winner for population
        c1_pop_class = "winner" if city1['population'] > city2['population'] else ""
        c2_pop_class = "winner" if city2['population'] > city1['population'] else ""

        col_a, col_b, col_c = st.columns([1, 0.2, 1])
        
        with col_a:
            st.markdown(f"""
            <div class="comparison-card">
                <h2>{city1['city']}</h2>
                <p style="color: grey">{city1['country']}</p>
                <div class="stat-row">
                    <span class="stat-label">Population</span>
                    <span class="stat-value {c1_pop_class}">{city1['population']:,}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Local Time</span>
                    <span class="stat-value">{c1_time_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_b:
             st.markdown('<div class="vs-badge">VS</div>', unsafe_allow_html=True)
             st.markdown(f"<div style='text-align: center; color: #94a3b8; font-size: 0.8rem;'>Distance<br><b>{int(dist_km):,} km</b><br><br>Time Diff<br><b>{time_diff_str}</b></div>", unsafe_allow_html=True)

        with col_c:
            st.markdown(f"""
            <div class="comparison-card">
                <h2>{city2['city']}</h2>
                <p style="color: grey">{city2['country']}</p>
                <div class="stat-row">
                    <span class="stat-label">Population</span>
                    <span class="stat-value {c2_pop_class}">{city2['population']:,}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Local Time</span>
                    <span class="stat-value">{c2_time_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

else:
    st.info("Need at least 2 cities for comparison. Adjust filters.")

# --- 3D Map Visualization (Moved to Bottom to show Flight Paths) ---
if not filtered_df.empty:
    st.markdown("### 🌐 Global Density Map")
    
    # View State Management
    if 'view_lat' not in st.session_state:
        st.session_state['view_lat'] = np.average(filtered_df['lat'])
        st.session_state['view_lon'] = np.average(filtered_df['lon'])
        st.session_state['view_zoom'] = 2

    view_state = pdk.ViewState(
        latitude=st.session_state['view_lat'],
        longitude=st.session_state['view_lon'],
        zoom=st.session_state['view_zoom'],
        min_zoom=1,
        max_zoom=15,
        pitch=45,
        bearing=0
    )

    layers = []

    if map_style == "3D Columns":
        layers.append(pdk.Layer(
            "ColumnLayer",
            data=filtered_df,
            get_position=["lon", "lat"],
            get_elevation="population",
            elevation_scale=50,
            radius=20000,
            get_fill_color=[180, 0, 200, 140],
            pickable=True,
            auto_highlight=True,
        ))
    elif map_style == "Heatmap":
        layers.append(pdk.Layer(
            "HeatmapLayer",
            data=filtered_df,
            get_position=["lon", "lat"],
            get_weight="population",
            radius_pixels=60,
        ))
    elif map_style == "Scatter":
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=filtered_df,
            get_position=["lon", "lat"],
            get_radius="population",
            radius_scale=0.05,
            get_fill_color=[10, 150, 250, 140],
            pickable=True,
        ))

    # Flight Arc Layer
    if flight_data:
        layers.append(pdk.Layer(
            "ArcLayer",
            data=flight_data,
            get_source_position="source",
            get_target_position="target",
            get_source_color=[0, 255, 0, 160],
            get_target_color=[255, 0, 0, 160],
            get_width=5,
            width_min_pixels=3,
        ))

    tooltip = {
        "html": "<b>{city}</b>, {country}<br/>Population: <b>{population}</b>",
        "style": {
            "background": "grey",
            "color": "white",
            "font-family": '"Helvetica Neue", Roboto, Arial, sans-serif',
            "z-index": "10000",
        },
    }

    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/dark-v10",
    )

    st.pydeck_chart(r)
else:
    st.warning("No cities found with the current filters.")


# --- Charts Section ---
st.markdown("---")
c1, c2 = st.columns((1, 1))

with c1:
    st.markdown("### 🏙️ Top 15 Cities by Population")
    if not filtered_df.empty:
        # Top 15 for the bar chart
        top_cities = filtered_df.head(15).sort_values(by="population", ascending=True) # Ascending for horiz bar
        
        fig_bar = px.bar(
            top_cities,
            x="population",
            y="city",
            orientation='h',
            text_auto=True,
            color="population",
            color_continuous_scale="Viridis",
            hover_data=["country", "lat", "lon"]
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, title=None),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig_bar, width="stretch")

with c2:
    st.markdown("### 🗺️ Population Distribution")
    if not filtered_df.empty:
        # Treemap or Sunburst
        # Limit to top 50 for performance if dataset is huge, or aggregate by country
        
        # Aggregate by country first for a cleaner chart if needed, but per-city is requested
        # Let's do a Treemap of Top 30 Cities
        top_30 = filtered_df.head(30)
        
        fig_tree = px.treemap(
            top_30,
            path=[px.Constant("World"), 'country', 'city'],
            values='population',
            color='population',
            color_continuous_scale='Magma'
        )
        fig_tree.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig_tree, width="stretch")

# --- Data Table ---
st.markdown("### 📋 Detailed Dataset")
with st.expander("Show Raw Data"):
    st.dataframe(
        filtered_df[['city', 'country', 'population', 'lat', 'lon']],
        use_container_width=True,
        hide_index=True
    )

