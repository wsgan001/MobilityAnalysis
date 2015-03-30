# ESTAData
Source code and documentation of the ESTAData Project. 
For more detailed information check the documentation provided in the **doc** folder.

Reference: 

Budde, Matthias, et al. "Leveraging spatio-temporal clustering for participatory urban infrastructure monitoring." Proceedings of the First International Conference on IoT in Urban Space. ICST (Institute for Computer Sciences, Social-Informatics and Telecommunications Engineering), 2014.

##Data Format & Loading
In order to successfully load the information from the csv/json files, they need
to provide certain information. Otherwise, the load functionality ends in fail-
ure. This is avoided if the data files contain the following columns with their
respective values:

• ’lng’ for longitude (a double precision floating point number).

• ’lat’ for latitude (a double precision floating point number).

• ’created at’ for the creation time of the report. For .csv files, the date
formatting should be ’yyyy-MM-dd HH:mm:ss’, for .json files: ’yyyy-MM-
dd’T’HH:mm:ss’ (a string).

• ’summary’ for the category of the report (a string).

• ’description’ for the user’s description of the report (a string).

• for the report’s URL address, ’bitly’ in case of .csv files, ’html url’ in case
of .json files (a string).

• ’id’ for the report’s ID (an integer).

• in case of .json files, ’reporter’ for the ID of the reporter (an integer).

To load data into Terracotta, execute:

*$ java [JVM args] -jar mining.jar --config CONFIG FILE --reportscache CACHE --load PATH --type [json|csv] --ratio R*

The JVM arguments tend to have a big impact in the performance of the framework. 
Especially, when loading big datasets, the JVM should have access to as much memory as possible. This is done using the 
flag -Xmx (e.g. -Xmx8G will allow the JVM heap to use up to 8G of memory).
Regarding the program arguments:

• CONFIG FILE is the path to the Terracotta configuration file,

• CACHE is the name of the Terracotta cache where the reports should be stored in,

• PATH is the path to a directory or single file containing the data (must be json or csv),

• and the ratio R is a parameter in range [0,1] signalizing which percentage
of the data should be loaded. Its default value is 1.0, and if minor to one,
the selected data is random (i.e. two executions using the same ratio could
result in different sets of data being loaded).

##Graph Generation
*$ java [JVM args] -jar mining.jar [config+cache] --mode filter -m M -d D*

As when loading data into Terracotta, it is important to provide the JVM 
with as much heap memory (flag -Xmx) as well as with off-heap memory (flag
-XX:MaxDirectMemorySize). Regarding the program arguments:

• config+cache: here, the configuration file of terracotta and the cache
containing the reports needs to be provided (see 3). However, a further
cache is also needed. In it, the clustering results are to be stored. This
cache is provided using the flag --clusterscache.

• --mode filter indicates the modality being executed. In future sections
we shall see the alternatives.

• -m M or --meters M indicates the maximal spatial distance M in meters
that two reports can have to be ST-connected.

• -d D or --days D indicates the maximal temporal distance D in days that
two reports can have to be ST-connected.

##Graph Clustering

*$ java [JVM args] -jar mining.jar [config+caches] --mode cluster --algorithm ALG [ARGS]*

Like before, the JVM arguments should assign the as much memory (on- and off-heap) 
as possible to the program. Just as well as before, config+caches contains the 
necessary information about the Terracotta configuration file and
the caches containing the reports and clusters. In this scenario we need a graph to work on. 
Therefore, the necessary caches should exist with the convention names (see full documentation).

Regarding the remaining arguments, --mode cluster indicates that the program must execute
a clustering algorithm over the graph; ALG is the algorithm to be executed, 
which can be one of the following: SCAN, louvain, louvain mlv (for Louvain with multilevel refinement) 
or slm (for smart local moving algorithm for large-scale modularity-based community detection). 
The last three are modularity based algorithms, and their provided implementations were taken from
http://www.ludowaltman.nl/slm/.
When using SCAN, ARGS consists of: --mu MU --eps EPS, which are the algorithm’s
parameters. If not provided, MU and EPS take the default values 2 and 0.7, respectively.
On the other hand, when using any of the modularity based algorithms, a wide set of arguments is available for the user:

• --modularity function FUNC: the modularity function to be used: standard (default) or alternative.

• --resoltion RESOL: the resolution parameter (default: 1.0).

• --random starts RANDS: the number of random starts executed by the algorithm, default: 10.

• --iterations ITER: the number of iterations per random start, default: 10.

• --random seed SEED: seed for the RNG, default: random.

For more detailed information about these arguments, we refer to the aforemen-
tioned website.
