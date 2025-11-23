"""
Table Image Rendering Utility.

This module handles the visual generation of data tables, including:
1. Converting raw data lists into a Pandas DataFrames
2. Applying high-contrast styling (Dark Mode body, Pink headers) via Plottable.
3. Exporting the final render to an in-memory BytesIO buffer and returning the rendered buffer
"""

import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from plottable import Table, ColumnDefinition

def render_table_image(headers, rows):

    df = pd.DataFrame(rows, columns=headers)

    first_col_name = df.columns[0]

    n_rows, n_cols = df.shape
    # Calculate size dynamically
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
            #uses the first column as index, to remove the default index column given by panda's dataframe
            index_col=first_col_name,
            
            # Global text settings
            textprops={
                'fontsize': 14, 
                'color': 'white',
                'ha': 'center',
                'family': 'sans-serif' # cleaner font
            },
            
            #the table ignore Column Definitions if there's no column of given name. So for nomal league tables, challenger and challenged will be ignored.
            #and for rivals table osu-username's ColumnDefinition will be ignored
            column_definitions=[
                ColumnDefinition(
                    name='osu_username', 
                    textprops={"weight": "bold", "ha": "left"},
                    width = 1.2
                ),
                ColumnDefinition(
                    name="challenger",
                    textprops={"weight": "bold", "ha": "left"},
                    width = 1.2
                ),
                ColumnDefinition(
                    name="challenged",
                    textprops={"weight": "bold", "ha": "left"},
                    width = 1.2
                )
            ],
            
            # Header Style, light pink with white borders
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
            
            # Alternating Backgrounds, grey and black
            odd_row_color='#000000', 
            even_row_color='#222222' 
        )
        #store the plot in ram buffer for performance
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=250, facecolor=fig.get_facecolor())
        #set the buffer's pointer to initial byte
        buf.seek(0)
        return buf
    #in case buffer does not render
    except Exception as e:
        print(f"Error rendering table: {e}")
        return None

    finally:
        # This block runs no matter what, even if the code crashes above, to clean up the fig
        if fig:
            plt.close(fig)