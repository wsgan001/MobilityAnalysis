#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 5 Dec. 2014
#-------------------------------------------------------------------------------

from os.path import basename, isdir, dirname

import pandas as pd
import igraph as gr

#-------------------------------------------------------------------------------

def collect_data(json_files):
    """
    json_files: a list containing json path-strings

    Returns a sorted pandas.DataFrame object made up of all json objects
    together.
    """
    df_list = []

    print "Processing..."
    for filepath in json_files:
        print "\rLoading file \"%s\"" % basename(filepath)
        df = build_df(filepath)
        df_list.append(df)

    df = pd.concat(df_list) # merge list info one DF
    df.sort(inplace=True)

    return df

def build_df(json_path):
    df = pd.read_json(json_path)
    df["pid"] = [r["id"] for r in df.reporter] # pid ~ person id
    df["name"] = [r["name"] for r in df.reporter]
    df = df[["pid", "created_at", "lat", "lng", "name"]].sort(["pid", "created_at"]).set_index("pid")

    return df

def df_to_graph(df):
    # Build naked graph
    g = gr.Graph(len(df.index.levels[0][1:])) # slice out first (anonymous) id
    return g

#-------------------------------------------------------------------------------

def write_geojson(df, outpath):
    geojson = '{"type":"FeatureCollection","features":['

    for pid, fr in df[df.index > 0].groupby(level=0): # exclude id 0 (anonymous)
        name = df.ix[pid]["name"] if isinstance(df.ix[pid]["name"], unicode) \
            else df.ix[pid]["name"].iloc[0] # take the first name in the list
        geojson += ('{"type":"Feature","properties":{"id":'
            + str(pid)
            + ',"name":'
            + '"%s"' % name
            + '},"geometry":{"type":"LineString","coordinates":[')
        for i, r in fr.iterrows():
            c = "[{0},{1}],".format(r["lng"], r["lat"]) # geojson coordinates follow [lng, lat] formatting
            geojson += c
        geojson = geojson[:-1] + "]}}," # remove trailing comma of last coord.
    geojson = geojson[:-1] + "]}" # remove trailing comma of last path

    with open(outpath, "wt") as fout:
        fout.write(geojson.encode('utf-8'))

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    from optparse import OptionParser

    usage = "./%prog [options] path\n\npath -- the path of a JSON file or a directory containing such files."
    parser = OptionParser(usage=usage)
    parser.add_option("-w",
        dest="filename",
        type="string",
        help="write GeoJSON file to the specified path FILENAME")

    (options, args) = parser.parse_args()

    # terminal interface
    if len(args) > 0:
        from os import listdir
        from os.path import isfile, abspath, join, splitext

        # input path
        if isdir(args[0]):
            dirpath = args[0]
            json_files = [abspath(join(dirpath, f)) for f in listdir(dirpath) \
                if isfile(join(dirpath, f)) and splitext(f)[1] == '.json']
        elif all([isfile(a) for a in args]) \
            and all([a.endswith('.json') for a in args]):
            json_files = [abspath(f) for f in args]
        else:
            raise IOError("Files must be in JSON format")

        if len(json_files) == 0:
            raise IOError("No JSON files within the directory: " + dirpath)

        df = collect_data(json_files)

        if options.filename:
            write_geojson(df, options.filename)
            c = {'green': "\033[92m", 'endc': "\033[0m"}
            print c['green'] + "Data written to: " \
                + abspath(options.filename) + c['endc']
    else:
        parser.print_help()

#-------------------------------------------------------------------------------
