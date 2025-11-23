import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from plottable import Table, ColumnDefinition

def render_table_image(headers, rows):

    df = pd.DataFrame(rows, columns=headers)
    n_rows, n_cols = df.shape
    df = df.set_index('osu_username')

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
            textprops={
                'fontsize': 14, 
                'color': 'white',
                'ha': 'center'
            },
            column_definitions=[
                ColumnDefinition(
                    name="osu_username", # Now this works because we named it in Step 1
                    textprops={"weight": "bold", "ha": "left"},
                    width = 1.2
                ),
            ],
            # Header Box Style (Pink)
            col_label_cell_kw={
                'facecolor': '#FF69B4', 
                'edgecolor': 'white', 
            },
            # Body Box Style (Borders)
            cell_kw={
                'edgecolor': 'white', 
            },
            # FIX 2: Dark Backgrounds so White text is visible
            odd_row_color='#000000',  # Black
            even_row_color='#222222'  # Dark Gray
        )
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=250, facecolor=fig.get_facecolor())
        buf.seek(0)
        return buf

    except Exception as e:
        print(f"Error rendering table: {e}")
        return None

    finally:
        # THIS is the memory leak fix.
        # This block runs no matter what, even if the code crashes above.
        if fig:
            plt.close(fig)