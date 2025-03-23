import pandas as pd
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
import os
import math
import json

def load_nearby_stars(max_distance=20):
    """
    Load data for stars within max_distance light years of the Sun.
    Returns a DataFrame with position, color, and other stellar properties.
    """
    # Load data from CSV file
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'stars.csv')
    
    # Read the CSV file
    stars_df = pd.read_csv(csv_path)
    
    # Clean up column names
    stars_df.columns = [col.strip() for col in stars_df.columns]
    
    # Store all the original columns for displaying full data
    all_columns = list(stars_df.columns)
    
    # Extract relevant data
    data = {
        'name': [],
        'distance_ly': [],
        'abs_magnitude': [],
        'color_b_v': [],
        'x': [],
        'y': [],
        'z': [],
        'is_multiple': [],  # Flag for multiple star systems
        'system_name': [],  # Name of the system this star belongs to
        'system_components': [],  # Number of components in the system
        'component': [],    # Component identifier (A, B, C, etc.)
        'separation': [],   # Separation information
        'original_data': []  # Store all data from CSV for each star
    }
    
    # Try to load enhanced multiple star system data if available
    star_systems_data = {}
    system_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'star_systems_mapping.json')
    
    try:
        if os.path.exists(system_data_path):
            with open(system_data_path, 'r') as f:
                star_systems_data = json.load(f)
            print(f"Loaded multiple star systems data for {len(star_systems_data)} stars")
    except Exception as e:
        print(f"Warning: Could not load star systems data: {e}")
    
    # Extract data for visualization
    for _, star in stars_df.iterrows():
        # Skip rows without distance info or with placeholder values
        if pd.isna(star['Distance (ly)']) or star['Distance (ly)'] == '--':
            continue
        
        name = star['Common Name']
        try:
            distance = float(star['Distance (ly)'])
        except (ValueError, TypeError):
            continue
        
        # Skip stars beyond the maximum distance
        if distance > max_distance:
            continue
            
        # Add basic star data
        data['name'].append(name)
        data['distance_ly'].append(distance)
        
        # Get absolute magnitude
        try:
            abs_mag = float(star['Abs Mag']) if not pd.isna(star['Abs Mag']) and star['Abs Mag'] != '--' else 10.0
        except (ValueError, TypeError):
            abs_mag = 10.0  # Default value if conversion fails
        data['abs_magnitude'].append(abs_mag)
        
        # Special case for Sirius
        if name == 'Sirius A':
            color_b_v = 'SIRIUS_BLUE'  # Force Sirius to be blue
        else:
            # Estimate B-V color from spectral class for all other stars
            spectral_class = star['Class'] if not pd.isna(star['Class']) else 'G2'
            color_b_v = estimate_b_v_from_class(spectral_class)
        
        data['color_b_v'].append(color_b_v)
        
        # Store all original data for this star
        star_data = {}
        for col in all_columns:
            if not pd.isna(star[col]) and star[col] != '--':
                star_data[col] = star[col]
        data['original_data'].append(star_data)
        
        # Check if this star is part of a multiple system using the enhanced data
        is_multiple = False
        system_name = ""
        component = ""
        system_components = 1
        separation_info = None
        
        # First check if it's in our enhanced data
        if name in star_systems_data:
            is_multiple = True
            system_info = star_systems_data[name]
            system_name = system_info['system_name']
            component = system_info['component']
            system_components = system_info['system_components']
            separation_info = system_info['separation']
        # Fallback to the simple check
        elif not pd.isna(star['Separation (AU)']) and star['Separation (AU)'] != '--':
            is_multiple = True
            # Basic system name extraction (just for fallback)
            if ' ' in name and name[-2] == ' ':  # Names like "Sirius A"
                system_name = name[:-2]
                component = name[-1]
            else:
                system_name = name
            
            separation_info = star['Separation (AU)']
        
        # Store the multiple system information
        data['is_multiple'].append(is_multiple)
        data['system_name'].append(system_name)
        data['component'].append(component)
        data['system_components'].append(system_components)
        data['separation'].append(separation_info)
        
        # Calculate approximate 3D coordinates
        # We'll use simple math to distribute stars in 3D space based on their distance
        # This is a simplification as we don't have actual 3D coordinates in the CSV
        
        # For stars with coordinate data, create more accurate positions
        try:
            # Check if both l and b coordinates are available as separate columns
            if ('Galactic Coordinates (l°)' in stars_df.columns and 
                'Galactic Coordinates (b°)' in stars_df.columns and
                not pd.isna(star['Galactic Coordinates (l°)']) and 
                not pd.isna(star['Galactic Coordinates (b°)'])):
                
                gal_l = float(star['Galactic Coordinates (l°)'])
                gal_b = float(star['Galactic Coordinates (b°)'])
                
                # Convert galactic coordinates to 3D Cartesian
                l_rad = math.radians(gal_l)
                b_rad = math.radians(gal_b)
                
                # Calculate 3D coordinates
                x = distance * math.cos(b_rad) * math.cos(l_rad)
                y = distance * math.cos(b_rad) * math.sin(l_rad)
                z = distance * math.sin(b_rad)
            
            # Check if combined coordinates are available 
            elif ('Galactic Coordinates (l° b°)' in stars_df.columns and
                  not pd.isna(star['Galactic Coordinates (l° b°)']) and 
                  star['Galactic Coordinates (l° b°)'] != '--'):
                
                gal_coords = star['Galactic Coordinates (l° b°)'].split(',')
                gal_l = float(gal_coords[0].strip())
                gal_b = float(gal_coords[1].strip())
                
                # Convert galactic coordinates to 3D Cartesian
                l_rad = math.radians(gal_l)
                b_rad = math.radians(gal_b)
                
                # Calculate 3D coordinates
                x = distance * math.cos(b_rad) * math.cos(l_rad)
                y = distance * math.cos(b_rad) * math.sin(l_rad)
                z = distance * math.sin(b_rad)
            else:
                # For stars without coordinate data, distribute randomly at their distance
                theta = np.random.random() * 2 * np.pi
                phi = np.random.random() * np.pi - np.pi/2
                x = distance * np.cos(phi) * np.cos(theta)
                y = distance * np.cos(phi) * np.sin(theta)
                z = distance * np.sin(phi)
        except (ValueError, IndexError):
            # Fallback to random distribution if conversion fails
            theta = np.random.random() * 2 * np.pi
            phi = np.random.random() * np.pi - np.pi/2
            x = distance * np.cos(phi) * np.cos(theta)
            y = distance * np.cos(phi) * np.sin(theta)
            z = distance * np.sin(phi)
        
        # Special case for the Sun
        if name == 'Sun':
            x, y, z = 0, 0, 0
            
        data['x'].append(x)
        data['y'].append(y)
        data['z'].append(z)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Load the complete multiple star systems information
    systems_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'multiple_systems.json')
    
    try:
        if os.path.exists(systems_data_path):
            with open(systems_data_path, 'r') as f:
                all_systems_data = json.load(f)
            # Add the systems data as a separate attribute to the DataFrame
            df.system_info = all_systems_data
            print(f"Loaded full multiple star systems data: {len(all_systems_data['systems'])} systems")
        else:
            # Create a simple placeholder if file doesn't exist
            df.system_info = {'systems': []}
    except Exception as e:
        print(f"Warning: Could not load full systems data: {e}")
        # Create a simple placeholder if loading fails
        df.system_info = {'systems': []}
    
    # Use color from the Color column if available, otherwise calculate it from B-V index
    if 'Color' in all_columns:
        # Map text color names to RGB hex values
        color_map = {
            'red': '#ff5555',
            'darkred': '#aa0000',
            'orange': '#ff9955',
            'yellow': '#ffff55',
            'lyellow': '#ffffaa',  # light yellow
            'white': '#ffffff',
            'grey': '#aaaaaa'
        }
        
        # Create a new column with the color hex values
        direct_colors = []
        for _, star in df.iterrows():
            star_data = star['original_data']
            if 'Color' in star_data and star_data['Color'].lower() in color_map:
                direct_colors.append(color_map[star_data['Color'].lower()])
            else:
                # Fallback to calculated color if missing
                direct_colors.append(b_v_to_rgb(star['color_b_v']))
                
        df['color'] = direct_colors
    else:
        # Calculate color based on B-V color index if no Color column
        df['color'] = df['color_b_v'].apply(b_v_to_rgb)
    
    return df

