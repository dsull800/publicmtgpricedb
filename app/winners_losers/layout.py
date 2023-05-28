import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash import dash_table

tooltip_data = []
PAGE_SIZE = 20

layout = dbc.Container([
    dbc.Row(dbc.Col(dcc.Dropdown(
        id="worl",
        options=[{"label": x, "value": x}
                 for x in ['Winners', 'Losers']],
        value='Winners',
        clearable=False,
        style={'width': '100%', 'display': 'inline-block', 'font-size': '20px', 'padding': '0px',
               'box-shadow': 'inset 0em 1.8em Cyan'}
    ), width=True)),
    dbc.Row(dbc.Col(dash_table.DataTable(
        id='datatable-paging-page-count',
        columns=[
            {"name": i, "id": i} for i in ["cardname", "slope"]
        ],
        editable=False, tooltip_data=tooltip_data,
        page_current=0,
        page_size=PAGE_SIZE,
        page_action='custom',
        style_cell={'textAlign': 'right',
                    'font-size': '20px'},
        style_cell_conditional=[
            {
                'if': {'column_id': 'Region'},
                'textAlign': 'right'
            }
        ],
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'font-size': '20px'
        }, css=[{
            'selector': '.dash-tooltip img',
            'rule': '''
               display: block;
               margin-left: auto;
               margin-right: auto;
               width: 100%;
               height: 100%;
               object-fit: contain;
               border-style: hidden;
        '''
        }, {'selector': '.dash-tooltip',
            'rule': '''
               margin-left: auto;
               margin-right: auto;
               width: 50%;
               height: 50%;
               object-fit: scale-down;
               border-style: hidden;
        '''

            }],
        tooltip_delay=0,
        tooltip_duration=None
    ), width=True)),
], fluid=True)
