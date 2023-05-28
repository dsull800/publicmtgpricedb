import os
import sys

sys.path.append(os.getcwd())
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
# from scripts.analyze import get_namerows
from dash import dash_table

# namerows = get_namerows()

layout = dbc.Container(id="onload", children=[
    dbc.Row([dbc.Col(dcc.Dropdown(
        id="graphstyle",
        options=[{"label": lab, "value": val}
                 for (lab, val) in
                 [('Ebay Price', 'MINAVGMED'), ('Goatbot Price', 'price0'), ('% Field in Modern', 'modratio'),
                  ('% Field in Pioneer', 'pioratio'), ('% Field in Standard', 'standratio')]],
        value='MINAVGMED',
        clearable=False,
        style={'width': '100%', 'display': 'inline-block', 'font-size': '20px', 'padding': '0px',
               'box-shadow': 'inset 0em 1.8em Cyan'}
    ))]),
    dbc.Row([dbc.Col(dcc.Dropdown(
        id="ticker",
        value='Thoughtseize',
        clearable=False,
        style={'width': '100%', 'display': 'inline-block', 'font-size': '20px', 'padding': '0px',
               'box-shadow': 'inset 0em 1.8em LightCyan'}
    ))]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="time-series-chart",
                          ),
                style={
                    'height': '83vh',
                },
                width=9),
        dbc.Col([html.Img(id="scryfallimg",
                          height='100%', width='100%',
                          style={
                              'margin-left': 'auto',
                              'margin-right': 'auto',
                              'display': 'block',
                              'object-fit': 'contain',
                          }
                          ),
                 dcc.Loading(dash_table.DataTable(id='transaction-table',
                                                  style_cell={'textAlign': 'left',
                                                              'font-size': '20px',
                                                              'overflow': 'hidden',
                                                              'textOverflow': 'ellipsis', },
                                                  style_header={
                                                      'backgroundColor': 'white',
                                                      'fontWeight': 'bold',
                                                      'font-size': '20px'
                                                  },
                                                  style_table={'overflowX': 'auto',
                                                               'margin-top': '28%'},
                                                  ))],
                width=3)
    ],
    ),
],
    fluid=True
)
