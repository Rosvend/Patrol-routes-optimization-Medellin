from .default_router import PoliceRouter
from .prediction.simple_wrapper import SimpleModelWrapper
from argparse import ArgumentParser
from config_test import ORS_KEY, MODEL_PATH
from datetime import datetime
from operator import itemgetter
from os.path import exists
from random import choices
from shapely import LineString
import geopandas as gpd
import numpy as np
import pandas as pd

MAX_STATIONS = 4
MAX_ROUTES = 4
ROUTE_LENGTH_WEIGHT = -0.1
ROUTE_LENGTHVAR_WEIGHT = -0.02
SCALER = 1000
RESULTS_FILE = "evaluation_results.csv"
TIMESTAMP_FORMAT = "%y-%m-%d %H:%M:%S"

def mark_emptyroutes(points: list):
    if len(points) > 1:
        return LineString(points)
    return None

def evaluate_routes(result: dict):
    """Return the score of a given result for route computing."""
    areas = gpd.GeoDataFrame.from_features(result["hotareas"])
    routes = [mark_emptyroutes(route) for route in result["routes"]]
    route_lengths = [route.length if route is not None else 0 for route in routes]
    length_cv = np.std(route_lengths) / np.mean(route_lengths)

    return SCALER * (ROUTE_LENGTHVAR_WEIGHT * length_cv**2 + (sum(
        ((areas.intersection(route).length * areas["probability"]).sum()
        / route.length
        + ROUTE_LENGTH_WEIGHT * route.length)
        for route in routes if route is not None
    ) / len(routes)))

def evaluate_router(router: PoliceRouter, **kwargs):
    station_ids = choices(range(len(router._stations)), k=MAX_STATIONS)
    scores = [0 for _ in range(MAX_ROUTES)]
    
    for id in station_ids:
        for n in range(MAX_ROUTES):
            scores[n] += evaluate_routes(router.compute_routes(id, n + 1, **kwargs))
    return scores

if __name__ == "__main__":
    parser = ArgumentParser(
        prog='evaluate.py',
        description='Evaluate the performance of the routing algorithm'
    )
    parser.add_argument('-s', '--save', action='store_true', help=f'Store the results in {RESULTS_FILE}')
    args = parser.parse_args()

    router = PoliceRouter(
        ORS_KEY, SimpleModelWrapper(MODEL_PATH)
    )
    results = evaluate_router(router)

    if args.save:
        if exists(RESULTS_FILE):
            past_results = pd.read_csv(RESULTS_FILE)
        else:
            past_results = pd.DataFrame(columns=['timestamp',
                *(f"score_{n+1}" for n in range(MAX_ROUTES))
            ])
        past_results.loc[len(past_results)] = \
            [datetime.strftime(datetime.now(), TIMESTAMP_FORMAT)] \
            + results
        past_results.to_csv(RESULTS_FILE, index=False)
       
    else:
        print(results)
