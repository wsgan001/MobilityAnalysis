#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 9 Feb. 2015
# ------------------------------------------------------------------------------
# BOUNDING BOXES
# bbox = [W, S, E, N]
# Use `bbox_from_name` to get more bounding boxes.
BB_CAL = [-124.48, 32.53, -114.13, 42.01] # California
BB_SF_AREA = [-122.5893, 37.1719, -121.6862, 38.0196] # San Francisco bay area
BB_SF_CITY = [-122.614895, 37.63983, -122.28178, 37.929844] # San Francisco city
BB_OAK = [-122.355881, 37.632226, -122.114672, 37.885368] # Oakland
# ------------------------------------------------------------------------------

import numpy as np
import pandas as pd

from psense.util import *

# ------------------------------------------------------------------------------

def slow_build_grid(df, bbox=None, gridsize=1.0, lazy=0):
    """
    Return the cell of size `s` with the highest all-time record count.

    Args:
        df (pandas.DataFrame): Source dataframe with spatiotemporal user
            data upon which the grid is built.
        bbox (list, optional): The target bounding box of the geodata.
        gridsize (float): The gridsize in kilometers.
        lazy (int): The choice of the distance function. Must be in
            [0, 1, 2].

    Runtime:
        O(m * n * S), where S is the size of `df` and (m, n) is the dimension of
        the grid.
    """
    if not bbox:
        bbox = get_bbox(df)
    W, S, E, N = bbox
    print "Sampling in a (%skm x %skm) box with %skm long steps" % (E - W, N - S, gridsize)
    bottom = S
    left = W
    traffic = []
    while left < E - EPSILON: # walk east
        traffic.append([])
        right = min(go_east(bottom, left, gridsize), E)
        while bottom < N - EPSILON: # walk north
            top = min(go_north(bottom, left, gridsize), N)
            count = len(bound(df, [left, bottom, right, top]))
            traffic[-1].insert(0, count)
            bottom = top
        bottom = S
        left = right

    traffic = np.matrix(traffic, dtype='int').T # transpose
    print "Yielded (%s x %s) grid." % traffic.shape

    g = Grid(bbox, sizematrix=traffic, gridsize=gridsize, lazy=lazy)
    return g

def get_max_traffic_cell(grid, all=False):
    """
    Return the cell with the highest all-time record count.
    """
    m = grid.sizematrix
    if all: # return all maxima
        # This does 3 iterations through the whole matrix
        i, j = np.where(m == m.max())
        return zip(i, j)
    else: # return first maximum found
        i, j = np.unravel_index(m.argmax(), m.shape)
        return [(i, j)]

def get_max_traffic_location(df, bbox=None, gridsize=1.0, lazy=0):
    """
    Return the midpoint of the cell of gridsize `gridsize` with the highest all-time record count.
    """
    g = build_grid(df, bbox, gridsize=gridsize, lazy=lazy)
    c = get_max_traffic_cell(g)
    return g.get_midpoint(c, lazy=lazy)

# ------------------------------------------------------------------------------