def estimate_b_v_from_class(spectral_class):
    """
    Estimate B-V color index based on spectral class with subclass precision.
    Enhanced for more color variety, with special focus on A-class stars.
    Reference: https://en.wikipedia.org/wiki/Stellar_classification
    """
    # Default for missing or invalid data
    if not spectral_class or pd.isna(spectral_class):
        return 0.65  # Default to solar value
    
    # Extract the main spectral type and subclass if available
    spectral_class = str(spectral_class).strip().upper()
    
    # Special case for Sirius - A1 class
    if spectral_class == 'A1':
        return 'SIRIUS_BLUE'  # Special tag for vivid blue color
    
    # Handle white dwarfs specially - they follow a different classification
    if spectral_class.startswith('D') or 'WD' in spectral_class:
        return '0.1_white_dwarf'  # Tagged for special handling
    
    # Extract main spectral type (first character)
    spectral_type = spectral_class[0]
    
    # Try to extract numeric subclass (0-9)
    subclass = 5  # Default to middle of the range if not specified
    for char in spectral_class[1:]:
        if char.isdigit():
            subclass = int(char)
            break
    
    # Modified B-V values - much more blue for A stars
    base_values = {
        'O': -0.33,  # Very rare in our dataset
        'B': -0.20,  # Blue stars
        'A': -0.15,  # A0 is deep blue, shifted way down to be more blue
        'F': 0.30,   # White to yellow-white
        'G': 0.60,   # G2 (Sun) = 0.65, Yellow
        'K': 1.00,   # Orange
        'M': 1.50,   # Red
        'L': 1.80,   # Deep red
        'T': 2.00,   # Very red
        'Y': 2.20    # Extremely red
    }
    
    # Use main spectral type to get base value or default to G
    base_value = base_values.get(spectral_type, 0.65)
    
    # Special handling for A-class stars to make them much more blue
    if spectral_type == 'A':
        # Subclass 0 is bluest, 9 is more white
        # For A stars: A0 = -0.15, A9 = 0.10
        adjusted_value = base_value + (subclass * 0.025)
        return adjusted_value
    
    # Adjust based on subclass (0-9) for other spectral types
    if spectral_type in base_values:
        # Get the next spectral type's value for interpolation
        spectral_types = list(base_values.keys())
        current_index = spectral_types.index(spectral_type)
        
        if current_index < len(spectral_types) - 1:
            next_type = spectral_types[current_index + 1]
            next_value = base_values[next_type]
            
            # Calculate the range between types
            type_range = next_value - base_value
            
            # Adjust based on subclass (0 = coolest/reddest, 9 = hottest/bluest of the type)
            # For most spectral types, higher subclass means redder
            adjustment = type_range * (subclass / 10)
            
            # Adjust the value
            return base_value + adjustment
    
    return base_value

