#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 20 Mar. 2015
# ------------------------------------------------------------------------------

import sys
from os import path as op
import timeit
import time
from datetime import datetime
import inspect
from itertools import product
import pandas as pd

LOGDIR = "logs/time/"
DATADIR = "data/twitter/CSV/"

# ------------------------------------------------------------------------------

SHEAD = """
from psense.io_csv import *
from psense.%s import *
f = choose_files("%s", filenumber=%s)
df = build_df(f)
""" % ("%s", op.abspath(op.join(op.dirname(__file__), '..', DATADIR)), "%s")

def log_time(outf, r):
    ts = time.time()
    d = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    with open(outf, "a") as f:
        s = d + "    " + str(r) + " seconds\n"
        f.write(s)

def time_build_grid(filenumber=100, repeat=3, number=10, gridsize=2.0, tres=3600, bbox=None, tbox=None, lazy=0, mode="all", all=False):
    setup = SHEAD % ("grid", filenumber)

    runstr = "Grid.build(df, %s, %s, %s)" % (bbox, gridsize, lazy)
    tlist = timeit.Timer(runstr, setup=setup).repeat(
        repeat=repeat, number=number)
    print "-" * 36
    print "Tries:", tlist
    r = min(tlist) / number
    print r, "seconds (%sr, %sn)" % (repeat, number)

    outf = LOGDIR + "build-grid-G%s-[f%sr%sn%s].log" % (gridsize, filenumber, repeat, number)
    log_time(outf, r)

def time_build_timegrid(filenumber=100, repeat=3, number=10, gridsize=2.0, tres=3600, bbox=None, tbox=None, lazy=0, mode="all", all=False):
    setup = SHEAD % ("timegrid", filenumber)

    runstr = "TimeGrid.build(df, %s, %s, %s, %s, %s, bound_dense=True)" % (bbox, tbox, gridsize, tres, lazy)
    tlist = timeit.Timer(runstr, setup=setup).repeat(
        repeat=repeat, number=number)
    print "-" * 36
    print "Tries:", tlist
    r = min(tlist) / number
    print r, "seconds (%sr, %sn)" % (repeat, number)

    outf = LOGDIR + "build-timegrid-G%sT%sL%s-[f%sr%sn%s].log" % (gridsize, tres, lazy, filenumber, repeat, number)
    log_time(outf, r)

def time_get_central_user(filenumber=100, repeat=3, number=10, gridsize=2.0, tres=3600, bbox=None, tbox=None, lazy=0, mode="all", all=False):
    setup = (SHEAD + "g = TimeGrid.build(df, %s, %s, %s, %s, %s, bound_dense=True)") % ("timegrid", filenumber, bbox, tbox, gridsize, tres, lazy)

    runstr = "get_central_user(g, mode='%s', all=%s)" % (mode, all)
    tlist = timeit.Timer(runstr, setup=setup).repeat(
        repeat=repeat, number=number)
    print "-" * 36
    print "Tries:", tlist
    r = min(tlist) / number
    print r, "seconds (%sr, %sn)" % (repeat, number)

    a = "all" if all else "single"
    outf = LOGDIR + "central-user-%s-(%s)-G%sT%sL%s-[f%sr%sn%s].log" % (mode, a, gridsize, tres, lazy, filenumber, repeat, number)
    log_time(outf, r)


if __name__ == '__main__':
    sys.path.append(op.join(op.dirname(__file__), '..'))

    BB_SF_CITY = [-122.614895, 37.63983, -122.28178, 37.929844]
    TB_100F = (pd.Timestamp('2010-09-12 02:15:25'), pd.Timestamp('2011-06-20 12:33:47.690727448'))

    args = {}
    # Hard coded test-arguments
    args["repeat"] = 4
    args["number"] = 10
    args["filenumber"] = 100
    args["gridsize"] = 2.0
    args["tres"] = 3600
    args["bbox"] = BB_SF_CITY
    args["tbox"] = TB_100F
    args["lazy"] = 0
    args["mode"] = "all" # all, users, spatial
    args["all"] = False

    if len(sys.argv) >= 2:
        if sys.argv[1] != "all":
            print "[TIMEIT:", args["repeat"], "reps", args["number"], "loops]"
            i = int(sys.argv[1])
            function = [
                time_build_grid,
                time_build_timegrid,
                time_get_central_user
                ][i]

            args = [args[a] for a in inspect.getargspec(function)[0]]
            function(*args)
        else:
            # test multiple parameter combinations for a single function
            i = int(sys.argv[2])
            function = [
                time_build_grid,
                time_build_timegrid,
                time_get_central_user
                ][i]

            f_ = [100, 200, 300]
            g_ = [4.0, 3.0, 2.0, 1.0, 0.5]
            t_ = [2880, 1440, 720, 360, 168]
            l_ = [0, 1, 2]
            m_ = ["all", "users", "spatial"]
            a_ = [False, True]

            for f, g, t, l, m, a in product(f_, g_, t_, l_, m_, a_):
                if (i == 0 and (t == t_[0] and m == m_[0] and a == a_[0]) or
                    i == 1 and (m == m_[0] and a == a_[0]) or
                    i == 2):
                    function(filenumber=f, repeat=3, number=10, gridsize=g, tres=t, bbox=BB_SF_CITY, tbox=TB_100F, lazy=l, mode=m, all=a)
    else:
        raise ValueError("Function to time unspecified")
