import segyio
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SEGYAnalyzer:
    def __init__(self, inventory_df: pd.DataFrame):
        """Initialize the SEGY analyzer with an inventory DataFrame."""
        self.df = inventory_df
        self.segy_files = self.df[
            self.df['file_name'].str.lower().str.endswith(('.sgy', '.segy'))
        ].copy()
        self.missing_files = []
        self.error_files = []
        
    def analyze_segy_files(self, max_traces_per_file: int = None) -> pd.DataFrame:
        """Analyze all SEGY files in the inventory"""
        results = []
        self.missing_files = []
        self.error_files = []
        
        for _, row in self.segy_files.iterrows():
            try:
                file_path = Path(row['file_path'])
                if not file_path.exists():
                    self.missing_files.append(str(file_path))
                    continue
                    
                with segyio.open(file_path, 'r', ignore_geometry=True) as f:
                    # Get basic file info
                    n_traces = len(f.trace)
                    sample_rate = f.bin[segyio.BinField.Interval] / 1000  # Convert to ms
                    
                    # Get inline/crossline ranges
                    if f.bin[segyio.BinField.Traces] > 0:  # Has proper geometry
                        f.mode = segyio.TraceField.offset
                        il_range = (f.ilines[0], f.ilines[-1])
                        xl_range = (f.xlines[0], f.xlines[-1])
                    else:
                        # Try to get from trace headers
                        il_nums = []
                        xl_nums = []
                        trace_limit = min(max_traces_per_file or float('inf'), n_traces)
                        for i in range(trace_limit):
                            il_nums.append(f.header[i][segyio.TraceField.INLINE_3D])
                            xl_nums.append(f.header[i][segyio.TraceField.CROSSLINE_3D])
                        il_range = (min(il_nums), max(il_nums))
                        xl_range = (min(xl_nums), max(xl_nums))
                    
                    # Calculate survey area (rough approximation)
                    il_dist = abs(il_range[1] - il_range[0])
                    xl_dist = abs(xl_range[1] - xl_range[0])
                    survey_area_km2 = (il_dist * xl_dist) / 1_000_000  # Convert to km²
                    
                    result = {
                        'file_path': str(row['file_path']),
                        'file_name': row['file_name'],
                        'size_mb': row['size_mb'],
                        'total_traces': n_traces,
                        'sample_interval_us': sample_rate * 1000,  # Convert ms to μs
                        'inline_min': il_range[0],
                        'inline_max': il_range[1],
                        'crossline_min': xl_range[0],
                        'crossline_max': xl_range[1],
                        'survey_area_km2': survey_area_km2
                    }
                    
                    results.append(result)
                    
            except Exception as e:
                error_msg = f"Error analyzing SEGY file {row['file_path']}: {str(e)}"
                logger.error(error_msg)
                self.error_files.append((str(row['file_path']), str(e)))
                continue
                
        return pd.DataFrame(results)
        
    def get_survey_coverage(self) -> dict:
        """Calculate total survey coverage from all SEGY files"""
        analysis_df = self.analyze_segy_files()
        total_segy_files = len(self.segy_files)
        accessible_files = len(analysis_df)
        missing_files = len(self.missing_files)
        error_files = len(self.error_files)
            
        total_size_gb = self.segy_files['size_mb'].sum() / 1024  # Convert MB to GB
            
        return {
            'total_segy_files': total_segy_files,
            'accessible_files': accessible_files,
            'missing_files': missing_files,
            'error_files': error_files,
            'total_area_km2': analysis_df['survey_area_km2'].sum() if not analysis_df.empty else 0,
            'size_gb': total_size_gb
        }
        
    def get_survey_boundaries(self) -> dict:
        """Get the overall survey boundaries from all SEGY files"""
        analysis_df = self.analyze_segy_files()
        if analysis_df.empty:
            return {}
            
        return {
            'inline_range': (
                analysis_df['inline_min'].min(),
                analysis_df['inline_max'].max()
            ),
            'crossline_range': (
                analysis_df['crossline_min'].min(),
                analysis_df['crossline_max'].max()
            )
        }
    
    def get_error_summary(self) -> pd.DataFrame:
        """Get a summary of files with errors"""
        if not self.error_files:
            return pd.DataFrame()
            
        return pd.DataFrame(self.error_files, columns=['File Path', 'Error'])
    
    def get_missing_files_summary(self) -> pd.DataFrame:
        """Get a summary of missing files"""
        if not self.missing_files:
            return pd.DataFrame()
            
        return pd.DataFrame(self.missing_files, columns=['File Path'])
    
    def get_trace_statistics(self):
        """Compute basic statistics from trace samples."""
        stats = {
            'Statistic': [
                'Mean',
                'Median',
                'Standard Deviation',
                'Min',
                'Max',
                'RMS'
            ],
            'Value': [
                np.mean(self.trace_samples),
                np.median(self.trace_samples),
                np.std(self.trace_samples),
                np.min(self.trace_samples),
                np.max(self.trace_samples),
                np.sqrt(np.mean(np.square(self.trace_samples)))
            ]
        }
        return pd.DataFrame(stats)
    
    def plot_survey_boundary(self):
        """Create a plot showing the survey boundary."""
        il_min, il_max = self.il_range
        xl_min, xl_max = self.xl_range
        
        # Create boundary points
        boundary = go.Scatter(
            x=[xl_min, xl_max, xl_max, xl_min, xl_min],
            y=[il_min, il_min, il_max, il_max, il_min],
            mode='lines+markers',
            name='Survey Boundary',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        )
        
        fig = go.Figure(data=[boundary])
        fig.update_layout(
            title='Survey Boundary',
            xaxis_title='Crossline',
            yaxis_title='Inline',
            showlegend=True,
            width=800,
            height=600
        )
        return fig
    
    def plot_amplitude_distribution(self):
        """Create a histogram of trace amplitudes."""
        # Flatten trace samples and remove extreme outliers
        amplitudes = self.trace_samples.flatten()
        q1, q3 = np.percentile(amplitudes, [25, 75])
        iqr = q3 - q1
        mask = (amplitudes >= q1 - 1.5*iqr) & (amplitudes <= q3 + 1.5*iqr)
        filtered_amplitudes = amplitudes[mask]
        
        fig = px.histogram(
            filtered_amplitudes,
            nbins=100,
            title='Amplitude Distribution',
            labels={'value': 'Amplitude', 'count': 'Frequency'},
            color_discrete_sequence=['#1E88E5']
        )
        fig.update_layout(
            showlegend=False,
            width=800,
            height=400
        )
        return fig 