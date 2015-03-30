#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 5 Dec. 2014
#-------------------------------------------------------------------------------

from os import listdir
from os.path import abspath, join, splitext, isfile, isdir, dirname, getmtime, getsize, basename
import random as rdm

import pandas as pd

from psense.stats import do_stats

#-------------------------------------------------------------------------------

def choose_files(dirpath, filenumber=None, size=[], newest=True, random=False):
    csv_files = [abspath(join(dirpath, f)) for f in listdir(dirpath) \
        if isfile(join(dirpath, f)) and splitext(f)[1] == '.csv']

    if not csv_files:
        raise IOError("No CSV files within the specified directory: " + dirpath)

    if not random:
        csv_files.sort(key=getmtime, reverse=newest)
    else:
        rdm.shuffle(csv_files)

    if size:
        assert len(size) == 2
        minsize, maxsize = size
        csv_files = [f for f in csv_files if getsize(f) >= minsize and getsize(f) < maxsize]

    if not csv_files:
        raise IOError("No CSV files matching the conditions: %sB <= file size < %sB" % (minsize, maxsize))

    return csv_files[:filenumber]

def build_df(csv_files):
    """
    Returns a sorted pandas.DataFrame object made up of all csv objects
    together.

    Expects a list if CSV paths with at least 'user_id', 'lat' and 'lng' entries.
    """
    df_list = []

    print "Processing..."
    for filepath in csv_files:
        print "\rLoading file \"%s\"" % basename(filepath)
        df = pd.read_csv(filepath)
        df.set_index("user_id", inplace=True)
        df.index.name = "user_id"
        df_list.append(df)

    df = pd.concat(df_list) # merge list info one DF
    df.sort(inplace=True)
    df['created_at'] = pd.to_datetime(df['created_at'])
    return df

#-------------------------------------------------------------------------------

def write_geojson(df, outpath, toPoints=False):
    geojson = '{"type":"FeatureCollection","features":['

    for i, (uid, fr) in enumerate(df.groupby(level="user_id")):
        geomType = "MultiPoint" if toPoints else "LineString"
        geojson += '{"type":"Feature","properties":{"number":%s,"id":%s},"geometry":{"type":"%s","coordinates":[' % (i, uid, geomType)
        for i, r in fr.iterrows():
            c = "[%s,%s]," % (r["lng"], r["lat"]) # geojson [lng, lat] standard  layout
            geojson += c
        geojson = geojson[:-1] + "]}}," # remove trailing comma of last coord.
    geojson = geojson[:-1] + "]}" # remove trailing comma of last path

    with open(outpath, "wt") as fout:
        fout.write(geojson.encode('utf-8'))

#-------------------------------------------------------------------------------

def print_success(arg):
    c = {'green': "\033[92m", 'endc': "\033[0m"}
    print c['green'] + arg + c['endc']

def stats_callback(option, opt_str, value, parser):
    if parser.rargs and not parser.rargs[0].startswith('-'):
        value = parser.rargs.pop(0)
    else:
        value = True
    setattr(parser.values, option.dest, value)

if __name__ == '__main__':
    from optparse import OptionParser

    usage = "./%prog [options] path\n\npath -- the path of a CSV file or a directory containing such files."
    parser = OptionParser(usage=usage)
    parser.add_option("-n",
        dest="nfiles",
        type="int",
        default=None,
        help="number of files to get from the directory.")
    parser.add_option("-w", "-o",
        dest="filename",
        type="string",
        help="write GeoJSON file to the specified path FILENAME.")
    parser.add_option("-p",
        dest="toPoints",
        action="store_true",
        default=False,
        help="write as collection of points instead of lines.")
    parser.add_option("-l",
        dest="toLines",
        action="store_true",
        default=True,
        help="write as collection of lines (default if -p not present).")
    parser.add_option("-c", "--config",
        dest="configfile",
        type="string",
        help="read parameters from a given configuration file. If present, passed arguments are overridden by these parameters.")
    parser.add_option("-s",
        dest="statsfile",
        action="callback",
        callback=stats_callback,
        help="print out the stats (with no arguments) or write the stats to STATSFILE.")

    (options, args) = parser.parse_args()

    # terminal interface
    if len(args) > 0 or options.configfile:
        from os import listdir
        from os.path import isfile, abspath, join, splitext

        # configuration file
        if options.configfile:
            import ConfigParser
            from ast import literal_eval as leval

            config = ConfigParser.RawConfigParser()
            config.read(options.configfile)

            getcfg = lambda x: leval(config.get('params', x))

            args = [config.get('paths', 'inputdir')]
            options.filename = config.get('paths', 'geojsonfile')
            options.nfiles = getcfg('filenumber')
            options.toLines = getcfg('points')
            options.toPoints = getcfg('lines')

            extraparams = {}
            present = set(['size', 'newest', 'random']) \
                .intersection(config.options('params'))
            for opt in present:
                extraparams[opt] = getcfg(opt)

        # input path
        if isdir(args[0]):
            dirpath = args[0]
            csv_files = choose_files(dirpath, options.nfiles, **extraparams)
        elif all([isfile(a) for a in args]) \
            and all([a.endswith('.csv') for a in args]):
            csv_files = [abspath(f) for f in args]
        else:
            raise IOError("Files must be in CSV format")

        # build dataframe
        df = build_df(csv_files)

        if options.toPoints and not options.filename:
            parser.error('Filename not given')

        # output
        if options.filename:
            outpaths = []
            if options.toPoints:
                fname = options.filename
                if options.toLines:
                    fname = fname[:fname.find(".geojson")] + "-pts.geojson"
                    write_geojson(df, options.filename)
                    outpaths.append(abspath(options.filename))
                write_geojson(df, fname, toPoints=True)
                outpaths.append(abspath(fname))
            else:
                write_geojson(df, options.filename)
                outpaths.append(abspath(options.filename))
            print_success("Data written to: " + "\n".join(outpaths))

        if options.statsfile:
            stats = do_stats(df)
            if isinstance(options.statsfile, str):
                with open(options.statsfile, 'wt') as f:
                    stats.to_csv(f)
                print_success("Stats written to: " + abspath(options.statsfile))
            else:
                pd.set_option('precision', 7)
                print "\nStatistics:"
                print stats
    else:
        parser.print_help()

#-------------------------------------------------------------------------------
