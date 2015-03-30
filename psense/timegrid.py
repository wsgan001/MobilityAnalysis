#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 13 Feb. 2015
# ------------------------------------------------------------------------------
# GOALS
# 1. Choose users to carry higher quality sensors based on their connectivity.
# 2. Determine strong connections between neighbors.
# 3. Analyse movement patterns and choose mobile reference agents carrying
#    higher quality sensors.
#
# SETTING
# - High number of lower quality sensors carried by individual people.
# - Calibration is done constantly, giving priority to higher quality sensors
#       (or, much less frequently, static sensor stations) and to sensors with
#       a more recent calibration stamp.
# - Calibration happens only in one direction (higher quality -> low quality),
#       i.e. results are not averaged.
#
# Central user HEURISTICS:
# - Pick user with most rendezvous.
# - Pick user with most (unique) redezvous users.
# - Pick the user with the greatest number of spatial rendezvous users.
# ------------------------------------------------------------------------------

import datetime as dt
from psense.util import *
from psense.grid import *

# ------------------------------------------------------------------------------

def get_rendezvous(g, uid):
    """
    Get the number of cell coincidences with other users for a given user.

    Runtime:
        O(M * N), where M is the maximum number entries per user and N is the
        length of the data
    """
    rendezvous = []
    for cell in g.get_cells(uid):
        for point in g.get_points(cell):
            if point['user_id'] != uid:
                rendezvous.append(point)
    return rendezvous

def get_rendezvous_users(g, uid):
    """
    Get the users with which the user with ID `uid` shares a cell (rendezvous).
    """
    rvs_users = []
    for cell in g.get_cells(uid):
        for point in g.get_points(cell):
            if point['user_id'] != uid and point['user_id'] not in rvs_users:
                rvs_users.append(point['user_id'])
    return rvs_users

def get_spatial_rendezvous_users(g, uid):
    """
    Get the users with which the user `uid` shares a spatial cell (time-independently).
    """
    if isinstance(g, TimeGrid):
        g = g.projection
    srvs_users = []
    for cell in g.get_cells(uid):
        for point in g.get_points(cell):
            if point['user_id'] != uid:
                srvs_users.append(point['user_id'])
    return srvs_users

def measure_rendezvous(g, uid):
    """
    Compute the number of rendezvous of a given user.

    Args:
        g (TimeGrid): A data-populated three dimensional grid.
        uid (int): The ID of a user in the dataframe of `g`.

    Returns:
        The number of rendezvous of the user with ID `uid`, which is defined by
        a cell coincidence with another user.

    Runtime:
        O(M * N), M is the maximum number entries per user and N is the length
        of the data. If the gridsize is such that there is a 1/n chance to find
        a non-empty cell (or a 'dense' cell), then we get an average time of
        O(M).
    """
    return len(get_rendezvous(g, uid))

def measure_rendezvous_users(g, uid):
    """
    Compute the number of rendezvous users of a given user.

    Returns:
        The number of different users with which the user with ID `uid` shares a cell (rendezvous).
    """
    return len(get_rendezvous_users(g, uid))

def measure_spatial_rendezvous_users(g, uid):
    """
    Compute the number of spatial rendezvous users of a given user.

    Returns:
        The number of users with which the user `uid` shares a spatial cell
        (time-independently).

    Runtime:
        TODO: (grid projection) + U * M * N

    This approach assumes the user data reflects general movement patterns that are not time-specific.
    """
    return len(get_spatial_rendezvous_users(g, uid))

