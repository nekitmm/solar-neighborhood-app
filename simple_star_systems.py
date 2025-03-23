#!/usr/bin/env python3
"""
Enhanced script to identify multiple star systems by finding stars with similar names
and parsing separation information to show relationships between stars.
Generates a JSON file with the data for use in the visualization.
"""

import pandas as pd
import re
import json

# Load the star data
data = pd.read_csv('data/stars.csv')

# Dictionary to store systems grouped by base name
systems = {}

# Dictionary for separation information
separations = {}

# Pattern for component identifiers like "A", "B" at the end of names
component_pattern = re.compile(r'(.*)\s([A-Z])$')

# Pattern for separation information like "AB:24 AU" or "AC:14000 AU"
separation_pattern = re.compile(r'([A-Z]{2}):(\d+\.?\d*)')

# Process each star
for idx, row in data.iterrows():
    name = row['Common Name']
    if pd.isna(name):
        continue
        
    # Try to match the pattern for component identification
    match = component_pattern.match(name)
    if match:
        # Found a component of a system
        base_name = match.group(1)  # The name without the component letter
        component = match.group(2)  # The component letter (A, B, C, etc.)
        
        # Add to systems dictionary
        if base_name not in systems:
            systems[base_name] = []
            separations[base_name] = {}
        
        # Store star information
        star_info = {
            'name': name,
            'component': component,
            'distance': row['Distance (ly)'] if not pd.isna(row['Distance (ly)']) else None,
            'class': row['Class'] if not pd.isna(row['Class']) else None,
            'visual_mag': row['Visual Mag'] if not pd.isna(row['Visual Mag']) else None,
            'abs_mag': row['Abs Mag'] if not pd.isna(row['Abs Mag']) else None,
            'color': row['Color'] if not pd.isna(row['Color']) else None
        }
        
        # Add separation information if available
        if not pd.isna(row['Separation (AU)']):
            separation_info = row['Separation (AU)']
            if isinstance(separation_info, str):
                # Look for separation pattern
                sep_matches = separation_pattern.findall(separation_info)
                for pair, distance in sep_matches:
                    # Store the separation information
                    separations[base_name][pair] = float(distance)
                    
                # Store the raw separation string
                star_info['separation'] = separation_info
        
        systems[base_name].append(star_info)

# Prepare visualization data - only include systems with multiple stars
multiple_systems = {}
for system_name, components in systems.items():
    if len(components) > 1:  # Only include actual multiple systems
        # Get distance from first component if available
        distance = components[0]['distance']
        
        # Compile the system information
        system_data = {
            'name': system_name,
            'distance': distance,
            'components': len(components),
            'stars': components,
            'separations': separations.get(system_name, {})
        }
        
        # Add to the multiple systems dictionary
        multiple_systems[system_name] = system_data

# Also create a mapping for each individual star to its system
star_to_system_map = {}
for system_name, system_data in multiple_systems.items():
    for star in system_data['stars']:
        star_name = star['name']
        star_to_system_map[star_name] = {
            'system_name': system_name,
            'component': star['component'],
            'separation': star.get('separation', None),
            'system_components': system_data['components'],
            'system_distance': system_data['distance']
        }

# Print the results
print("Multiple Star Systems (based on naming patterns):")
print("-------------------------------------------------")

for system_name, system_data in sorted(multiple_systems.items(), key=lambda x: x[1]['distance'] if x[1]['distance'] else float('inf')):
    print(f"\n{system_name} System:")
    
    # Get distance if available
    distance = system_data['distance']
    if distance:
        print(f"  Distance: {distance} light years")
        
    print(f"  Components: {system_data['components']}")
    
    # Print component information
    for component in sorted(system_data['stars'], key=lambda x: x['component']):
        class_str = component['class'] if component['class'] else 'Unknown class'
        mag_str = f", Mag: {component['visual_mag']}" if 'visual_mag' in component and component['visual_mag'] is not None else ""
        color_str = f", Color: {component['color']}" if 'color' in component and component['color'] is not None else ""
        
        print(f"    - {component['name']} ({class_str}{mag_str}{color_str})")
        
        # Print separation info if available
        if 'separation' in component and component['separation']:
            print(f"      Separation: {component['separation']}")
    
    # Print a structured separation diagram if we have separation data
    if system_data['separations']:
        print("\n  Separation Diagram:")
        
        # Print each known separation
        for pair, distance in sorted(system_data['separations'].items()):
            # Split the pair (e.g., "AB" -> "A" and "B")
            primary, secondary = pair[0], pair[1]
            
            # Print the separation in a readable format
            print(f"    {primary} -- {distance} AU --> {secondary}")

# Count the total number of multiple star systems
multiple_systems_count = len(multiple_systems)
print(f"\nTotal number of identified multiple star systems: {multiple_systems_count}")

# Export the data to JSON files for visualization
print("\nExporting data to JSON files...")

# Save the multiple star systems data
with open('data/multiple_systems.json', 'w') as f:
    json.dump({
        'systems': list(multiple_systems.values())
    }, f, indent=2)
print("- Multiple star systems data saved to data/multiple_systems.json")

# Save the star-to-system mapping
with open('data/star_systems_mapping.json', 'w') as f:
    json.dump(star_to_system_map, f, indent=2)
print("- Star-to-system mapping saved to data/star_systems_mapping.json")

print("\nData export complete! These files can now be used by the visualization application.")
print("To use them in the application, just run 'python main.py' and select stars that are part of multiple systems.")
print("You can toggle the multiple star system inset view with the 'I' key.")