class Grid(object):
    """
    Geographically projected grid, populated with two-dimensional data.

    Common instantiation::
        Grid(bbox, gridsize)

    Args:
        bbox (list, optional): Bounding box in degrees of the format
            [W, S, E, N]. If a dataframe `df` is specified, then it is generated from that if unpresent.
        tbox (list, optional): The time span or limits of the time range. If a
            dataframe `df` is specified, then it is generated from that if
            unpresent.
        data (psense.util.SparseArray, optional): Array containing the points
            that correspond to the entries in dataframe `df`.
        sizematrix (numpy.matrix, optional): Matrix giving the size of each
            gridcell of `data`. Is overwritten if `data` is given.
        df (pandas.DataFrame, optional): Source pandas.DataFrame containing
            spatiotemporal data within the grid (tbox and bbox).
        gridsize (float, optional): The spatial resolution in kilometers.
        partition (tuple, optional): a list or dict with two elements: a `rows`
            list giving the latitude each horizontal cut of the grid; and a
            `columns` list giving the longitude of each vertical cut of the
            grid.
        lazy (int, optional): The degree of laziness in distance calculations.
            Should be in [0, 1, 2]

    Specifying at least one of the `gridsize` and `partition` parameters is
    required.
    """
    def __init__(self, bbox=None, data=None, sizematrix=None, df=None, gridsize=None, partition=None, lazy=0):
        self._rows = None
        self._columns = None
        self._gridsize = None
        self._data = data
        self._sizematrix = sizematrix
        if data is not None and not isinstance(data, SparseArray):
            raise TypeError("'data' must be of type SparseArray")
        if sizematrix is not None and not isinstance(sizematrix, np.matrixlib.defmatrix.matrix):
            raise TypeError("'sizematrix' must be a numpy.matrix")
        if gridsize is None and partition is None:
            raise TypeError("You must specify at least one of the 'gridsize' or 'partition' parameters")

        if gridsize:
            if gridsize > 0:
                self._gridsize = float(gridsize)
            else:
                raise ValueError("'gridsize' must be positive")
        else:
            self.partition = partition

        self.lazy = lazy
        self.df = df # points (users) DataFrame
        self.bbox = bbox
        self._updateRows = False
        self._updateCols = False

    def __repr__(self):
        s = repr(self.sizematrix.__array__()).replace('array', 'Grid')
        # line up matrix rows with the first row
        l = s.splitlines()
        for i in range(1, len(l)):
            if l[i]:
                l[i] = l[i][1:]
        return '\n'.join(l)

    def __str__(self):
        return self.sizematrix.__str__()

    def __getitem__(self, cellindex):
        if isinstance(cellindex, slice):
            raise "Invalid index slicing"
        elif len(cellindex) == 2 and isinstance(cellindex, (list, tuple)):
            x, y = cellindex
            return self.data[(x, y)]
        else:
            raise TypeError("Invalid argument type")

    def _distance(self, *args, **kwargs):
        kwargs['lazy'] = self.lazy
        return distance(*args, **kwargs)

    def _checkConsistency(self, axis):
        this = self._columns if axis == 'cols' else self._rows
        other = self._columns if axis == 'rows' else self._rows
        bounds = self.vbounds if axis == 'rows' else self.hbounds
        obounds = self.vbounds if axis == 'cols' else self.hbounds
        gheight = [(this[0], obounds[0]), (this[1], obounds[0])]
        gwidth = [(obounds[0], this[0]), (obounds[0], this[1])]
        d = self._distance(*gheight) if axis == 'rows' else self._distance(*gwidth)

        if not all(bounds[0] <= b <= bounds[1] for b in this):
            raise ValueError("Partition not within bbox")
        if not self.gridsize:
            self._gridsize = d
        elif other is not None and np.abs(self.gridsize - d) > EPSILON:
            raise TypeError("Gridsize does not correspond to the resolution of the partition")

    def _go_east(self, d):
        W, S = self.bbox[:2]
        return go_east(S, W, d)

    def _go_north(self, d):
        W, S = self.bbox[:2]
        return go_north(S, W, d)

    def add_point(self, *args, **kwargs):
        if (len(args) == 2 or (len(args) == 1 and isinstance(args[0], tuple))):
            lat, lng = args
            P = Point((lat, lng), metadata=kwargs)
        elif len(args) == 1 and isinstance(args[0], Point):
            P = args[0]
        else:
            raise TypeError("Invalid point type")
        if not in_bounds(P, self.bbox):
            raise ValueError("Point (%s, %s) not inside grid's bbox" % (P.lat, P.lng))

        # space
        W, S, E, N = self.bbox
        index = [0, 0] # t, lat, lng
        for n in [0, 1]:
            Q = [(P.lat, W), (S, P.lng)][n]
            d = self._distance((S, W), Q)
            k = int(d / self.gridsize)
            # reverse row indexing
            index[n] = k if (n == 1) else self.rowlength - k - 1

        index = tuple(index)
        self.data.insert(index, P)
        return index

    def add_cell_in_df(self, P):
        df.loc[(df.created_at == P.ts) & (df.index == P.user_id), "icell"] = self.add_point(P)

    def get_midpoint(self, cell, lazy=False):
        i, j = cell
        top = self.rows[i]
        left = self.columns[j]
        d = self.gridsize / 2
        lat = go_north(top, left, -d, lazy=lazy)
        lng = go_east(top, left, d, lazy=lazy)
        return (lat, lng)

    def get_cells(self, uid):
        if self.df is None:
            raise ValueError("DataFrame 'df' has not been set")
        if uid not in self.df.index:
            raise ValueError("%s not in 'df'" % uid)
        rawcells = self.df.loc[uid, "icell"]
        if isinstance(rawcells, tuple):
            return [rawcells]
        else:
            return list(set(self.df.loc[uid, "icell"]))

    def get_points(self, cellindex):
        return self.data[cellindex]

    # -- CLASS METHODS --
    @classmethod
    def build(cls, df, bbox=None, gridsize=1.0, lazy=0):
        """
        Build a two-dimensional grid from the locations of each point of the
        DataFrame `df`, and count the occurrences in each cell.

        Runtime:
            O(S + (m * n)), where S is the size of `df` and (m, n) is the
            dimension of the grid. (m * n) just comes from initializing the
            grid.
        """
        # initialize grid
        g = cls(bbox, gridsize=gridsize, lazy=lazy)
        # define row vector function
        def add_point(row):
            metadata = row.loc[:"text"].to_dict()
            P = Point((row.lat, row.lng), metadata=metadata)
            # modify g and return the cell index
            return [g.add_point(P)] # passes a list because of pd.Timestamp bug
        # bound dataframe to bbox (and make 'user_id' a column)
        df_bounded = bound(df, bbox).reset_index()
        # loop through the dataframe and register each report in the grid
        # Extract the results of the first (any) column (pd.Timestamp
        # workaround)
        df_bounded.loc[:, "icell"] = df_bounded.apply(add_point, axis=1).iloc[:, 0]
        # set 'user_id' back to index
        df_bounded.set_index("user_id", inplace=True)
        df_bounded.index.name = "user_id"
        g.df = df_bounded
        return g

    # -- PROPERTIES --
    @property
    def gridsize(self):
        return self._gridsize

    @gridsize.setter
    def gridsize(self, value):
        if value != self._gridsize:
            self._gridsize = float(value)
            self._updateRows = True
            self._updateCols = True

    @property
    def bbox(self):
        if self._bbox is not None:
            return self._bbox
        else:
            raise ValueError("'bbox' not yet set")

    @bbox.setter
    def bbox(self, value):
        if value is None:
            # generate from `df` if possible
            if self.df is not None:
                self._bbox = get_bbox(self.df)
            else:
                self._bbox = None
        else:
            W, S, E, N = value
            if (self._distance((S, W), (N, W)) < self.gridsize
                or self._distance((S, W), (S, E)) < self.gridsize):
                raise ValueError("Grid size doesn't fit within bbox")
            self.vbounds = (S, N)
            self.hbounds = (W, E)
            self._bbox = value
            if self._rows is not None:
                self._updateRows = True
            if self._columns is not None:
                self._updateCols = True

    @property
    def size(self):
        W, S, E, N = self.bbox
        vertical = self._distance((S, W), (N, W))
        horizontal = self._distance((S, W), (S, E))
        return (vertical, horizontal)

    @property
    def shape(self):
        return (self.rowlength, self.collength)

    @property
    def data(self):
        if self._data is None or self.shape != self._data.shape:
            # self._data = np.matrix(np.zeros(self.shape, dtype=np.int))
            self._data = SparseArray(dimension=2, shape=self.shape, default_value=list())
        return self._data

    @property
    def sizematrix(self):
        if self._sizematrix is not None and self._data is None:
            return self._sizematrix
        else:
            m = np.matrix(np.zeros(self.shape, dtype=np.int))
            for i in self.data:
                m[i] = len(self.data[i])
            return m

    @property
    def columns(self):
        if self.gridsize and (self._columns is None or self._updateCols):
            new_cols = [self._go_east(i*self.gridsize) \
                for i in range(self.collength)]
            # new_cols = [lng for lng in new_cols if W <= lng <= E]
            self._columns = np.array(new_cols)
            self._updateCols = False
        return self._columns

    @columns.setter
    def columns(self, value):
        if isinstance(value, np.ndarray):
            self._columns = value
        elif isinstance(value, list):
            self._columns = np.array(value)
        else:
            raise TypeError
        self._checkConsistency('cols')

    @property
    def rows(self):
        if self.gridsize and (self._rows is None or self._updateRows):
            new_rows = [self._go_north(i*self.gridsize) \
                for i in range(self.rowlength)]
            # new_rows = [lat for lat in new_rows if S <= lat <= N]
            new_rows.reverse()
            self._rows = np.array(new_rows)
            self._updateRows = False
        return self._rows

    @rows.setter
    def rows(self, value):
        if isinstance(value, np.ndarray):
            self._rows = value
        elif isinstance(value, list):
            self._rows = np.array(value)
        else:
            raise TypeError
        self._checkConsistency('rows')

    @property
    def collength(self):
        W, S, E, N = self.bbox
        return int(self._distance((S, W), (S, E)) / self.gridsize) + 1

    @property
    def rowlength(self):
        W, S, E, N = self.bbox
        return int(self._distance((S, W), (N, W)) / self.gridsize) + 1

    @property
    def partition(self):
        return (self.rows, self.columns)

    @partition.setter
    def partition(self, value):
        if len(value) != 2:
            raise TypeError("The partition must be a (rows, columns) pair")
        if isinstance(partition, (list, tuple)):
            self.rows, self.columns = partition
        elif isinstance(partition, dict):
            self.rows, self.columns = partition['rows'], partition['columns']
        else:
            raise TypeError("Partition must be a list, tuple or dictionary")

    @property
    def userlist(self): # actually a np.array
        if self.df is not None:
            return self.df.index.unique()
        else:
            raise AttributeError("No users to retrieve because grid's DataFrame 'df' has not been set")

