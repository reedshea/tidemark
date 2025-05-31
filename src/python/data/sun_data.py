#!/usr/bin/env python3
"""
Sun data provider - calculates sunrise/sunset times with twilight for Boston area
"""

import datetime
import math

# Sun rise/set data for Boston area (42.3601° N, 71.0589° W)
# This is sample data - in production, these would be calculated astronomically
# Times are in EST/EDT
BOSTON_SUN_DATA = {
    # Each entry contains sunrise, sunset times with twilight periods
    "2025-05-30": {
        "nautical_dawn": {"hour": 4, "minute": 5},
        "sunrise": {"hour": 5, "minute": 8},
        "sunset": {"hour": 19, "minute": 56},
        "nautical_dusk": {"hour": 21, "minute": 0}
    },
    "2025-05-31": {
        "nautical_dawn": {"hour": 4, "minute": 4},
        "sunrise": {"hour": 5, "minute": 8},
        "sunset": {"hour": 19, "minute": 57},
        "nautical_dusk": {"hour": 21, "minute": 1}
    },
    "2025-06-01": {
        "nautical_dawn": {"hour": 4, "minute": 4},
        "sunrise": {"hour": 5, "minute": 7},
        "sunset": {"hour": 19, "minute": 58},
        "nautical_dusk": {"hour": 21, "minute": 2}
    }
}

def get_sun_events(date=None):
    """
    Get sun rise/set times with twilight for a specific date
    
    Parameters:
    - date: Date to get sun data for (default: today)
    
    Returns:
    - Dictionary with nautical_dawn, sunrise, sunset, nautical_dusk times
    """
    # Default to today if no date provided
    if date is None:
        date = datetime.datetime.now().date()
    
    date_str = date.strftime("%Y-%m-%d")
    
    # Check if we have hardcoded data for this date
    if date_str in BOSTON_SUN_DATA:
        return BOSTON_SUN_DATA[date_str].copy()
    else:
        # Generate approximate data based on patterns
        # For Boston in late May/early June
        # Sunrise around 5:08 AM, sunset around 8:00 PM
        # Nautical twilight is when sun is 12 degrees below horizon
        # Approximately 1 hour before sunrise and after sunset
        
        base_date = datetime.datetime(2025, 5, 30)
        days_diff = (date - base_date.date()).days
        
        # Sun times shift by about 1 minute per day
        sunrise_minutes = 5 * 60 + 8 - days_diff  # 5:08 AM base
        sunset_minutes = 19 * 60 + 56 + days_diff  # 7:56 PM base
        
        # Nautical twilight approximately 63 minutes before/after
        nautical_dawn_minutes = sunrise_minutes - 63
        nautical_dusk_minutes = sunset_minutes + 63
        
        return {
            "nautical_dawn": {
                "hour": nautical_dawn_minutes // 60,
                "minute": nautical_dawn_minutes % 60
            },
            "sunrise": {
                "hour": sunrise_minutes // 60,
                "minute": sunrise_minutes % 60
            },
            "sunset": {
                "hour": sunset_minutes // 60,
                "minute": sunset_minutes % 60
            },
            "nautical_dusk": {
                "hour": nautical_dusk_minutes // 60,
                "minute": nautical_dusk_minutes % 60
            }
        }

def get_sun_events_for_range(start_date, days=2):
    """
    Get sun rise/set times with twilight for multiple days
    
    Parameters:
    - start_date: Starting date
    - days: Number of days to fetch (default: 2)
    
    Returns:
    - List of dictionaries, each containing:
      - date: The date for this set of events
      - nautical_dawn, sunrise, sunset, nautical_dusk: Time dictionaries
    """
    events = []
    for i in range(days):
        date = start_date + datetime.timedelta(days=i)
        day_events = get_sun_events(date)
        day_events['date'] = date
        events.append(day_events)
    return events

def convert_sun_events_to_hours_since_start(sun_events_list, start_datetime):
    """
    Convert sun events to hours since a start datetime
    
    Parameters:
    - sun_events_list: List of sun events from get_sun_events_for_range
    - start_datetime: Reference datetime to calculate hours from
    
    Returns:
    - List of events with hours_since_start added
    """
    converted_events = []
    
    for day_events in sun_events_list:
        date = day_events['date']
        
        # Convert each event to hours since start
        for event_type in ['nautical_dawn', 'sunrise', 'sunset', 'nautical_dusk']:
            if event_type in day_events and day_events[event_type]:
                event_time = day_events[event_type]
                # Create datetime for this event
                event_datetime = datetime.datetime.combine(
                    date,
                    datetime.time(event_time['hour'], event_time['minute'])
                )
                
                # Calculate hours since start
                time_diff = event_datetime - start_datetime
                hours_since_start = time_diff.total_seconds() / 3600
                
                # Include events from -24 to 48 hours to capture previous day's events
                if -24 <= hours_since_start <= 48:
                    converted_events.append({
                        'type': event_type,
                        'hours_since_start': hours_since_start,
                        'datetime': event_datetime,
                        'hour': event_time['hour'],
                        'minute': event_time['minute']
                    })
    
    # Sort by hours_since_start
    converted_events.sort(key=lambda x: x['hours_since_start'])
    return converted_events

if __name__ == "__main__":
    # Test the module
    data = get_sun_events()
    print(f"Sun data for today:")
    print(f"Nautical dawn: {data['nautical_dawn']['hour']:02d}:{data['nautical_dawn']['minute']:02d}")
    print(f"Sunrise: {data['sunrise']['hour']:02d}:{data['sunrise']['minute']:02d}")
    print(f"Sunset: {data['sunset']['hour']:02d}:{data['sunset']['minute']:02d}")
    print(f"Nautical dusk: {data['nautical_dusk']['hour']:02d}:{data['nautical_dusk']['minute']:02d}")
    
    # Test multi-day fetch
    print("\nMulti-day sun events:")
    start_date = datetime.datetime.now().date()
    events = get_sun_events_for_range(start_date, days=2)
    for day_events in events:
        print(f"\nDate: {day_events['date']}")
        print(f"  Sunrise: {day_events['sunrise']['hour']:02d}:{day_events['sunrise']['minute']:02d}")
        print(f"  Sunset: {day_events['sunset']['hour']:02d}:{day_events['sunset']['minute']:02d}")