"""
Table Image Rendering Utility.

This module handles the visual generation of data tables using Matplotlib and Plottable.
It converts raw data into high-contrast, stylized PNG images suitable for Discord.

Features:
1. Converts raw lists into Pandas DataFrames.
2. Applies custom styling (Dark Mode body, Pink headers).
3. Exports the result to an in-memory BytesIO buffer.
"""

import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from plottable import Table, ColumnDefinition
from typing import List, Tuple, Any

"""
Functions in this module:
1. render_table_image(headers: List[str], rows: List[Tuple[Any, ...]]) -> BytesIO | None
"""

def render_table_image(headers: List[str], rows: List[Tuple[Any, ...]]) -> BytesIO | None:
    """
    Renders a list of data rows into a stylized PNG table image.

    This function creates a Pandas DataFrame from the input data, formats it using
    Plottable with a dark-theme aesthetic, and saves the resulting plot to an 
    in-memory buffer.

    Args:
        headers (List[str]): A list of strings representing the column names.
        rows (List[Tuple[Any, ...]]): A list of tuples, where each tuple represents a row of data.

    Returns:
        BytesIO | None: A memory buffer containing the PNG image if successful, 
                        or None if rendering fails.
    """
    df = pd.DataFrame(rows, columns=headers)

    # Use the first column as the index (e.g., Rank or ID)
    first_col_name = df.columns[0]

    n_rows, n_cols = df.shape
    
    # Calculate figure size dynamically based on data volume
    fig_width = n_cols * 3
    fig_height = n_rows * 0.6 + 1
    
    # Initialize fig to None so the finally block is safe
    fig = None 

    try:
        # Create the figure
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        
        fig.set_facecolor('black')
        ax.axis('off')

        Table(
            df,
            ax=ax,
            # Uses the first column as index to remove the default Pandas index column
            index_col=first_col_name,
            
            # Global text settings
            textprops={
                'fontsize': 14, 
                'color': 'white',
                'ha': 'center',
                'family': 'sans-serif' # Cleaner font choice
            },
            
            # Column-specific definitions.
            # Plottable ignores definitions if the column name doesn't exist in the df.
            # This allows us to have one definition list for both 'Rivals' and 'League' tables.
            column_definitions=[
                ColumnDefinition(
                    name='osu_username', 
                    textprops={"weight": "bold", "ha": "left"},
                    width=1.2
                ),
                ColumnDefinition(
                    name="challenger",
                    textprops={"weight": "bold", "ha": "left"},
                    width=1.2
                ),
                ColumnDefinition(
                    name="challenged",
                    textprops={"weight": "bold", "ha": "left"},
                    width=1.2
                )
            ],
            
            # Header Style: Light pink with white borders
            col_label_cell_kw={
                'facecolor': '#FF69B4', 
                'edgecolor': 'white', 
                'linewidth': 1.5,   
            },
            
            # Body Style
            cell_kw={
                'edgecolor': 'white', 
                'linewidth': 1.5    
            },
            
            # Alternating Backgrounds: Black and Dark Grey
            odd_row_color='#000000', 
            even_row_color='#222222' 
        )

        # Store the plot in a RAM buffer for performance (avoids disk I/O)
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=250, facecolor=fig.get_facecolor())
        
        # Reset the buffer's pointer to the beginning so it can be read
        buf.seek(0)
        return buf

    except Exception as e:
        print(f"Error rendering table: {e}")
        return None

    finally:
        # Ensure the figure is closed to free up memory, even if the render crashed
        if fig:
            plt.close(fig)