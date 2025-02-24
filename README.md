# Streamlit SEGY Analyzer

A Streamlit-based web application for analyzing and visualizing SEGY seismic data files.

## Features

- Interactive visualization of SEGY file contents
- Survey geometry analysis
- File size and trace count statistics
- Area calculations and boundary visualization
- Interactive charts and graphs

## Installation

1. Ensure you have Python 3.13+ installed
2. Clone this repository
3. Install dependencies using `uv`:

```bash
uv venv
uv pip install -e .
```

## Usage

To run the Streamlit app, you can use the provided shell script:

```bash
./run_app.sh
```

Or run it manually with:

```bash
PYTHONPATH=$PYTHONPATH:src streamlit run src/streamlit_segy/gui/app.py
```

The interface provides:
1. File upload capability for SEGY files
2. Basic statistics about your files
3. Interactive visualizations:
   - Survey coverage statistics
   - File size distributions
   - Survey area visualizations
   - Detailed SEGY information

## Development

To set up the development environment:

```bash
uv venv
uv pip install -e ".[test,lint]"
```

Run tests:
```bash
pytest tests/
```

Run linting:
```bash
ruff check .
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