def b_v_to_rgb(b_v):
    """
    Convert B-V color index or spectral class tag to RGB values.
    Enhanced for more dramatic colors from blue to deep red,
    with A-class stars (like Sirius A1) appearing distinctly blue.
    """
    # Special case for A1 stars (Sirius) - forced to be very blue
    if isinstance(b_v, str) and b_v == 'SIRIUS_BLUE':
        r = 30
        g = 100
        b = 255
        return f'#{int(r):02x}{int(g):02x}{int(b):02x}'
    
    # Special case for white dwarfs - bluish white with slight purple tint
    if isinstance(b_v, str) and 'white_dwarf' in b_v:
        r = 180
        g = 200
        b = 255
        # Return as hex color
        return f'#{int(r):02x}{int(g):02x}{int(b):02x}'
    
    # Limit the B-V value to a reasonable range for non-string values
    if not isinstance(b_v, str):
        b_v = max(-0.4, min(2.0, b_v))
    
    # Adjusted color mappings with much more aggressive blue tones for A stars
    
    if b_v < -0.1:  # A0-A2 stars - vivid blue (includes Sirius A1 in normal path)
        r = 40
        g = 100
        b = 255
    elif b_v < 0.0:  # A3-A5 stars - bright blue
        r = 80
        g = 140
        b = 255
    elif b_v < 0.1:  # A6-A9 stars - blue with slight white
        r = 130
        g = 180
        b = 255
    elif b_v < 0.2:  # Early F stars - blue-white
        r = 180
        g = 210
        b = 255
    elif b_v < 0.3:  # Mid F stars - white with blue tinge
        r = 225
        g = 235
        b = 255
    elif b_v < 0.4:  # Late F stars - pure white
        r = 250
        g = 250
        b = 250
    elif b_v < 0.5:  # Early G stars - white with yellow tinge
        r = 255
        g = 250
        b = 225
    elif b_v < 0.6:  # Mid G stars - yellow-white
        r = 255
        g = 245
        b = 180
    elif b_v < 0.7:  # G stars (including Sun) - yellow
        r = 255
        g = 240
        b = 140
    elif b_v < 0.8:  # Late G stars - golden yellow
        r = 255
        g = 220
        b = 100
    elif b_v < 0.9:  # Latest G stars - yellow-orange
        r = 255
        g = 200
        b = 80
    elif b_v < 1.0:  # Early K stars - light orange
        r = 255
        g = 180
        b = 60
    elif b_v < 1.1:  # K stars - orange
        r = 255
        g = 160
        b = 45
    elif b_v < 1.2:  # Mid K stars - deep orange
        r = 255
        g = 140
        b = 40
    elif b_v < 1.3:  # Late K stars - orange-red
        r = 255
        g = 120
        b = 35
    elif b_v < 1.4:  # K-M transition - light red
        r = 255
        g = 100
        b = 30
    elif b_v < 1.5:  # Early M stars - red
        r = 255
        g = 80
        b = 25
    elif b_v < 1.6:  # M stars - medium red
        r = 255
        g = 60
        b = 20
    elif b_v < 1.8:  # Mid M stars - deeper red
        r = 240
        g = 40
        b = 15
    elif b_v < 2.0:  # Late M stars - dark red
        r = 220
        g = 30
        b = 10
    else:  # L, T, Y and cooler stars - very dark red
        r = 200
        g = 20
        b = 5
    
    # Return as hex color
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'

