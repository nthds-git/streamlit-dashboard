import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import numpy as np

st.set_page_config(
    page_title="File Inventory Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS for styling with Tailwind-inspired classes
st.markdown("""
    <style>
        /* Main app styling */
        .stApp {
            max-width: 1400px;
            margin: 0 auto;
            background-color: #f9fafb;
        }
        .block-container {
            padding: 3rem 1rem;
            background-color: white;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            margin: 1rem;
        }
        
        /* Typography */
        h1 {
            color: #2563eb;
            margin-bottom: 1.5rem;
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1.2;
        }
        h2 {
            color: #1e40af;
            margin: 1.5rem 0 1rem 0;
            font-size: 1.8rem;
            font-weight: 600;
        }
        h3 {
            color: #374151;
            font-size: 1.5rem;
            margin: 1rem 0;
            font-weight: 600;
        }
        
        /* Tabs styling */
        .stTabs {
            background-color: white;
            padding: 1.25rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background-color: #f3f4f6;
            padding: 0.5rem;
            border-radius: 0.75rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 10px 20px;
            border-radius: 0.5rem;
            margin: 0 4px;
            background-color: transparent;
            transition: all 0.2s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(37, 99, 235, 0.1);
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: white;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        .stTabs [data-baseweb="tab-list"] button {
            font-size: 1rem;
            font-weight: 500;
        }
        
        /* Simple radio button styling */
        .stRadio > label {
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        /* Metric cards */
        .metric-card {
            background-color: #f9fafb;
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            border-left: 4px solid #2563eb;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: #f3f4f6;
            border-radius: 0.5rem;
            padding: 0.75rem 1rem;
            font-weight: 500;
        }
        .streamlit-expanderContent {
            background-color: white;
            border-radius: 0 0 0.5rem 0.5rem;
            padding: 1.25rem;
            border: 1px solid #e5e7eb;
            border-top: none;
        }
        
        /* File uploader */
        .stFileUploader {
            padding: 1.5rem;
            background-color: #f9fafb;
            border-radius: 0.75rem;
            border: 2px dashed #d1d5db;
            margin-bottom: 2rem;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 1.5rem;
            color: #6b7280;
            font-size: 0.875rem;
            border-top: 1px solid #e5e7eb;
            margin-top: 2rem;
        }
        
        /* DataFrames */
        .stDataFrame {
            border-radius: 0.5rem;
            overflow: hidden;
            border: 1px solid #e5e7eb;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.75rem !important;
            font-weight: 700 !important;
            color: #2563eb !important;
        }
        [data-testid="stMetricLabel"] {
            font-weight: 500 !important;
        }
        
        /* Plotly charts */
        .js-plotly-plot {
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            background-color: white;
            padding: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

def normalize_extension(ext: str) -> str:
    """Normalize file extension to lowercase and handle special cases"""
    if pd.isna(ext) or not ext:
        return 'no extension'
    ext = str(ext).lower().strip()
    return ext if ext else 'no extension'

def create_pie_chart(df: pd.DataFrame, values: str, names: str, title: str, threshold_pct: float = 1.0):
    """Create a pie chart with small values grouped into 'Other'"""
    # Calculate total
    total = df[values].sum()
    
    # Calculate percentage for each category
    df = df.copy()
    df['percentage'] = (df[values] / total) * 100
    
    # Format the title with units for storage
    if 'Size' in values:
        if total >= 1024:
            formatted_total = f"{total/1024:.1f} GB"
            title = f"{title} (Total: {formatted_total})"
        else:
            formatted_total = f"{total:.1f} MB"
            title = f"{title} (Total: {formatted_total})"
    
    # Improved algorithm for handling "Other" category
    if len(df) > 8:
        # Sort by percentage descending
        df = df.sort_values('percentage', ascending=False)
        
        # Take top categories that make up 95% of the data or at least top 7 categories
        cumulative_pct = df['percentage'].cumsum()
        main_idx = min(
            max(7, (cumulative_pct < 95).sum() + 1),  # At least top 7, or categories making up 95%
            len(df) - 1  # Don't include all if there are many categories
        )
        
        main_categories = df.iloc[:main_idx].copy()
        other_categories = df.iloc[main_idx:].copy()
        
        if not other_categories.empty:
            # Create 'Other' row
            other_row = pd.DataFrame({
                names: ['Other'],
                values: [other_categories[values].sum()],
                'percentage': [other_categories['percentage'].sum()]
            })
            
            # Combine main categories with 'Other'
            plot_df = pd.concat([main_categories, other_row])
        else:
            plot_df = df
    else:
        plot_df = df  # Use all categories if 8 or fewer
    
    # Sort by value for consistent color assignment
    plot_df = plot_df.sort_values(values, ascending=False)
    
    # Create pie chart with a better color scheme
    fig = px.pie(
        plot_df,
        values=values,
        names=names,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    # Calculate which slices should have text inside vs in legend
    plot_df['show_text'] = plot_df['percentage'] >= 5
    
    # Update traces for better readability
    fig.update_traces(
        textposition=['inside' if show else 'none' for show in plot_df['show_text']],
        textinfo='percent+label',
        textfont=dict(size=12, color='white', family="Arial, sans-serif"),
        marker=dict(line=dict(color='#ffffff', width=1)),
        showlegend=True,
        pull=[0.05 if name != 'Other' and show else 0 for name, show in zip(plot_df[names], plot_df['show_text'])],
        hovertemplate="<b>%{label}</b><br>%{value:,.1f} (%{percent:.1%})<extra></extra>"
    )
    
    # Position legend to the right of the pie
    fig.update_layout(
        title=dict(
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top',
            font=dict(size=18, color='#1e40af', family="Arial, sans-serif")
        ),
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.1,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(0, 0, 0, 0.1)",
            borderwidth=1,
            font=dict(size=12, family="Arial, sans-serif")
        ),
        width=None,
        height=450,
        margin=dict(t=80, r=120, b=20, l=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_toggle_switch(key_suffix: str):
    """Create a simple radio button group"""
    st.markdown("### View Options")
    return st.radio(
        "Group by:",
        options=["File Type", "Extension"],
        horizontal=True,
        key=f"view_toggle_{key_suffix}"
    )

def prepare_data_for_analysis(df: pd.DataFrame, view_option: str):
    """Prepare data for analysis with case-insensitive grouping"""
    df = df.copy()
    
    # Normalize file type to be title case
    df['file_type'] = df['file_type'].str.title()
    
    if view_option == "Extension":
        # Extract and normalize extension
        df['extension'] = df['file_name'].str.extract(r'\.([^.]+)$', expand=False).apply(normalize_extension)
        
        # Get total counts
        summary = df.groupby(['extension', 'file_type']).agg({
            'file_name': 'count',  # total count
            'size_mb': ['mean', 'sum']
        }).reset_index()
        
        # Get duplicate counts
        dupe_counts = df[df.duplicated(subset=['hash'], keep='first')].groupby(['extension', 'file_type']).agg({
            'file_name': 'count'  # duplicate count
        }).reset_index()
        
        # Merge the counts
        summary.columns = ['Extension', 'File Type', 'Total Files', 'Avg Size (MB)', 'Total Size (MB)']
        dupe_counts.columns = ['Extension', 'File Type', 'Duplicate Files']
        
        # Merge total and duplicate counts
        summary = summary.merge(
            dupe_counts,
            on=['Extension', 'File Type'],
            how='left'
        )
        
        # Fill NaN with 0 for files with no duplicates
        summary['Duplicate Files'] = summary['Duplicate Files'].fillna(0).astype(int)
        
        # Calculate original files
        summary['Original Files'] = summary['Total Files'] - summary['Duplicate Files']
        
        summary = summary.sort_values('Total Files', ascending=False)
        
        # Create summary for pie charts (extension only)
        pie_summary = summary.groupby('Extension').agg({
            'Total Files': 'sum',
            'Duplicate Files': 'sum',
            'Original Files': 'sum',
            'Total Size (MB)': 'sum'
        }).reset_index()
        
    else:
        # Get total counts
        summary = df.groupby('file_type').agg({
            'file_name': 'count',  # total count
            'size_mb': ['mean', 'sum']
        }).reset_index()
        
        # Get duplicate counts
        dupe_counts = df[df.duplicated(subset=['hash'], keep='first')].groupby('file_type').agg({
            'file_name': 'count'  # duplicate count
        }).reset_index()
        
        # Merge the counts
        summary.columns = ['File Type', 'Total Files', 'Avg Size (MB)', 'Total Size (MB)']
        dupe_counts.columns = ['File Type', 'Duplicate Files']
        
        # Merge total and duplicate counts
        summary = summary.merge(
            dupe_counts,
            on=['File Type'],
            how='left'
        )
        
        # Fill NaN with 0 for files with no duplicates
        summary['Duplicate Files'] = summary['Duplicate Files'].fillna(0).astype(int)
        
        # Calculate original files
        summary['Original Files'] = summary['Total Files'] - summary['Duplicate Files']
        
        summary = summary.sort_values('Total Files', ascending=False)
        pie_summary = summary
    
    return summary, pie_summary, df

def display_duplicate_stats(df: pd.DataFrame):
    """Display pre-computed duplicate statistics from the inventory"""
    st.markdown("## 🔍 Duplicate File Analysis")
    
    df = df.copy()
    df['file_type'] = df['file_type'].str.title()
    
    total_files = len(df)
    duplicates = df[df.duplicated(subset=['hash'], keep=False)].copy()
    duplicate_files = len(duplicates)
    duplicate_size_mb = duplicates['size_mb'].sum()
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Duplicate Files", f"{duplicate_files:,}")
    with col2:
        st.metric("Duplicate Percentage", f"{(duplicate_files/total_files)*100:.1f}%")
    with col3:
        st.metric("Duplicate Storage", f"{duplicate_size_mb/1024:.2f} GB")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### 📊 Distribution Analysis")
    
    # Get view option before data preparation
    view_option = create_toggle_switch("duplicates")
    
    # Prepare data and get summaries
    summary, pie_summary, df_prepared = prepare_data_for_analysis(duplicates, view_option)
    
    # Display charts using the view_option
    col1, col2 = st.columns(2)
    
    with col1:
        fig_count = create_pie_chart(
            pie_summary,
            values='Total Files',
            names='File Type' if view_option == "File Type" else 'Extension',
            title=f'Duplicate Files by {view_option}',
            threshold_pct=2.0
        )
        st.plotly_chart(fig_count, use_container_width=True)
    
    with col2:
        fig_size = create_pie_chart(
            pie_summary,
            values='Total Size (MB)',
            names='File Type' if view_option == "File Type" else 'Extension',
            title=f'Duplicate Storage by {view_option}',
            threshold_pct=2.0
        )
        st.plotly_chart(fig_size, use_container_width=True)
    
    # Detailed breakdown in an expander
    with st.expander("📋 Detailed Breakdown", expanded=False):
        # Add a header for the grouped columns
        st.markdown("#### File Count Metrics")
        
        # Explicitly set column order before displaying
        if 'Extension' in summary.columns:
            column_order = ['Extension', 'File Type', 'Total Files', 'Duplicate Files', 'Original Files', 
                           'Avg Size (MB)', 'Total Size (MB)']
        else:
            column_order = ['File Type', 'Total Files', 'Duplicate Files', 'Original Files', 
                           'Avg Size (MB)', 'Total Size (MB)']
        
        # Reorder columns to ensure they appear in the desired order
        summary_display = summary[column_order]
        
        st.dataframe(
            summary_display,
            hide_index=True,
            column_config={
                'Extension': st.column_config.TextColumn('Extension'),
                'File Type': st.column_config.TextColumn('File Type'),
                'Total Files': st.column_config.NumberColumn(
                    'Total Files', 
                    format="%d",
                    help="Total number of files in this category"
                ),
                'Duplicate Files': st.column_config.NumberColumn(
                    'Duplicate Files', 
                    format="%d",
                    help="Files that are duplicates of others"
                ),
                'Original Files': st.column_config.NumberColumn(
                    'Original Files', 
                    format="%d",
                    help="Files that are not duplicates"
                ),
                'Avg Size (MB)': st.column_config.NumberColumn('Avg Size (MB)', format="%.2f"),
                'Total Size (MB)': st.column_config.NumberColumn('Total Size (MB)', format="%.2f"),
            }
        )

def display_inventory_analysis(df: pd.DataFrame):
    """Display inventory analysis dashboard"""
    st.markdown("## 📊 File Inventory Overview")
    
    df = df.copy()
    df['file_type'] = df['file_type'].str.title()
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", f"{len(df):,}")
    with col2:
        st.metric("Total Size", f"{df['size_mb'].sum()/1024:.2f} GB")
    with col3:
        st.metric("Unique File Types", f"{df['file_type'].nunique():,}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### 📈 Distribution Analysis")
    
    # Get view option before data preparation
    view_option = create_toggle_switch("inventory")
    
    # Prepare data and get summaries
    summary, pie_summary, df_prepared = prepare_data_for_analysis(df, view_option)
    
    # Display charts using the view_option
    col1, col2 = st.columns(2)
    
    with col1:
        fig_count = create_pie_chart(
            pie_summary,
            values='Total Files',
            names='File Type' if view_option == "File Type" else 'Extension',
            title=f'File Count by {view_option}',
            threshold_pct=1.0
        )
        st.plotly_chart(fig_count, use_container_width=True)
    
    with col2:
        fig_size = create_pie_chart(
            pie_summary,
            values='Total Size (MB)',
            names='File Type' if view_option == "File Type" else 'Extension',
            title=f'Storage Usage by {view_option}',
            threshold_pct=1.0
        )
        st.plotly_chart(fig_size, use_container_width=True)
    
    # Detailed breakdowns in expanders
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("📋 Detailed Breakdown", expanded=False):
            # Add a header for the grouped columns
            st.markdown("#### File Count Metrics")
            
            # Explicitly set column order before displaying
            if 'Extension' in summary.columns:
                column_order = ['Extension', 'File Type', 'Total Files', 'Duplicate Files', 'Original Files', 
                               'Avg Size (MB)', 'Total Size (MB)']
            else:
                column_order = ['File Type', 'Total Files', 'Duplicate Files', 'Original Files', 
                               'Avg Size (MB)', 'Total Size (MB)']
            
            # Reorder columns to ensure they appear in the desired order
            summary_display = summary[column_order]
            
            st.dataframe(
                summary_display,
                hide_index=True,
                column_config={
                    'Extension': st.column_config.TextColumn('Extension'),
                    'File Type': st.column_config.TextColumn('File Type'),
                    'Total Files': st.column_config.NumberColumn(
                        'Total Files', 
                        format="%d",
                        help="Total number of files in this category"
                    ),
                    'Duplicate Files': st.column_config.NumberColumn(
                        'Duplicate Files', 
                        format="%d",
                        help="Files that are duplicates of others"
                    ),
                    'Original Files': st.column_config.NumberColumn(
                        'Original Files', 
                        format="%d",
                        help="Files that are not duplicates"
                    ),
                    'Avg Size (MB)': st.column_config.NumberColumn('Avg Size (MB)', format="%.2f"),
                    'Total Size (MB)': st.column_config.NumberColumn('Total Size (MB)', format="%.2f"),
                }
            )
    
    with col2:
        with st.expander("📁 Top 20 Largest Files", expanded=False):
            largest_files = df.nlargest(20, 'size_mb').copy()
            # Extract extension before filtering columns
            if view_option == "Extension":
                largest_files['extension'] = largest_files['file_name'].str.extract(r'\.([^.]+)$', expand=False).apply(normalize_extension)
                largest_files = largest_files[['file_name', 'file_path', 'extension', 'file_type', 'size_mb', 'hash']]
            else:
                largest_files = largest_files[['file_name', 'file_path', 'file_type', 'size_mb', 'hash']]
            largest_files['size_gb'] = largest_files['size_mb'] / 1024
            
            st.dataframe(
                largest_files,
                hide_index=True,
                column_config={
                    'file_name': st.column_config.TextColumn('File Name'),
                    'file_path': st.column_config.TextColumn('File Path', width='large'),
                    'extension': st.column_config.TextColumn('Extension'),
                    'file_type': st.column_config.TextColumn('File Type'),
                    'size_gb': st.column_config.NumberColumn('Size (GB)', format="%.2f"),
                    'hash': st.column_config.TextColumn('Hash')
                }
            )

def main():
    st.title("🗄️ File Inventory Analyzer")
    st.markdown("""
    <div style="background-color: #f0f9ff; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #3b82f6; margin-bottom: 2rem;">
        <p style="margin: 0; color: #1e40af; font-size: 1rem;">
            Upload your file inventory CSV to analyze its contents and find duplicates.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Styled file uploader
    uploaded_file = st.file_uploader("Upload file_inventory.csv", type=["csv"])
    
    if uploaded_file is not None:
        # Load data
        df = pd.read_csv(uploaded_file)
        
        # Create tabs with better styling
        tab1, tab2 = st.tabs(["📊 Inventory Analysis", "🔄 Duplicate Analysis"])
        
        with tab1:
            display_inventory_analysis(df)
            
        with tab2:
            display_duplicate_stats(df)
    
    # Add footer
    st.markdown("---")
    st.markdown(
        '<div class="footer">A NthDS Demo Environment<br><span style="font-size: 0.75rem; color: #9ca3af;">© 2023 NthDS - All Rights Reserved</span></div>', 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 