# MobilityAnalysis

The project consists of two parts:

`psense` – a Python module for data analysis in mobile networks.

`pvis` – a JavaScript module for in-browser data visualization via Leaflet and Mapbox.

The following is an overview of the modules' features.

### Dependencies

- pandas
- geopy
- ~~igraph~~

## Input/Output

JSON and CSV are the currently supported input-file types.

We assume *at least* the following entries are specified in the input data:

- `user_id`: The ID of the user corresponding to the entry.
- `lat`: The latitude of the geographical point in degrees.
- `lng`: The longitude of the geographical point in degrees.
- `created_at`: The timestamp (date and time) the entry was created at.

Utility methods for input and output are found in `psense.io_csv` and `psense.io_json`

For instance, to read in a bunch of CSV files you would do:

```python
from psense.io_csv import *
f = choose_files("local/data/path", filenumber=100)
df = build_df(f)
```

To write a GeoJSON file (for visualization purposes) call the method `write_geojson` on a DataFrame.

You can also use the command line interface for convenience. Run *psense/io_csv.py* directly to show valid options.

```bash
> python psense/io_csv.py
```

Edit psense/config.cfg conveniently to generate GeoJSON files from selected data and do (this gives you more control over the selected input files)

```bash
> python psense/io_csv.py -c psense/config.cfg
```

or pass parameters directly like so

```bash
> python psense/io_csv.py input/CSV/directory/ -n 10 -w geojson/data.geojson -p -l
```

This gathers the 10 newest CSV files in `input/CSV/directory/` and writes GeoJSON lines in `geojson/data.geojson` and points in `geojson/data-pts.geojson`.

To print out geometric statistics you run (for instance)

```sh
> python psense/io_csv.py input/CSV/directory/ -n 3 -s
Processing...
Loading file "163201665_tweets.csv"
Loading file "314226613_tweets.csv"
Loading file "47487483_tweets.csv"

Statistics:
           avg_locality  med_locality   radius_avg   radius_med
user_id
47487483       0.000002      0.000003  5173.649905  5214.953663
163201665      0.000032      0.000039   679.829722   688.902151
314226613      0.000002      0.000002  3576.990507  4335.761981
```

## Generating grids

Grids offer another, more efficient way of defining *rendezvous* in participatory sensing settings.

### Two-dimensional grids

The Grid class implements the discretization of an ellipsoidal surface for *time-independent* algorithms on a set of geographical points.

Use the class method `build` to build a Grid instance from a given DataFrame. You must specify the grid-size in kilometers, but the bounding box is optional:

```python
g = Grid.build(df, bbox=BBOX, gridsize=2.4)
```

The bounding box must be of the form [W, S, E, N]. You can get the bounding box of a specific area by its name by using `psense.util.bbox_from_name`.

### Three-dimensional grids

The TimeGrid class is an extension of the Grid class which supports operations related to time-relevant analysis. In essence, it just adds a third time dimension with a corresponding time-resolution (`tres`) parameter.

As before, the bounding box is not required, neither is the "temporal box". The time resolution, on the other hand, should be set in hours.

```python
tg = TimeGrid.build(df, bbox=BBOX, tbox=TBOX, gridsize=2.0, tres=24)
```

## Computing statistics

Use the command line interface `psense/io_csv.py -s` or directly call `psense.do_stats(df)` on an existing DataFrame to compute the geometric average (centroid), geometric median, radius and locality measures for each of the users.
