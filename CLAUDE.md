# Project Information for Claude

## Common Commands

### Setup and Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Run the application
python main.py

# Run with a specific maximum distance
python main.py --max-distance 15

```

## Code Style Preferences

- Use PEP 8 formatting standards
- Use numpy-style docstrings
- Use type hints where appropriate
- Prefer explicit imports over wildcard imports
- 4 spaces for indentation
- Maximum line length of 100 characters
- Keep functions focused and under 30 lines when possible

## Project Structure

- `src/`: Source code directory
  - `data_loader.py`: Functions for loading and processing star and solar system data
  - `visualization.py`: Classes for different visualization methods
- `data/`: Directory for additional data files
- `main.py`: Entry point for running the application
- `requirements.txt`: Python dependencies