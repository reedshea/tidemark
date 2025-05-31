#!/usr/bin/env python3
"""
Moon data provider - calculates moon rise/set times and phase for Boston area
"""

import datetime
import json
import os
import math

# Moon rise/set data for Boston area (42.3601° N, 71.0589° W)
# This is sample data - in production, these would be calculated astronomically
# Times are in EST/EDT
BOSTON_MOON_DATA = {
    # Each entry contains moonrise, moonset times and phase for that date
    # Phase: 0 = New Moon, 0.25 = First Quarter, 0.5 = Full Moon, 0.75 = Last Quarter
    "2025-05-30": {
        "moonrise": {"hour": 6, "minute": 42},
        "moonset": {"hour": 21, "minute": 18},
        "phase": 0.11  # Waxing crescent
    },
    "2025-05-31": {
        "moonrise": {"hour": 7, "minute": 51},
        "moonset": {"hour": 22, "minute": 20},
        "phase": 0.18
    },
    "2025-06-01": {
        "moonrise": {"hour": 9, "minute": 2},
        "moonset": {"hour": 23, "minute": 15},
        "phase": 0.25  # First quarter
    },
    "2025-06-02": {
        "moonrise": {"hour": 10, "minute": 12},
        "moonset": None,  # Sets after midnight
        "phase": 0.32
    },
    "2025-06-03": {
        "moonrise": {"hour": 11, "minute": 20},
        "moonset": {"hour": 0, "minute": 3},  # Early morning
        "phase": 0.39
    }
}

def calculate_moon_phase(date):
    """
    Calculate approximate moon phase for a given date
    Based on the synodic month (29.53 days)
    
    Returns phase as a value between 0 and 1:
    - 0.0 = New Moon
    - 0.25 = First Quarter
    - 0.5 = Full Moon
    - 0.75 = Last Quarter
    """
    # Known new moon date (January 1, 2000 was close to new moon)
    known_new_moon = datetime.datetime(2000, 1, 6, 18, 14)
    
    # Convert date to datetime if needed
    if isinstance(date, datetime.date) and not isinstance(date, datetime.datetime):
        date = datetime.datetime.combine(date, datetime.time(12, 0))
    
    # Calculate days since known new moon
    delta = date - known_new_moon
    days = delta.total_seconds() / 86400.0
    
    # Synodic month is approximately 29.53 days
    synodic_month = 29.530588
    
    # Calculate phase (0 to 1)
    phase = (days % synodic_month) / synodic_month
    
    return phase

def get_moon_events(date=None):
    """
    Get moon rise/set times and phase for a specific date
    
    Parameters:
    - date: Date to get moon data for (default: today)
    
    Returns:
    - Dictionary with moonrise, moonset times and phase
    """
    # Default to today if no date provided
    if date is None:
        date = datetime.datetime.now().date()
    
    date_str = date.strftime("%Y-%m-%d")
    
    # Check if we have hardcoded data for this date
    if date_str in BOSTON_MOON_DATA:
        data = BOSTON_MOON_DATA[date_str].copy()
    else:
        # Generate approximate data based on patterns
        # Moon rises about 50 minutes later each day
        base_date = datetime.datetime(2025, 5, 30)
        days_diff = (date - base_date.date()).days
        
        # Base times from our known data
        base_moonrise_minutes = 6 * 60 + 42  # 6:42 AM
        base_moonset_minutes = 21 * 60 + 18  # 9:18 PM
        
        # Add ~50 minutes per day
        moonrise_minutes = (base_moonrise_minutes + days_diff * 50) % (24 * 60)
        moonset_minutes = (base_moonset_minutes + days_diff * 50) % (24 * 60)
        
        data = {
            "moonrise": {
                "hour": moonrise_minutes // 60,
                "minute": moonrise_minutes % 60
            },
            "moonset": {
                "hour": moonset_minutes // 60,
                "minute": moonset_minutes % 60
            },
            "phase": calculate_moon_phase(date)
        }
    
    # Handle cases where moon sets after midnight
    # If moonset is earlier than moonrise, it's the next day
    if data["moonset"] and data["moonrise"]:
        moonrise_total = data["moonrise"]["hour"] * 60 + data["moonrise"]["minute"]
        moonset_total = data["moonset"]["hour"] * 60 + data["moonset"]["minute"]
        
        # If moonset appears earlier, it might be next day or there might be no moonset in this 24h period
        if moonset_total < moonrise_total:
            # Check if this is an early morning moonset (from previous day's rise)
            if moonset_total < 360:  # Before 6 AM
                # This is fine, it's an early morning set
                pass
            else:
                # Moon doesn't set in this 24h period
                data["moonset"] = None
    
    return data

def get_moon_phase_name(phase):
    """
    Get a human-readable name for the moon phase
    
    Parameters:
    - phase: Phase value between 0 and 1
    
    Returns:
    - String name of the phase
    """
    if phase < 0.03 or phase > 0.97:
        return "New Moon"
    elif 0.03 <= phase < 0.22:
        return "Waxing Crescent"
    elif 0.22 <= phase < 0.28:
        return "First Quarter"
    elif 0.28 <= phase < 0.47:
        return "Waxing Gibbous"
    elif 0.47 <= phase < 0.53:
        return "Full Moon"
    elif 0.53 <= phase < 0.72:
        return "Waning Gibbous"
    elif 0.72 <= phase < 0.78:
        return "Last Quarter"
    else:
        return "Waning Crescent"

