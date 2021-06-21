# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 23:50:56 2021

@author: Haythem
"""


import datetime

import plotly.graph_objs as go


import dash
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.express as px
from datetime import date

import pandas as pd
from datetime import datetime as dt
import pickle
import arcgis
from arcgis.gis import GIS
import getpass
from IPython.display import HTML

from arcgis import geocoding
from arcgis.features import Feature, FeatureSet
from arcgis.features import GeoAccessor, GeoSeriesAccessor

portal_url = 'https://www.arcgis.com'
#connect to your GIS
user_name = 'Mansour_Haythem_LearnArcGIS5' # '<user_name>'
password = 'redlean123' #'<password>'
my_gis = GIS(portal_url, user_name, password)


model = pickle.load(open('model.pkl', 'rb'))

def cal_pred (df):

    df['new'] = pd.Series([1 for x in range(len(df.index))])
    int_features = df[['new', 'distance', 'speed']]
    final_features = int_features.iloc[:,:].values
    prediction = model.predict(final_features)
    df["Duration"]=prediction
    df["Duration"]= pd.to_datetime(df["Duration"], unit='s').dt.strftime("%H:%M:%S")
    df=df.sort_values(['Round_Name','TourneeId', 'Duration'], ascending=True)

    #prediction=df["Duration"].tolist()
    return df["Duration"]

# calculer le temps de départ :
def cal_depart_time(df):
    
    df["realInfoHasPrepared"]=pd.to_datetime(df["realInfoHasPrepared"], format='%Y-%m-%d %H:%M:%S')
    df["sourceClosureDate"]=pd.to_datetime(df["sourceClosureDate"], format='%Y-%m-%d %H:%M:%S')
    #sort by round Name 
    df['sourceSequence'] = df.groupby(['Round_Name','TourneeId']).cumcount().add(1)
    df["depart_time"]= df.sourceClosureDate.shift(1)
    sourceSequence = df['sourceSequence'].tolist()
    depart_time=df["depart_time"].tolist()
    realInfoHasPrepared=df["realInfoHasPrepared"].tolist()
    for i in range (len(sourceSequence)):
        if sourceSequence[i] == 1 :
            depart_time[i] = realInfoHasPrepared[i]
    return depart_time

#Calculer le temps d'arrivé :
def cal_Arrive_time (df) :
    df['Duration_time']= pd.to_timedelta( df['Duration'])
    df['Arrive_time'] = df['depart_time'] + df['Duration_time']
    return df['Arrive_time']

# Afficher le tableaux des taches finale : 
    
def update_data_df(data_df):
    data_df["Duration"]= cal_pred (data_df)
    data_df["depart_time"]= cal_depart_time(data_df)
    data_df['Arrive_time'] = cal_Arrive_time (data_df)
    data_df.drop(['new' , "Duration_time"], axis=1 , inplace=True )
    return data_df


def routes_process (routes_df, x):
    routes_df = routes_df.loc[routes_df["Date"]  == x]
    routes_df["startTime"]=pd.to_datetime(routes_df["startTime"],format='%Y-%m-%d %H:%M:%S')
    routes_df["endTime"]=pd.to_datetime(routes_df["endTime"], format='%Y-%m-%d %H:%M:%S')
    routes_df["date"]=pd.to_datetime(routes_df["date"], format='%Y-%m-%d %H:%M:%S')
    routes_df["realInfoHasPrepared"]=pd.to_datetime(routes_df["realInfoHasPrepared"],format='%Y-%m-%d %H:%M:%S')
    routes_df["realInfoHasStarted"]=pd.to_datetime(routes_df["realInfoHasStarted"], format='%Y-%m-%d %H:%M:%S')
    routes_df["realInfoHasFinished"]=pd.to_datetime(routes_df["realInfoHasFinished"], format='%Y-%m-%d %H:%M:%S')
    routes_df['count'] = routes_df.groupby('roundName')['roundName'].transform('count')
    routes_df.drop(['sourceHubName'], axis=1 , inplace=True )
    
    routes_df = routes_df[["roundId", "roundName", "startLocation","endLocation","startTime",
                           "endTime", "weight","costPerUnitTime","maxOrders","maxDuration","count"]]
    routes_df.columns = ['ObjectID', 'Name', 'StartDepotName', 'EndDepotName', 'EarliestStartTime', 'LatestStartTime','Capacities','CostPerUnitTime','MaxOrderCount','MaxTotalTime','AssignmentRule']
    
    routes_df["EarliestStartTime"] = routes_df["EarliestStartTime"].astype("int64") / 10 ** 6
    routes_df["LatestStartTime"] = routes_df["LatestStartTime"].astype("int64") / 10 ** 6
    routes_df["Capacities"] = routes_df["Capacities"].astype("int64") 
    routes_df["CostPerUnitTime"] = routes_df["CostPerUnitTime"].astype("int64")
    routes_df["MaxOrderCount"] = routes_df["MaxOrderCount"].astype("int64") 
    routes_df["MaxTotalTime"] = routes_df["MaxTotalTime"].astype("int64") 
    
    return routes_df
def orders_df_process(data, x):
    data = data.loc[data["Date"]  == x]
    orders_df=data.filter(['sourceAddress', "Longitude", "Latitude"], axis=1)
    data=data.reset_index(drop=True)
    orders_df=data.filter(['sourceAddress', "Longitude", "Latitude"], axis=1)
    orders_df.columns = ['Address', "Longitude", "Latitude"]
    return orders_df
def depots_df_process(depots_df,routes_df ):
    depots_df=depots_df.loc[depots_df.sourceHubName.isin(routes_df['EndDepotName'])]

    return depots_df

def out_stops_df_process(depots_df,routes_df, orders_df, data, x ): 
    routes_df = routes_process (routes_df, x)
    #
    routes_fset = arcgis.features.FeatureSet.from_dataframe(routes_df)
    #
    orders_df=orders_df_process(data, x)
    #
    orders_sdf = pd.DataFrame.spatial.from_xy(orders_df, "Longitude", "Latitude")
    orders_sdf = orders_sdf.drop(axis=1, labels=["Longitude", "Latitude"])
    orders_fset = orders_sdf.spatial.to_featureset()
    #
    depots_df = depots_df_process(depots_df,routes_df )
    depots_sdf = pd.DataFrame.spatial.from_xy(depots_df, "Longitude", "Latitude")
    depots_sdf = depots_sdf.drop(axis=1, labels=["Longitude", "Latitude"])
    depots_sdf=depots_sdf.rename(columns={'sourceHubName':'Name'})
    depots_fset = depots_sdf.spatial.to_featureset()
    today = datetime.datetime.now()
    from arcgis.network.analysis import solve_vehicle_routing_problem
    results = solve_vehicle_routing_problem(orders= orders_fset,
                                            depots = depots_fset,
                                            routes = routes_fset, 
                                            save_route_data='true',
                                            populate_directions='true',
                                            travel_mode="Driving Time",
                                            default_date=today)
    out_stops_df = results.out_stops.sdf
    out_stops_df = out_stops_df[['Name','RouteName','Sequence','ArriveTime','DepartTime', 'SnapX', 'SnapY', 'FromPrevTravelTime', 'FromPrevDistance']].sort_values(by=['RouteName','Sequence'])
    out_stops_df['new'] = pd.Series([1 for x in range(len(out_stops_df.index))])
    out_stops_df['speed'] = (out_stops_df.FromPrevDistance/(out_stops_df.FromPrevTravelTime/60))
    out_stops_df.loc[(out_stops_df.SnapX == 0 ),'speed']= 0
    out_stops_df.loc[(out_stops_df.FromPrevTravelTime == 0 ),'speed']= 0
    #
    out_stops_df["FromPrevTravelTime"]= pd.to_datetime(out_stops_df["FromPrevTravelTime"], unit='m').dt.strftime("%H:%M:%S")
    int_features = out_stops_df[['new', 'FromPrevDistance', 'speed']]
    final_features = int_features.iloc[:,:].values
    prediction = model.predict(final_features)
    out_stops_df["Duration"]=prediction
    out_stops_df.loc[(out_stops_df.SnapX == 0 ),'Duration']= 0
    out_stops_df["Duration"]= pd.to_datetime(out_stops_df["Duration"], unit='s').dt.strftime("%H:%M:%S")
    out_stops_df['Duration_time']= pd.to_timedelta( out_stops_df['Duration'])
    out_stops_df['Duration_trajet']= pd.to_timedelta( out_stops_df['FromPrevTravelTime'])
    out_stops_df['Temps du service'] = out_stops_df['Duration_time'] - out_stops_df['Duration_trajet']
    out_stops_df['Arrive_time'] = out_stops_df['DepartTime'] + out_stops_df['Duration_time']
    out_stops_df.drop(['new' , "Duration_time", "ArriveTime"], axis=1 , inplace=True )
    
    return (out_stops_df)






app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])
server = app.server
app.title = "DASHBOARD"

#import location data 
data_df = pd.read_csv("data.csv")
data_df=data_df.rename(columns={'roundName':'Round_Name'})
data_df=data_df.rename(columns={'roundId':'TourneeId'})
routes_df = pd.read_csv('routes.csv')
depots_df = pd.read_csv('depots_df.csv')
x = "2021-03-20"

orders_df = orders_df_process(data_df, x)




colors = {"graphBackground": "#F5F5F5", "background": "#ffffff", "text": "#000000"}
mapbox_access_token = "pk.eyJ1IjoiaGF5dGhlbS1tYW5zb3VyIiwiYSI6ImNrcHB6bTB2MzBlb3IydnM0bnRyZzl1NXAifQ.4Yms3o7MHgDjxI5AAjNT9Q"




def update_depots_df(depots_df):

    table = html.Div(
            [
                dash_table.DataTable(
                    data=depots_df.to_dict("rows"),
                    columns=[{"name": i, "id": i} for i in depots_df.columns],
                    page_size=12,
                    style_as_list_view=True,
                    style_cell={'textAlign': 'left','backgroundColor': '#2D3038','padding': '1rem'},
                    style_table={'height': '30rem','overflowY': 'auto'},
                ),
                html.Hr(),

            ]
        )
    return table




def update_figure(depots_df):

    locations=[go.Scattermapbox(
                    lon = pd.Series(depots_df['Longitude'], dtype="string").tolist(),
                    lat = pd.Series(depots_df['Latitude'], dtype="string").tolist(),
                    mode='markers',
                    marker=go.scattermapbox.Marker(size=14),
                    unselected={'marker' : {'opacity':1}},
                    selected={'marker' : {'opacity':0.5, 'size':25}},
                    hoverinfo='text',
                    hovertext=depots_df['sourceHubName'],
    )]

    # Return figure
    return {
        'data': locations,
        'layout': go.Layout(
            autosize=True,
            margin=go.layout.Margin(l=0, r=0, t=0, b=0),
            showlegend=False,
            modebar=None,
            uirevision= 'foo', #preserves state of figure/map after callback activated
            clickmode= 'event+select',
            hovermode='closest',
            hoverdistance=5,
            height = 300,
            paper_bgcolor="#2D3038",
            plot_bgcolor="#2D3038",
            mapbox=dict(
                accesstoken=mapbox_access_token,
                bearing=100,
                style='open-street-map',
                center=dict(
                   lat=48.751824,
                   lon=2.362877,
                ),
                pitch=40,
                zoom=10
            ),
            font=dict(
            size=10,
            color="#95969A"
            )
        )
    }

"""@app.callback(
    Output("output-out_stops_df-upload", "children"),
    Input('date-picker', 'date'),
)
def update_out_stops_df(date_value):
    data_df = pd.read_csv("data.csv")
    data_df=data_df.rename(columns={'roundName':'Round_Name'})
    data_df=data_df.rename(columns={'roundId':'TourneeId'})
    routes_df = pd.read_csv('routes.csv')
    depots_df = pd.read_csv('depots_df.csv')
    if date_value is not None:
        date_object = date.fromisoformat(date_value)
        date_string = date_object.strftime('%Y-%m-%d')
        orders_df = orders_df_process(data_df, date_string)
        out_stops_df= out_stops_df_process(depots_df,routes_df, orders_df, data_df, date_string )
    table = html.Div(
            [
                dash_table.DataTable(
                    data=out_stops_df.to_dict("rows"),
                    columns=[
                        {'id': c, 'name': c, 'editable': (c == 'Duration')}
                        for c in out_stops_df.columns
                    ],
                    
                    page_size=6,
                    style_as_list_view=True,
                    style_cell={'textAlign': 'left','backgroundColor': '#2D3038','padding': '1rem'},
                    style_cell_conditional=[{
                                                'if': {'column_id': 'Duration'},
                                                'backgroundColor': '#23262E',
                                                'textAlign': 'left'
                                            }],
                    style_table={'height': '30rem','overflowY': 'auto'},
                ),
                html.Hr(),

            ]
        )
    return table"""



chart = html.Div([
    html.P("Sélectionner un variable :" ,className="text-nowrap" ),
    dcc.Dropdown(
        id='names', 
        value='Round_Name', 
        options=[{'value': x, 'label': x} 
                 for x in ['Round_Name', 'Expediteur', 'ID_de_la_tache','metadataFACTURATION', ]],
        clearable=False,
    ),       
])
@app.callback(
    Output("pie-chart", "figure"), 
    [Input("names", "value"), 
     Input('date-picker', 'date'),])
def generate_chart(names,  date_value):
    data_df = pd.read_csv("data.csv")
    data_df=data_df.rename(columns={'roundName':'Round_Name'})
    data_df=data_df.rename(columns={'roundId':'TourneeId'})
    if date_value is not None:
        date_object = date.fromisoformat(date_value)
        date_string = date_object.strftime('%Y-%m-%d')
        data_df = data_df.loc[data_df["Date"]  == date_string]
    fig = px.pie(data_df, names=names)
    fig.update_layout(paper_bgcolor='#2D3038',
                      margin=go.layout.Margin(l=10, r=0, t=0, b=0),
                      font=dict(
                                size=10,
                                color="#95969A"
                            )),
    
    return fig

# Build App
#app = JupyterDash(external_stylesheets=[dbc.themes.SLATE])


@app.callback(
    Output("output-map-upload", "figure"),
    Input('date-picker', 'date'),
)
def update_map_tasks(date_value):
    
    data_df = pd.read_csv("data.csv")
    data_df=data_df.rename(columns={'roundName':'Round_Name'})
    data_df=data_df.rename(columns={'roundId':'TourneeId'})
    if date_value is not None:
        date_object = date.fromisoformat(date_value)
        date_string = date_object.strftime('%Y-%m-%d')
        data_df = data_df.loc[data_df["Date"]  == date_string]
    locations=[go.Scattermapbox(
                    lon = pd.Series(data_df['Longitude'], dtype="string").tolist(),
                    lat = pd.Series(data_df['Latitude'], dtype="string").tolist(),
                    mode='markers',
                    marker=go.scattermapbox.Marker(size=14),
                    unselected={'marker' : {'opacity':1}},
                    selected={'marker' : {'opacity':0.5, 'size':25}},
                    hoverinfo="lat+lon+text",
                    hovertext=data_df['Round_Name'],
    )]

    # Return figure
    return {
        'data': locations,
        'layout': go.Layout(
            autosize=True,
            margin=go.layout.Margin(l=0, r=0, t=0, b=0),
            showlegend=False,
            modebar=None,
            uirevision= 'foo', #preserves state of figure/map after callback activated
            clickmode= 'event+select',
            hovermode='closest',
            hoverdistance=2,
            height = 320,
            mapbox=dict(
                accesstoken=mapbox_access_token,
                bearing=25,
                style='open-street-map',
                center=dict(
                   lat=48.751824,
                   lon=2.362877,
                ),
                pitch=40,
                zoom=15
            ),
        )
    }

app.layout = dbc.Container([
    dbc.Card(
        dbc.CardBody([
            #header :
             dbc.CardHeader([
                  html.Div(
                    #className="navbar navbar-dark bg-dark",
                    id="header",
                    children=[
                        html.Img(id="logo", src=app.get_asset_url("redlean.jfif"),className="rounded float-right"),
                        html.Img(id="logo-1", src=app.get_asset_url("camion.svg"), className="rounded float-left"),
                        html.H4(children="Transporter Route", className="text-nowrap"),
            ],
        ),
            ],style = {"width" : "100%", "backgroundColor": "#2D3038"}), 
            html.Br(),
            
            dbc.Row([
                # espace de commannde :
                    dbc.Col([
                       dbc.Col([
                           #selection date :
                           dbc.Col([dbc.Row([   
                                                dbc.Col([html.P("Sélectionner une date :", className="text-nowrap"  ),
                                                dcc.DatePickerSingle(
                                                id="date-picker",
                                                min_date_allowed=dt(2021, 1, 1),
                                                max_date_allowed=dt(2021, 3, 31),
                                                initial_visible_month=dt(2021, 1, 1),
                                                date=dt(2021, 1, 1).date(),
                                                display_format="MMMM D, YYYY",
                                            )])]),  
                                    ], style = { "padding": "1rem","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px"}),
                           html.Br(),
                           
                           dbc.Col([dbc.Row([dbc.Col([ chart ])]),  
                                    html.Br(),
                                    dbc.Row([dbc.Col([dcc.Graph(id="pie-chart", config={'displayModeBar': False} )],)]), ], style = { "padding": "1rem","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px"}),
                           html.Br(),
                             dbc.Col([dbc.Row([dbc.Col([html.P("La distance parcourue par le livreur par heure :", className="text-nowrap" )])]),
                                               dbc.Col([dbc.Col([dcc.Graph(id="output-update_graphs", config={'displayModeBar': False})],style = {"marginTop": "1rem"})])], style = {"padding": "1rem","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px", 'height': '58.3rem'}),
                       ],style = {"padding": "2rem",
                                 "borderRadius": "2px",
                                 "backgroundColor": "#2D3038",
                                 "borderColor" : "#53555B",
                                 "boxShadow" : "0px 1px 3px",
                                 'height':'148rem' })],width=4),
                # visualisation
                    dbc.Col([
                         dbc.Col([
                             # map tasks
                            dbc.Col([dbc.Row([dbc.Col([html.P("Carte montre l'emplacement des Préstations  :", className="text-nowrap" )])]), 
                                             html.Br(),
                                             dbc.Col([dbc.Col([dcc.Graph(id="output-map-upload", config={'displayModeBar': False})])])], style = { "padding": "1rem","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'50rem' }),
                            html.Br(),
                            #tableau optimale : 
                            dbc.Col([dbc.Row([dbc.Col([html.P("Tableau des Routes Optimales  :", className="text-nowrap" )]),]), 
                                              html.Br(),  
                                              dbc.Col([html.Div(update_depots_df(depots_df))])], style = { "padding": "1rem","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'45rem' }),
                            html.Br(),
                            #tableau tournées : 
                            dbc.Col([dbc.Row([dbc.Col([html.P("Tableau des Tournées:",className="text-nowrap" )]),]), 
                                              html.Br(),  
                                              dbc.Col([html.Div(id='output-route-upload')])], style = { "padding": "1rem","borderColorT" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'43.5rem' }),
                            #dbc.Col([html.Div(id='output-out_stops_df-upload')]) 
                       
                ],style = {"padding": "2rem",
                            "borderRadius": "2px",
                            "backgroundColor": "#2D3038",
                            "borderColor" : "#53555B",
                            "boxShadow" : "0px 1px 3px",
                            'height':'148rem' })], width=8),
            ], align='center'), 
            html.Br(),
            dbc.Row([
                
                dbc.Col([
                    dbc.Col([
                        dbc.Col([
                            dbc.Col([dbc.Col([html.P("Tableau des Préstations :",className="text-nowrap" )])]),
                            html.Br(),
                            dbc.Col([dbc.Col([html.Div(id='output-data-upload')], style={"borderColor" : "#2D3038"})])
                            ] , style = { "padding": "1rem","backgroundColor": "#2D3038","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'50rem' })
                        ], style = { "padding": "2rem","backgroundColor": "#2D3038","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'55rem' })
                ], width=8),
                #map dépots :
                dbc.Col([
                    dbc.Col([
                        dbc.Col([
                            dbc.Col([dbc.Col([html.P("L'emplacement des Dépots :", className="text-nowrap" )])]),
                            html.Br(),
                            dbc.Col([dbc.Col([dcc.Graph(figure=update_figure(depots_df), config={'displayModeBar': False})])], style = {"height" : "40rem" ,"display": "flex" })
                            ], style = { "padding": "1rem","backgroundColor": "#2D3038","borderColor" : "#53555B", "boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'50rem' })
                        ], style = { "padding": "2rem","boxShadow" : "0px 1px 3px","borderRadius": "2px",'height':'55rem',"backgroundColor": "#2D3038","borderColor" : "#53555B" })
                ], width=4),
                
                
                ],style = {}, align='center')      
        ]), color = '#23262E', style = {"padding": "1%"}
    )
], fluid=True)
    



@app.callback(
    Output("output-data-upload", "children"),
    Input('date-picker', 'date'),
)


def update_table(date_value,):
    table = html.Div()
    data_df = pd.read_csv("data.csv")
    data_df=data_df.rename(columns={'roundName':'Round_Name'})
    data_df=data_df.rename(columns={'roundId':'TourneeId'})
    data_df= update_data_df(data_df)
    if date_value is not None:
        date_object = date.fromisoformat(date_value)
        date_string = date_object.strftime('%Y-%m-%d')
        data_df = data_df.loc[data_df["Date"]  == date_string]
        
        table = html.Div(
            [
                dash_table.DataTable(
                    data=data_df.to_dict("rows"),
                    sort_action='native',
                    columns=[
                        {'id': c, 'name': c, 'editable': (c == 'Duration')}
                        for c in data_df.columns
                    ],
                    
                    page_size=8,
                    style_as_list_view=True,
                    style_cell={'textAlign': 'left','backgroundColor': '#2D3038','padding': '0.9rem', 'textOverflow': 'ellipsis'},
                    style_cell_conditional=[{
                                                'if': {'column_id': 'Duration'},
                                                'backgroundColor': '#23262E',
                                                'textAlign': 'left'
                                            }],
                    style_table={'height': '37.5rem','overflowY': 'auto'},
                ),
                html.Hr(),

            ]
        )

    return table

@app.callback(
    Output("output-route-upload", "children"),
     Input('date-picker', 'date'),
)


def update_routes(date_value):

    table1 = html.Div()
    routes_df = pd.read_csv('routes.csv')
    if date_value is not None:
        date_object = date.fromisoformat(date_value)
        date_string = date_object.strftime('%Y-%m-%d')
        routes_df = routes_df.loc[routes_df["Date"]  == date_string]


        table1 = html.Div(
            [
                dash_table.DataTable(
                    data=routes_df.to_dict("rows"),
                    columns=[{"name": i, "id": i} for i in routes_df.columns],
                    style_as_list_view=True,
                    style_cell={'textAlign': 'left','backgroundColor': '#2D3038','padding': '1rem'},
                    style_table={'height': '200px','overflowY': 'auto'},
                ),
                html.Hr(),
            ] 
        )

    return table1
@app.callback(
    Output("output-update_graphs", "figure"),
     Input('date-picker', 'date'),
)
def update_graph(date_value):
    x = []
    y = []
    data_df = pd.read_csv("data.csv")
    data_df=data_df.rename(columns={'roundName':'Round_Name'})
    data_df=data_df.rename(columns={'roundId':'TourneeId'})
    data_df= update_data_df(data_df)
    if date_value is not None:
        date_object = date.fromisoformat(date_value)
        date_string = date_object.strftime('%Y-%m-%d')
        data_df = data_df.loc[data_df["Date"]  == date_string] 
        data_df['pickup_hour'] = data_df.depart_time.dt.hour
        x=data_df['pickup_hour']
        y=data_df['distance'] 

    fig = go.Figure(
    data=[go.Bar(x=x, y=y)],

    
    )
    fig.update_layout(
    margin=go.layout.Margin(l=0, r=0, t=0, b=0),
    xaxis_title="heure",
    yaxis_title="Distance(km)",
    legend_title="Legend Title",
    plot_bgcolor = "#2D3038",
    paper_bgcolor= "#2D3038",
    height = 400,
    font=dict(
        size=10,
        color="#95969A"
    )
    )
    return fig

if __name__ == "__main__":
    app.run_server(port=7000, debug=True)

