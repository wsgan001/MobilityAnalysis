#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Author: Alexis Luengas Zimmer
# Created: 5 Dec. 2014
#-------------------------------------------------------------------------------

import igraph as gr

#-------------------------------------------------------------------------------

def get_central_nodes(g, cmeasure):
    """
    Get the nodes maximizing a given centrality measure.

    Args:
        g (igraph.Graph): A non-empty graph
        cmeasure (string): one of the centrality measures: closeness,
            betweenness, eigenvector_centrality, alpha, authority_score,
            pagerank.
    """
    measures = [
        'closeness',
        'betweenness',
        'eigenvector_centrality',
        'alpha',
        'authority_score',
        'pagerank']

    if cmeasure in measures:
        if cmeasure == 'maxdegree':
            return g.vs.select(_degree=g.maxdegree())
        else:
            cm = eval('g.' + cmeasure)()
    elif callable(cmeasure) and hasattr(g, cmeasure.__name__):
        cm = cmeasure()
    maxNodes = [g.vs[i] for i, v in enumerate(cm) if v == max(cm)]
    return maxNodes
