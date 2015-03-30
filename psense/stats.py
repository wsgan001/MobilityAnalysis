#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 4 Feb. 2015
#-------------------------------------------------------------------------------

import time
from math import sqrt

import pandas as pd

from geopy.distance import distance # VincentyDistance
from psense.util import Point, EPSILON

#-------------------------------------------------------------------------------

def df_to_points(df, tuples=True):
    if tuples:
        points = [(r.lat, r.lng) for i, r in df.iterrows()]
    else:
        points = []
        def build_point(row):
            metadata = row.loc[:"text"].to_dict()
            P = Point((row.lat, row.lng), metadata=metadata)
            points.append(P)
        df.apply(build_point, axis=1)
    return points

def geom_average(points):
    """
    Compute the centroid or geometric average of the points in `df`.

    Runtime: O(n)
    """
    avg = [0, 0]
    for (x, y) in points:
        avg[0] += x
        avg[1] += y
    n = float(len(points))
    avg[0] /= n
    avg[1] /= n
    return tuple(avg)

# alias
geom_mean = geom_average

def geom_median_approx(P, points):
    """
    Apply one iteration of Weiszfeld's algorithm to the old
    appromixation P.

    Runtime: O(n)

    [Based on Gareth Rees' answer of 'Meeting Point problem from interviewstreet.com' in the Code Review Stack Exchange.]
    """
    W = x = y = 0.0
    for Q in points:
        d = distance(P, Q)
        if d != 0:
            w = 1.0 / d.km
            W += w
            x += Q[0] * w
            y += Q[1] * w
    return (x / W, y / W)

def geom_median(points, epsilon=EPSILON, user_id=None):
    """
    Start with the centroid and apply Weiszfeld's algorithm until the
    distance between steps is less than `epsilon`.

    Args:
        points: A list of 2-tuples or Point objects.
        epsilon: tolerance / precision of the result in kilometers.
        user_id: For debugging purposes if `points` is a list of plain tuples
            without user metadata.

    Runtime: o(n^2)

    [Based on Gareth Rees' answer of 'Meeting Point problem from interviewstreet.com' in the Code Review Stack Exchange.]
    """
    P = geom_average(points)
    start = time.time()
    while time.time() < start + sqrt(len(points)) / 2: # set a time limit
        Q = geom_median_approx(P, points)
        if distance(P, Q) < epsilon:
            return Q
        P = Q
    else:
        msg = "Geometric median approximation not converging. Stopping calculation."
        if user_id:
            msg = ("User %s: " % user_id) + msg
        elif isinstance(P, Point):
            msg = ("User %s: " % P["user_id"]) + msg
        print msg
        return Q

def radius(points, center_function=geom_average, center=None):
    C = center if center else center_function(points)
    return max(distance(P, C).km for P in points)

def locality(points, center_function=geom_average, center=None):
    """
    Assuming not all points are equal, returns a closeness measure
    of the set of points.
    """
    C = center if center else center_function(points)
    dts = [distance(P, C).km for P in points]
    return 1 / sum(dts)

#-------------------------------------------------------------------------------

def do_stats(df, join=False):
    stats = []

    for uid, r in df.groupby(level="user_id"):
        p = df_to_points(r)
        avg = geom_average(p)
        med = geom_median(p)
        lc_avg = locality(p, center=avg)
        lc_med = locality(p, center=med)
        avg_radius = radius(p, center=avg)
        med_radius = radius(p, center=med)
        stats.append((uid, lc_avg, lc_med, avg_radius, med_radius))
    stats_df = pd.DataFrame(stats, columns=["user_id", "avg_locality", "med_locality", "radius_avg", "radius_med"]).set_index("user_id")

    if join:
        df = df.join(stats_df)

    return stats_df

#-------------------------------------------------------------------------------

def write_geojson_centers(df, center_function, outpath):
    geojson = '{"type":"FeatureCollection","features":['

    for i, (uid, fr) in enumerate(df.groupby(level=0)):
        points = df_to_points(fr)
        c = center_function(points)
        geojson += '{"type":"Feature","properties":{"number":%s,"id":%s},"geometry":{"type":"Point","coordinates":[%s, %s]}},' % (i, uid, c[1], c[0]) # [lng, lat] layout
    geojson = geojson[:-1] + "]}" # remove trailing comma of last path

    with open(outpath, "wt") as fout:
        fout.write(geojson.encode('utf-8'))
