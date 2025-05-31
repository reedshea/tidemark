#!/usr/bin/env python3
"""
Tide data fetcher - calculates tide information from harmonic constituents
"""

import datetime
import json
import os
import math

# Harmonic constituents for Great Hill, Massachusetts (Station ID: 8447368)
# Values typically provided by NOAA or other oceanographic authorities
GREAT_HILL_CONSTITUENTS = {
    "station_id": "8447368",
    "name": "Great Hill, Massachusetts",
    "mean_tide_level": 0.590,            # Meters, relative to Mean Lower Low Water
    "time_zone": "GMT",                 # Time zone for phase data
    "unit": "meters",                   # Unit for amplitude and height
    "constituents": [
        {"name": "M2", "amplitude": 0.559, "phase": 12.4, "speed": 28.984104, "description": "Principal lunar semidiurnal constituent"},
        {"name": "S2", "amplitude": 0.125, "phase": 34.6, "speed": 30.0, "description": "Principal solar semidiurnal constituent"},
        {"name": "N2", "amplitude": 0.142, "phase": 356.1, "speed": 28.43973, "description": "Larger lunar elliptic semidiurnal constituent"},
        {"name": "K1", "amplitude": 0.063, "phase": 169.5, "speed": 15.041069, "description": "Lunar diurnal constituent"},
        {"name": "M4", "amplitude": 0.095, "phase": 43.2, "speed": 57.96821, "description": "Shallow water overtides of principal lunar constituent"},
        {"name": "O1", "amplitude": 0.052, "phase": 200.1, "speed": 13.943035, "description": "Lunar diurnal constituent"},
        {"name": "M6", "amplitude": 0.01, "phase": 299.5, "speed": 86.95232, "description": "Shallow water overtides of principal lunar constituent"},
        {"name": "MK3", "amplitude": 0.014, "phase": 15.7, "speed": 44.025173, "description": "Shallow water terdiurnal"},
        {"name": "S4", "amplitude": 0.008, "phase": 1.5, "speed": 60.0, "description": "Shallow water overtides of principal solar constituent"},
        {"name": "MN4", "amplitude": 0.042, "phase": 351.5, "speed": 57.423832, "description": "Shallow water quarter diurnal constituent"},
        {"name": "NU2", "amplitude": 0.022, "phase": 350.3, "speed": 28.512583, "description": "Larger lunar evectional constituent"},
        {"name": "S6", "amplitude": 0.001, "phase": 291.3, "speed": 90.0, "description": "Shallow water overtides of principal solar constituent"},
        {"name": "MU2", "amplitude": 0.028, "phase": 355.5, "speed": 27.968208, "description": "Variational constituent"},
        {"name": "2N2", "amplitude": 0.023, "phase": 342.4, "speed": 27.895355, "description": "Lunar elliptical semidiurnal second-order constituent"},
        {"name": "OO1", "amplitude": 0.006, "phase": 174.0, "speed": 16.139101, "description": "Lunar diurnal"},
        {"name": "LAM2", "amplitude": 0.002, "phase": 60.4, "speed": 29.455626, "description": "Smaller lunar evectional constituent"},
        {"name": "S1", "amplitude": 0.011, "phase": 145.3, "speed": 15.0, "description": "Solar diurnal constituent"},
        {"name": "M1", "amplitude": 0.005, "phase": 186.1, "speed": 14.496694, "description": "Smaller lunar elliptic diurnal constituent"},
        {"name": "J1", "amplitude": 0.005, "phase": 158.1, "speed": 15.5854435, "description": "Smaller lunar elliptic diurnal constituent"},
        {"name": "MM", "amplitude": 0.017, "phase": 73.9, "speed": 0.5443747, "description": "Lunar monthly constituent"},
        {"name": "SSA", "amplitude": 0.016, "phase": 75.1, "speed": 0.0821373, "description": "Solar semiannual constituent"},
        {"name": "SA", "amplitude": 0.061, "phase": 145.3, "speed": 0.0410686, "description": "Solar annual constituent"},
        {"name": "MSF", "amplitude": 0.0, "phase": 0.0, "speed": 1.0158958, "description": "Lunisolar synodic fortnightly constituent"},
        {"name": "MF", "amplitude": 0.0, "phase": 0.0, "speed": 1.0980331, "description": "Lunisolar fortnightly constituent"},
        {"name": "RHO", "amplitude": 0.004, "phase": 193.0, "speed": 13.471515, "description": "Larger lunar evectional diurnal constituent"},
        {"name": "Q1", "amplitude": 0.009, "phase": 176.8, "speed": 13.398661, "description": "Larger lunar elliptic diurnal constituent"},
        {"name": "T2", "amplitude": 0.011, "phase": 22.0, "speed": 29.958933, "description": "Larger solar elliptic constituent"},
        {"name": "R2", "amplitude": 0.005, "phase": 264.6, "speed": 30.041067, "description": "Smaller solar elliptic constituent"},
        {"name": "2Q1", "amplitude": 0.003, "phase": 203.6, "speed": 12.854286, "description": "Larger elliptic diurnal"},
        {"name": "P1", "amplitude": 0.019, "phase": 176.9, "speed": 14.958931, "description": "Solar diurnal constituent"},
        {"name": "2SM2", "amplitude": 0.004, "phase": 42.5, "speed": 31.015896, "description": "Shallow water semidiurnal constituent"},
        {"name": "M3", "amplitude": 0.009, "phase": 15.5, "speed": 43.47616, "description": "Lunar terdiurnal constituent"},
        {"name": "L2", "amplitude": 0.014, "phase": 12.5, "speed": 29.528479, "description": "Smaller lunar elliptic semidiurnal constituent"},
        {"name": "2MK3", "amplitude": 0.016, "phase": 357.2, "speed": 42.92714, "description": "Shallow water terdiurnal constituent"},
        {"name": "K2", "amplitude": 0.033, "phase": 30.5, "speed": 30.082138, "description": "Lunisolar semidiurnal constituent"},
        {"name": "M8", "amplitude": 0.002, "phase": 188.2, "speed": 115.93642, "description": "Shallow water eighth diurnal constituent"},
        {"name": "MS4", "amplitude": 0.026, "phase": 117.9, "speed": 58.984104, "description": "Shallow water quarter diurnal constituent"}
    ]
}