def get_central_user(g, mode="all", all=False):
    """
    General parent function to find a 'central' user maximizing different grid rendezvous measures.

    Args:
        g (Grid): Grid populated with data/dataframe.
        mode (str): choice of measure to maximize. Must be a key in the
            `maxfunctions` dictionary.
        all (bool, optional): decide whether to return only the first or all
            maxima. Defaults to False.

    Runtimes:
    - [all] measure_rendezvous
        O(U * M * N), where U is the number of users, M is the maximum
        number entries per user and N is the length of the data. On average
        O(U * M), see `measure_rendezvous`.
    - [user] measure_rendezvous_users
    """

    # maximizing functions/measures
    max_functions = {
        "all": measure_rendezvous,
        "users": measure_rendezvous_users,
        "spatial": measure_spatial_rendezvous_users,
        }

    if isinstance(mode, str) or isinstance(mode, int):
        try:
            if isinstance(mode, int):
                mode = max_functions.keys()[mode]
            max_function = max_functions[mode]
        except KeyError:
            raise ValueError("Invalid 'mode' %s" % mode)
    else:
        raise TypeError

    if mode == "spatial":
        if isinstance(g, TimeGrid):
            g = g.projection # project to two-dimensional spatial field

    m = 0
    maxuser = []
    for uid in g.userlist:
        n = max_function(g, uid)
        if not all:
            if n > m:
                maxuser = uid
                m = n
        else:
            if n >= m:
                maxuser.append(uid)
                m = n
    return maxuser

# ------------------------------------------------------------------------------

