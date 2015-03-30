#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 9 Feb. 2015
# ------------------------------------------------------------------------------

import sys
import inspect

from operator import itemgetter
from copy import deepcopy
from pprint import pformat
import datetime as dt
from math import cos, sin, acos

import pandas as pd
import numpy as np

from geopy.distance import Distance, VincentyDistance, GreatCircleDistance
from geopy.geocoders import Nominatim
from geopy.units import radians

EPSILON = 1e-4 # 1m

# Bearing (in degrees)
NORTH = 0.0
EAST = 90.0
SOUTH = 180.0
WEST = -90.0

# ------------------------------------------------------------------------------

def truncate(string, width=10):
    if len(string) > width:
        string = string[:width-4] + '...' + string[-1]
    return string

# Tracer for callables
def getcallables(module):
    c = []
    for x in inspect.getmembers(module):
        if inspect.isclass(x[1]):
            c += [m[0] for m in inspect.getmembers(x[1], predicate=inspect.ismethod)]
        elif inspect.isfunction(x[1]):
            c.append(x[0])
    return c

def tracerecip(module):
    c = [m for m in getcallables(module) if m not in ["__getattr__", "__len__"]]
    def tracefunc(frame, event, arg, indent=[0]):
        """Print function calls on the fly"""
        if event == "call":
            if frame.f_code.co_name in c:
                indent[0] += 2
                print "-" * indent[0] + "> call function", frame.f_code.co_name, "line", frame.f_lineno
        elif event == "return":
            if frame.f_code.co_name in c:
                print "<" + "-" * indent[0], "exit function", frame.f_code.co_name
                indent[0] -= 2
        return tracefunc
    return tracefunc

def settrace(module):
    sys.settrace(tracerecip(module))

# ------------------------------------------------------------------------------

def bbox_from_name(name):
    """Get the bounding box of a place by its name."""
    geolocator = Nominatim() # OpenStreetMaps locator
    location = geolocator.geocode(name)
    return location.raw['boundingbox']

def get_bbox(df):
    north = df['lat'].max() + 1e-15
    south = df['lat'].min()
    east = df['lng'].max() + 1e-15
    west = df['lng'].min()
    return [west, south, east, north]

def bound(df, bbox):
    W, S, E, N = bbox
    return df[(df.lng >= W) & (df.lng < E)
            & (df.lat >= S) & (df.lat < N)]

def in_bounds(P, bbox):
    W, S, E, N = bbox
    return (S <= P[0] < N and W <= P[1] < E)

# ------------------------------------------------------------------------------

def get_timespan(df):
    return (df.created_at.min(), df.created_at.max() + dt.timedelta(microseconds=1))

def bound_time(df, timespan):
    begin, end = timespan
    return df[(begin <= df.created_at < end)]

def in_timespan(P, timespan):
    begin, end = timespan
    if isinstance(P, Point):
        return (begin <= P.ts < end)
    else:
        return (begin <= P < end)

def get_dense_timespan(df, stdn=1.0):
    dt_min = df.created_at.min()
    deltas = df.created_at - dt_min
    dmean = deltas.mean()
    dstd = deltas.std()
    begin = dt_min + dmean - stdn * dstd
    end = dt_min + dmean + stdn * dstd
    minbegin, maxend = get_timespan(df)
    return (max(begin, minbegin), min(end, maxend))

# ------------------------------------------------------------------------------

def distance(*args, **kwargs):
    lazy = kwargs.pop('lazy', 0)
    if lazy == 1:
        # 1.7x faster than VincentyDistance
        distanceFunction = GreatCircleDistance
    elif lazy == 2:
        # 11.8x faster than VincentyDistance
        distanceFunction = lazyDistance
    else:
        distanceFunction = VincentyDistance
    return distanceFunction(*args, **kwargs).km

def lazyDistance(P, Q):
    """
    Fastest but inaccurate distance function.

    Radius    Error
    ~10km     0.002%
    ~100km    0.0016% (sometimes even better than GreatCircleDistance)
    ~3000km   0.00074%

    Speed: 11.8x faster than VincentyDistance
    """
    latP, lngP = radians(degrees=P[0]), radians(degrees=P[1])
    latQ, lngQ = radians(degrees=Q[0]), radians(degrees=Q[1])
    sphericalCos = sin(latP) * sin(latQ) + cos(latP) * cos(latQ) * cos(lngQ - lngP)
    return Distance(acos(sphericalCos) * 6371)

def sum_dist(P, d, bearing):
    Q = VincentyDistance(kilometers=d).destination(P, bearing)
    return (Q.latitude, Q.longitude)