def get_moon_illumination(phase):
    """
    Calculate the illuminated fraction of the moon
    
    Parameters:
    - phase: Phase value between 0 and 1
    
    Returns:
    - Illumination fraction (0 to 1)
    """
    # The illumination follows a cosine curve
    # 0 phase = new moon (0% illuminated)
    # 0.5 phase = full moon (100% illuminated)
    return (1 - math.cos(2 * math.pi * phase)) / 2

def get_moon_events_for_range(start_date, days=2):
    """
    Get moon rise/set times and phase for multiple days
    
    Parameters:
    - start_date: Starting date
    - days: Number of days to fetch (default: 2)
    
    Returns:
    - List of dictionaries, each containing:
      - date: The date for this set of events
      - moonrise, moonset: Time dictionaries
      - phase: Moon phase value
    """
    events = []
    for i in range(days):
        date = start_date + datetime.timedelta(days=i)
        day_events = get_moon_events(date)
        day_events['date'] = date
        events.append(day_events)
    return events

def convert_moon_events_to_hours_since_start(moon_events_list, start_datetime):
    """
    Convert moon events to hours since a start datetime
    
    Parameters:
    - moon_events_list: List of moon events from get_moon_events_for_range
    - start_datetime: Reference datetime to calculate hours from
    
    Returns:
    - List of events with hours_since_start added
    """
    converted_events = []
    
    for day_events in moon_events_list:
        date = day_events['date']
        
        # Process moonrise
        if 'moonrise' in day_events and day_events['moonrise']:
            moonrise_time = day_events['moonrise']
            moonrise_datetime = datetime.datetime.combine(
                date,
                datetime.time(moonrise_time['hour'], moonrise_time['minute'])
            )
            
            time_diff = moonrise_datetime - start_datetime
            hours_since_start = time_diff.total_seconds() / 3600
            
            if 0 <= hours_since_start <= 48:
                converted_events.append({
                    'type': 'moonrise',
                    'hours_since_start': hours_since_start,
                    'datetime': moonrise_datetime,
                    'hour': moonrise_time['hour'],
                    'minute': moonrise_time['minute'],
                    'phase': day_events['phase']
                })
        
        # Process moonset
        if 'moonset' in day_events and day_events['moonset']:
            moonset_time = day_events['moonset']
            moonset_datetime = datetime.datetime.combine(
                date,
                datetime.time(moonset_time['hour'], moonset_time['minute'])
            )
            
            # If moonset is early morning (before 6 AM), it might be from previous day's rise
            if moonset_time['hour'] < 6 and 'moonrise' in day_events and day_events['moonrise']:
                if moonset_time['hour'] < day_events['moonrise']['hour']:
                    # This moonset is from previous day's moonrise, skip if it's before our start
                    time_diff = moonset_datetime - start_datetime
                    hours_since_start = time_diff.total_seconds() / 3600
                    if hours_since_start < 0:
                        continue
            
            time_diff = moonset_datetime - start_datetime
            hours_since_start = time_diff.total_seconds() / 3600
            
            if 0 <= hours_since_start <= 48:
                converted_events.append({
                    'type': 'moonset',
                    'hours_since_start': hours_since_start,
                    'datetime': moonset_datetime,
                    'hour': moonset_time['hour'],
                    'minute': moonset_time['minute'],
                    'phase': day_events['phase']
                })
    
    # Sort by hours_since_start
    converted_events.sort(key=lambda x: x['hours_since_start'])
    return converted_events

if __name__ == "__main__":
    # Test the module
    data = get_moon_events()
    phase_name = get_moon_phase_name(data["phase"])
    illumination = get_moon_illumination(data["phase"])
    
    print(f"Moon data for today:")
    print(f"Moonrise: {data['moonrise']['hour']:02d}:{data['moonrise']['minute']:02d}")
    if data['moonset']:
        print(f"Moonset: {data['moonset']['hour']:02d}:{data['moonset']['minute']:02d}")
    else:
        print("Moonset: Not today")
    print(f"Phase: {phase_name} ({data['phase']:.2f})")
    print(f"Illumination: {illumination:.1%}")
    
    # Test multi-day fetch
    print("\nMulti-day moon events:")
    start_date = datetime.datetime.now().date()
    events = get_moon_events_for_range(start_date, days=2)
    for day_events in events:
        print(f"\nDate: {day_events['date']}")
        if day_events['moonrise']:
            print(f"  Moonrise: {day_events['moonrise']['hour']:02d}:{day_events['moonrise']['minute']:02d}")
        if day_events['moonset']:
            print(f"  Moonset: {day_events['moonset']['hour']:02d}:{day_events['moonset']['minute']:02d}")
        print(f"  Phase: {day_events['phase']:.2f}")