# ------------------------------------------------------------------------------
# Main functions

def main__compare_distances():
    from geopy.distance import Distance, VincentyDistance, GreatCircleDistance

    d = [VincentyDistance, GreatCircleDistance, lazyDistance]
    dnames = ['vincenty', 'greatcircle', 'lazy']
    P = (37.842520, -122.297614)
    Q = [(37.84254, -122.29729), (37.84856, -122.27148), (36.98912, -122.02291), (20.55051, -103.27148)]

    setup = """
from geopy.distance import VincentyDistance, GreatCircleDistance
from psense.grid import lazyDistance
d0 = VincentyDistance # very precise, slow
d1 = GreatCircleDistance # precise, moderate
d2 = lazyDistance # inaccurate, fast
P = (37.842520, -122.297614)
Q0 = (37.84254, -122.29729) # very near
Q1 = (37.84856, -122.27148) # near
Q2 = (36.98912, -122.02291) # far
Q3 = (20.55051, -103.27148) # very far
"""
    results = {'vincenty': [] ,'greatcircle': [], 'lazy': []}
    distances = {'vincenty': [] ,'greatcircle': [], 'lazy': []}

    for i, k in enumerate(dnames):
        print k.upper()
        for j in range(4):
            r = min(timeit.Timer('d%s(P, Q%s)' % (i, j), setup=setup).repeat(20, number=10000))
            results[k].append(r)
            distances[k].append(d[i](P, Q[j]).km)
            print "Q%s: " % j, r, "seconds"

    dictFrame = {"results": results, "distances": distances}
    t = {(outerKey, innerKey): values for outerKey, innerDict in dictFrame.iteritems() for innerKey, values in innerDict.iteritems()}

    df = pd.DataFrame(t, index=["Q0", "Q1", "Q2", "Q3"])

    def abs_diff(x, y):
        return abs(x - y)

    # difference
    micols = pd.MultiIndex.from_tuples([("difference", "greatcircle"), ("difference", "lazy"), ("difference", "vincenty")])
    df_diff = pd.DataFrame(columns=micols, index=["Q0", "Q1", "Q2", "Q3"])
    for k in dnames:
        df_diff["difference", k] = abs_diff(
            df["distances", k], df["distances", "vincenty"])

    df = pd.concat([df, df_diff], axis=1)
    df.to_pickle("log_dist.pickle")

def main__build_grid():
    f = choose_files("/Users/Alexis/Documents/estadata-alexis/data/twitter", filenumber=10)
    df = build_df(f)
    m = fast_grid_count(df, BB_OAK, s=2.5)
    g = Grid(BB_OAK, data=m, gridsize=2.5)
    print repr(g)
    print get_max_traffic_cell(g)


if __name__ == '__main__':
    from psense.io_csv import *
    import timeit
    # main__compare_distances()
    main__build_grid()

# ------------------------------------------------------------------------------
