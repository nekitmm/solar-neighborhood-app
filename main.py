import argparse
from src.data_loader import load_nearby_stars
from src.visualization import StarApp

def main():
    parser = argparse.ArgumentParser(description='20LY - Interactive 3D visualization of stars within 20 light years')
    parser.add_argument('--max-distance', type=float, default=20.0,
                      help='Maximum distance from Sun in light years (default: 20)')
    parser.add_argument('--fullscreen', action='store_true',
                      help='Run in fullscreen mode')
    
    args = parser.parse_args()
    
    # Load star data with the specified max distance
    stars_df = load_nearby_stars(max_distance=args.max_distance)
    
    # Run the app
    print(f"Starting {args.max_distance}LY - 3D Stellar Neighborhood Visualization")
    print("Controls:")
    print("Navigation:")
    print("- WASD/Arrow keys: Pan camera")
    print("- Mouse drag: Rotate view (X/Y axes)")
    print("- Q/E keys: Rotate around Z axis")
    print("- R key: Reset rotation")
    print("- Mouse wheel: Zoom in/out")
    print("- C key: Center view on selected star")
    print("- 0 key: Center on Sun")
    print("- Shift+Click: Set rotation center")
    print("- +/- keys: Adjust render distance")
    
    print("\nVisualization:")
    print("- N: Toggle star names (Sun and Sirius always shown)")
    print("- G: Toggle galactic plane visualization")
    print("- H: Toggle coordinate grid")
    print("- P: Toggle star projections onto galactic plane")
    print("- I: Toggle multiple star system inset view")
    
    print("\nMeasurement and Routes:")
    print("- M: Save distance line from current rotation center to selected star")
    print("- T: Add a star-hopping route between rotation center and selected star")
    print("- Shift+T: Clear all star-hopping routes")
    print("- Backspace: Clear all distance measurements")
    
    print("\nView Management:")
    print("- F1-F5: Save current view to slot 1-5")
    print("- Shift+F1-F5: Load view from slot 1-5")
    print("- F11: Toggle fullscreen mode")
    
    print("\nOther:")
    print("- Shift+P: Pause animation")
    print("- ESC: Quit")
    
    app = StarApp(stars_df, max_distance=args.max_distance, fullscreen=args.fullscreen)
    app.run()

if __name__ == "__main__":
    main()