def go_east(lat, lng, d, lazy=False):
    if d == 0:
        return lng
    else:
        if not lazy:
            return sum_dist((lat, lng), d, EAST)[1]
        else:
            # Longitude: 1 deg ~ 111.320*cos(latitude) km
            return lng + d / (111.32 * cos(radians(degrees=lat)))

def go_north(lat, lng, d, lazy=False):
    if d == 0:
        return lat
    else:
        if not lazy:
            return sum_dist((lat, lng), d, NORTH)[0]
        else:
            # Latitude: 1 deg ~ 110.54 km
            return lat + d / 110.54

# ------------------------------------------------------------------------------

class SparseArray(object):
    def __init__(self, dimension=2, default_value=0, shape=None):
        self.elements = {}
        self.default = default_value
        if not isinstance(dimension, int) or dimension < 2:
            raise ValueError("Invalid dimension")
        self.dim = dimension
        self.shape = shape

    def __getitem__(self, index):
        if not isinstance(index, tuple):
            raise IndexError("Index must be a %s-tuple" % self.dim)
        if not self.in_bounds(index):
            raise IndexError("Index %s out of bounds %s" % (index, self.shape))
        try:
            value = self.elements[index]
        except KeyError:
            value = deepcopy(self.default)
        return value

    def __setitem__(self, index, value):
        if not isinstance(index, tuple):
            raise IndexError("Index must be a %s-tuple" % self.dim)
        if not self.in_bounds(index):
            raise IndexError("Index %s out of bounds %s" % (index, self.shape))
        self.elements[index] = value

    def __repr__(self):
        return pformat(dict([(k, len(v)) for k, v in self.elements.items()]))

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    def in_bounds(self, index):
        if len(index) != self.dim:
            raise KeyError("Trying to access element %s in array of dimension %s" % (index, self.dim))

        if self.shape is not None:
            for i in range(self.dim):
                if not (0 <= index[i] < self.shape):
                    return False
        return True

    def insert(self, index, value):
        if index not in self.elements:
            self.elements[index] = [value]
        elif isinstance(self.elements[index], list):
            self.elements[index].append(value)
        else:
            raise ValueError("Cell %s is not empty" % index)

    def squash(self, d=0):
        """Project array supressing dimension `d`"""
        if self.dim == 2:
            return self

        shape = self.shape[:d] + self.shape[d+1:]
        dimension = self.dim - 1
        p = SparseArray(dimension=dimension, shape=shape, default_value=list())

        for i in self.elements:
            j = i[:d] + i[d+1:] # concatenate tuples
            for point in self.elements[i]:
                p.insert(j, point)
        return p

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self, b):
        if b is not None and len(b) != self.dim:
            raise ValueError("Dimension does not match bounds dimension")
        self._shape = b

# ------------------------------------------------------------------------------

class Point(object):
    """
    Simple two-dimensional geographical point with metadata.
    """
    def __init__(self, point, **kwargs):
        if isinstance(point, tuple):
            self.latlng = point
        else:
            raise TypeError("Invalid point format")
        # if metadata is not specified, interpret kwargs itself as the metadata
        self.metadata = kwargs.get('metadata', kwargs)

    def __getitem__(self, key):
        if key in [0, 1]:
            return self.latlng[key]
        elif key in ["lat", "lng"]:
            i = ["lat", "lng"].indexOf(key)
            return self.latlng[i]
        else:
            return self._metadata[key]

    def __setitem__(self, key, value):
        if key in [0, 1, "lat", "lng"]:
            raise TypeError("Point coordinates are immutable")
        else:
            self._metadata[key] = value

    def __getattr__(self, key):
        if key in self._metadata:
            return self._metadata[key]
        else:
            raise AttributeError(repr(key))

    def __iter__(self):
        return iter(self.latlng)

    def __repr__(self):
        lat, lng = self.latlng
        return "Point((%.3f, %.3f), metadata: %s)" % (lat, lng, truncate(str(self.metadata), 24))

    def __getnewargs__(self):
        "Return self as a plain tuple. Used by copy and pickle."
        return tuple(self)

    def __eq__(self, other):
        return tuple(self) == tuple(other) and self.latlng == other.latlng

    def __ne__(self, other):
        return tuple(self) != tuple(other) or self.latlng != other.latlng

    # -- PROPERTIES --
    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if value and not isinstance(value, dict):
            raise TypeError("'metadata' must be from type dict")
        if "lat" in value or "lng" in value:
            raise TypeError("'lat' and 'lng' are unallowed metadata keys")
        self._metadata = value

    lat = property(itemgetter(0), doc='Alias for field number 0')
    lng = property(itemgetter(1), doc='Alias for field number 1')
    timestamp = property(itemgetter("created_at"), doc='Alias for metadata key "created_at"')
    ts = property(itemgetter("created_at"), doc='Alias for metadata key "created_at"')