# Dictionary mapping of location names to constituent data
LOCATIONS = {
    "great_hill": GREAT_HILL_CONSTITUENTS,
    "8447368": GREAT_HILL_CONSTITUENTS  # Also accessible by station ID
}

def calculate_tide_height(constituents, datetime_point):
    """
    Calculate tide height at a specific time based on harmonic constituents
    
    Parameters:
    - constituents: Dictionary of tidal constituents with amplitude, phase, and speed
    - datetime_point: The datetime to calculate the tide height for
    
    Returns:
    - Tide height in meters
    """
    # Calculate hours since the UNIX epoch (Jan 1, 1970)
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime_point.tzinfo)
    hours_since_epoch = (datetime_point - epoch).total_seconds() / 3600.0
    
    # Start with mean tide level
    height = constituents["mean_tide_level"]
    
    # Add contribution from each constituent
    for const in constituents["constituents"]:
        # Calculate the angle in radians
        angle = math.radians(const["phase"]) + math.radians(const["speed"]) * hours_since_epoch
        
        # Add the constituent's contribution
        height += const["amplitude"] * math.cos(angle)
    
    return height

def find_extrema(heights, times, start_datetime=None):
    """
    Find local minima and maxima in the tide height data
    
    Parameters:
    - heights: List of tide heights
    - times: List of corresponding datetime objects
    - start_datetime: Reference datetime for calculating relative hours
    
    Returns:
    - List of dictionaries for high and low tides
    """
    extrema = []
    
    # Need at least 3 points to detect extrema
    if len(heights) < 3:
        return extrema
    
    for i in range(1, len(heights) - 1):
        # Check for local maximum (high tide)
        if heights[i] > heights[i-1] and heights[i] > heights[i+1]:
            dt = times[i]
            entry = {
                'hour': dt.hour,
                'minute': dt.minute,
                'height': round(heights[i], 2),
                'type': 'H'
            }
            # Calculate hours since start if start_datetime is provided
            if start_datetime:
                hours_since_start = (dt - start_datetime).total_seconds() / 3600.0
                entry['hours_since_start'] = hours_since_start
            extrema.append(entry)
        
        # Check for local minimum (low tide)
        elif heights[i] < heights[i-1] and heights[i] < heights[i+1]:
            dt = times[i]
            entry = {
                'hour': dt.hour,
                'minute': dt.minute,
                'height': round(heights[i], 2),
                'type': 'L'
            }
            # Calculate hours since start if start_datetime is provided
            if start_datetime:
                hours_since_start = (dt - start_datetime).total_seconds() / 3600.0
                entry['hours_since_start'] = hours_since_start
            extrema.append(entry)
    
    return extrema

