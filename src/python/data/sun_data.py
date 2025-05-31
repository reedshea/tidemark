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

if __name__ == "__main__":
    # Test the module
    data = get_sun_events()
    print(f"Sun data for today:")
    print(f"Nautical dawn: {data['nautical_dawn']['hour']:02d}:{data['nautical_dawn']['minute']:02d}")
    print(f"Sunrise: {data['sunrise']['hour']:02d}:{data['sunrise']['minute']:02d}")
    print(f"Sunset: {data['sunset']['hour']:02d}:{data['sunset']['minute']:02d}")
    print(f"Nautical dusk: {data['nautical_dusk']['hour']:02d}:{data['nautical_dusk']['minute']:02d}")