class TimeGrid(Grid):
    """
    Grid with additional time dimension.

    Common instantiation::
        TimeGrid(bbox, tbox, gridsize, tres)

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
        tres (float, optional): The resolution of the (equidistant) time
            partition in hours.
        partition (tuple or dict, optional): the partitions on each of the axes.
        lazy (int, optional): The degree of laziness in distance calculations.
            Should be in [0, 1, 2]

    Specifying at least one of the `gridsize` and `partition` parameters is
    required.
    """
    def __init__(self, bbox=None, tbox=None, data=None, sizematrix=None, df=None, gridsize=None, tres=None, partition=None, lazy=0):
        super(TimeGrid, self).__init__(bbox, data, sizematrix, df, gridsize, partition, lazy)
        self._timerange = None # time row/column
        self.tres = tres # time resolution
        self.df = df # points (users) DataFrame
        self.tbox = tbox
        self._updateTime = False

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "TimeGrid(%s, %s non-empty cells, %s points)" % (self.shape, len(self.data), len(self.df))

    def __getitem__(self, cellindex):
        if isinstance(cellindex, slice):
            raise "Invalid index slicing"
        elif len(cellindex) == 3 and isinstance(cellindex, (list, tuple)):
            t, x, y = cellindex
            return self.data[(t, x, y)]
        else:
            raise TypeError("Invalid argument type")

    def add_point(self, *args, **kwargs):
        if (len(args) == 2 or (len(args) == 1 and isinstance(args[0], tuple))) and "created_at" in kwargs:
            lat, lng = args
            P = Point((lat, lng), metadata=kwargs)
        elif len(args) == 1 and isinstance(args[0], Point):
            P = args[0]
        else:
            raise TypeError("Invalid point type")
        if not (in_bounds(P, self.bbox) and in_timespan(P, self.tbox)):
            raise ValueError("Point (%s, %s, t=%s) not inside grid's bbox and tbox" % (P.lat, P.lng, P.ts))

        # space
        W, S, E, N = self.bbox
        index = [0, 0, 0] # t, lat, lng
        for n in [0, 1]:
            Q = [(P.lat, W), (S, P.lng)][n]
            d = self._distance((S, W), Q)
            k = int(d / self.gridsize)
            # reverse row indexing
            index[n + 1] = k if (n == 1) else self.rowlength - k - 1

        # time
        d = P.ts - self.tbox[0]
        index[0] = int(d.total_seconds() / self.tres.total_seconds())

        index = tuple(index)
        self.data.insert(index, P)
        return index

    # -- CLASS METHODS --
    @classmethod
    def build(cls, df, bbox=None, tbox=None, gridsize=1.0, tres=24, lazy=0, bound_dense=False):
        """
        Return the cell of size `gridsize` with the highest all-time record count.

        Runtime:
            O(S + (m * n)), where S is the size of `df` and (m, n) is the
            dimension of the grid. (m * n) just comes from initializing the
            grid.
        """
        if bound_dense:
            tbox = get_dense_timespan(df)
        elif tbox is None:
            tbox = get_timespan(df)
        # initialize grid
        g = cls(bbox, tbox=tbox, gridsize=gridsize, tres=tres, lazy=lazy)
        # define row vector function
        def add_point(row):
            metadata = row.loc[:"text"].to_dict()
            P = Point((row.lat, row.lng), metadata=metadata)
            # modify g and return the cell index
            return [g.add_point(P)]
        # bound dataframe to bbox (and make 'user_id' a column)
        df_bounded = bound(df, bbox).reset_index()
        # loop through the dataframe and register each report in the grid.
        df_bounded["icell"] = df_bounded.apply(add_point, axis=1).iloc[:, 0]
        # set 'user_id' back to index
        df_bounded.set_index("user_id", inplace=True)
        df_bounded.index.name = "user_id"
        g.df = df_bounded
        return g

    # -- PROPERTIES --
    @property
    def tres(self):
        return self._tres

    @tres.setter
    def tres(self, value):
        if isinstance(value, float) or isinstance(value, int):
            self._tres = dt.timedelta(hours=value)
        elif isinstance(value, dt.timedelta):
            self._tres = value
        else:
            raise ValueError
        if self._timerange is not None:
            self._updateTime = True

    @property
    def tbox(self):
        if self._tbox is not None:
            return self._tbox
        else:
            raise ValueError("'tbox' not yet set")

    @tbox.setter
    def tbox(self, value):
        if value is None:
            # generate from `df` if possible
            if self.df is not None:
                self._tbox = get_timespan(self.df)
            else:
                self._tbox = None
        else:
            if not (isinstance(value, tuple) and len(value) == 2):
                raise ValueError
            elif not (hasattr(value[0], 'day') and hasattr(value[1], 'day')):
                raise ValueError
            tfrom, tto = value
            if tto - tfrom < self.tres:
                raise ValueError("Time-size doesn't fit within tbox")
            self._tbox = value
            if self._timerange is not None:
                self._updateTime = True

    @property
    def shape(self):
        return (self.tlength, self.rowlength, self.collength)

    @property
    def data(self):
        if self._data is None or self.shape != self._data.shape:
            self._data = SparseArray(dimension=3, shape=self.shape, default_value=list())
        return self._data

    @property
    def sizematrix(self):
        if self._sizematrix is not None and self._data is None:
            return self._sizematrix
        else:
            # ignores time dimension
            m = np.matrix(np.zeros(self.shape[1:], dtype=np.int))
            for i in self.data:
                m[i[1:]] += len(self.data[i])
            return m

    @property
    def timerange(self):
        if self.tres and (self._timerange is None or self._updateTime):
            tfrom = self.tbox[0]
            new_trange = [tfrom + i*self.tres for i in range(self.tlength)]
            self._timerange = np.array(new_trange)
            self._updateTime = False
        return self._timerange

    @timerange.setter
    def timerange(self, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            if not hasattr(value[0], 'day'):
                raise TypeError
            self._timerange = np.array(value)
        else:
            raise TypeError

    @property
    def tlength(self):
        delta = self.tbox[1] - self.tbox[0]
        return int(delta.total_seconds() / self.tres.total_seconds()) + 1

    @property
    def partition(self):
        return (self.timerange, self.rows, self.columns)

    @partition.setter
    def partition(self, value):
        if len(value) != 3:
            raise TypeError("The partition must be a (timerange, rows, columns) tuple")
        if isinstance(partition, (list, tuple, np.ndarray)):
            self.timerange, self.rows, self.columns = partition
        elif isinstance(partition, dict):
            self.timerange, self.rows, self.columns = partition['timerange'], partition['rows'], partition['columns']
        else:
            raise TypeError("Partition must be a list, tuple or dictionary")

    @property
    def projection(self):
        if not self.data:
            raise ValueError("Data array has not been set")
        squashed_data = self.data.squash()

        new_df = self.df.copy()
        reduce_dim = lambda r: [r.icell[1:]]
        new_df["icell"] = new_df.apply(reduce_dim, axis=1).iloc[:, 0]
        g = Grid(self.bbox, squashed_data, self.sizematrix, new_df, self.gridsize, None, self.lazy)
        return g
