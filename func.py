# -*- coding: utf-8 -*-
"""
Created on Fri Jun  4 01:04:50 2021

@author: Haythem
"""
import pandas as pd 
import pickle
import pandas as pd 
import arcgis
from arcgis.gis import GIS
import datetime
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
