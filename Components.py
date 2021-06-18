# -*- coding: utf-8 -*-
"""
Created on Sun Jun  6 18:22:30 2021

@author: Haythem
"""

import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc
import dash

from datetime import datetime as dt

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

navbar = dbc.Navbar(
    [
        
            # Use row and col to control vertical alignment of logo / brand
            dbc.Row(
                [
                    dbc.Col([html.Img(src=app.get_asset_url('camion.svg'), height="50px", className="rounded float-left")] ),
                    dbc.Col(dbc.NavbarBrand("Transporter Route", className="layout_title",style = {"font-weight": "normal",
                                                                                                     "font-family": "Trocchi",
                                                                                                      "line-height" : "48px",
                                                                                                      "font-weight": "normal",
                                                                                                      "font-size": "45px"})),     
               
                                            ],
                                            align="center",
                                            no_gutters=True,
                                        ),

                    dbc.Col([html.Img(src=app.get_asset_url('redlean.jfif'), height="50px", className="rounded float-right"  )] ),
        dbc.NavbarToggler(id="navbar-toggler"),
    ],
    className="mb-5",
    color = '#2D3038'
)
html.Div(id="output-data-upload")
task = dbc.Card(
    dbc.CardBody(
        [
            html.H4("Title", className="card-title"),
            html.H6("Card subtitle", className="card-subtitle"),
            html.P(
                "Some quick example text to build on the card title and make "
                "up the bulk of the card's content.",
                className="card-text",    
            ),
            #html.Div(id="output-data-upload"),
            #dbc.CardLink("External link", href="https://google.com"),
        ]
    ),
    style={"width": "100%", },
    className="rounded float-right",
    color = "#e9ecef"
    )