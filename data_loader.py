import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data
def load_data():
    """
    Loads and cleans the world cities dataset.
    """
    DATA_URL = "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/csv/cities.csv"
    
    try:
        df = pd.read_csv(DATA_URL)
        
        # Rename columns to match our app's expectation
        # Expected: city, country, lat, lon, population, timezone
        rename_map = {
            'name': 'city',
            'country_name': 'country',
            'latitude': 'lat',
            'longitude': 'lon',
            'population': 'population',
            'timezone': 'timezone'
        }
        df = df.rename(columns=rename_map)
        
        # Ensure coordinates and population are numeric
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df['population'] = pd.to_numeric(df['population'], errors='coerce')
        
        # Drop rows with missing critical data
        df = df.dropna(subset=['lat', 'lon', 'population', 'city', 'country'])
        
        # Filter out cities with 0 or very small population to reduce noise and file size influence
        df = df[df['population'] > 10000]
        
        # Sort by population descending
        df = df.sort_values(by='population', ascending=False).reset_index(drop=True)
        
        # Keep top 5000 cities for performance (rendering 48k+ columns in 3D can be heavy)
        # The user asked for "all most populated", so top 5000 covers significant ones.
        df = df.head(5000)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r