def get_tide_data(location=None, date=None, hours=24):
    """
    Get tide data for a specific location and date
    
    Parameters:
    - location: String identifier for location or dictionary with station_id
    - date: Date to get tide data for (default: today)
    - hours: Number of hours to generate data for (default: 24)
    
    Returns:
    - List of tide points (high and low tides)
    """
    # Save cache path in user directory
    cache_dir = os.path.expanduser("~/.tidemark")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Default to current time if no date provided
    if date is None:
        # Round to nearest 5 minutes
        now = datetime.datetime.now()
        minutes = now.minute
        rounded_minutes = (minutes // 5) * 5
        start_datetime = now.replace(minute=rounded_minutes, second=0, microsecond=0)
    else:
        start_datetime = datetime.datetime.combine(date, datetime.time(0, 0))
    
    # Format as YYYY-MM-DD-HH-MM for cache key
    date_str = start_datetime.strftime("%Y-%m-%d-%H-%M")
    
    # Default to Great Hill if no location provided
    location_key = "great_hill"
    
    # Check if location is a string ID
    if isinstance(location, str):
        location_key = location
    # Check if location is a dict with station_id
    elif isinstance(location, dict) and 'station_id' in location:
        location_key = location['station_id']
    
    # Get the constituent data for the location
    if location_key in LOCATIONS:
        constituent_data = LOCATIONS[location_key]
    else:
        constituent_data = GREAT_HILL_CONSTITUENTS  # Default to Great Hill
    
    # Create a cache file name that includes the location and hours
    cache_file = os.path.join(cache_dir, f"tide_{location_key}_{date_str}_{hours}h.json")
    
    # Check cache first (to avoid recalculation)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If cache is corrupted, continue to calculate new data
            pass
    
    # Calculate tide data for the specified number of hours
    # Generate data points every 10 minutes
    end_datetime = start_datetime + datetime.timedelta(hours=hours)
    time_points = []
    height_points = []
    
    # Generate data points every 10 minutes
    current_time = start_datetime
    while current_time <= end_datetime:
        time_points.append(current_time)
        height = calculate_tide_height(constituent_data, current_time)
        height_points.append(height)
        current_time += datetime.timedelta(minutes=10)
    
    # Find the extrema (high and low tides)
    extrema = find_extrema(height_points, time_points, start_datetime)
    
    # Add boundary points by calculating tide heights at start and end
    # This ensures we have data points at the exact edges
    height_at_start = calculate_tide_height(constituent_data, start_datetime)
    height_at_end = calculate_tide_height(constituent_data, end_datetime)
    
    # Add the start point if it's not already an extrema
    if not any(e.get('hours_since_start', -1) == 0 for e in extrema):
        extrema.insert(0, {
            'hour': start_datetime.hour,
            'minute': start_datetime.minute,
            'height': round(height_at_start, 2),
            'type': 'B',  # Boundary point
            'hours_since_start': 0
        })
    
    # Add the end point if it's not already there
    if not any(abs(e.get('hours_since_start', -1) - hours) < 0.01 for e in extrema):
        end_hour = (start_datetime.hour + hours) % 24
        end_minute = start_datetime.minute
        extrema.append({
            'hour': end_hour,
            'minute': end_minute,
            'height': round(height_at_end, 2),
            'type': 'B',  # Boundary point
            'hours_since_start': hours
        })
    
    # Cache the result
    try:
        with open(cache_file, 'w') as f:
            json.dump(extrema, f)
    except IOError:
        # If we can't write to cache, just continue
        pass
            
    return extrema

def get_locations():
    """
    Get a list of available tide locations
    
    Returns:
    - Dictionary of location name/id to display name
    """
    return {key: value["name"] for key, value in LOCATIONS.items()}

def add_location(station_id, name, constituents):
    """
    Add a new location with harmonic constituents
    
    Parameters:
    - station_id: Unique identifier for the station
    - name: Display name of the location
    - constituents: Dictionary with mean_tide_level and constituents array
    
    Returns:
    - True if successful, False otherwise
    """
    if not station_id or not name or not constituents:
        return False
    
    if 'mean_tide_level' not in constituents or 'constituents' not in constituents:
        return False
    
    # Create new location entry
    new_location = {
        "station_id": station_id,
        "name": name,
        "mean_tide_level": constituents['mean_tide_level'],
        "constituents": constituents['constituents']
    }
    
    # Add to locations dictionary
    LOCATIONS[station_id] = new_location
    LOCATIONS[name.lower().replace(' ', '_')] = new_location
    
    return True

if __name__ == "__main__":
    # Simple test when run directly
    data = get_tide_data()
    print(f"Tide data for {GREAT_HILL_CONSTITUENTS['name']}:")
    print(json.dumps(data, indent=2))
    
    # Optionally, display a specific date
    # tomorrow = datetime.datetime.now().date() + datetime.timedelta(days=1)
    # data_tomorrow = get_tide_data(date=tomorrow)
    # print(f"Tomorrow's tide data for {GREAT_HILL_CONSTITUENTS['name']}:")
    # print(json.dumps(data_tomorrow, indent=2))