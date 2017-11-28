#!/usr/bin/env python
'''
Do fun stuff to a connectivity graph
'''

import networkx
from wirecell import units

def neighbors_by_type(G, seed, typename, radius=1):
    '''
    Return a set of all neighbor nodes withing given radius of seed
    which are of the given typename.
    '''
    if radius == 1:
        return set([n for n in networkx.neighbors(G, seed) if G.node[n]['type'] == typename])

    return set([n for n in networkx.ego_graph(G, seed, radius) if G.node[n]['type'] == typename])

def neighbors_by_path(G, seed, typenamepath):
    '''
    Return all neighbor nodes by following a path of type names from
    given seed.
    '''
    if not typenamepath:
        return set()
    nn = neighbors_by_type(G, seed, typenamepath[0])
    for node in list(nn):
        nnn = neighbors_by_path(G, node, typenamepath[1:])
        nn.update(nnn)
    return nn

def parent(G, child, parent_type):
    '''
    Return parent node of given type 
    '''
    for n in networkx.neighbors(G, child):
        if G.node[n]['type'] == parent_type:
            return n
    return None
    

def channel_address(G, wire):
    '''
    Pull out the edge attributes
    '''

    conductor = parent(G, wire, 'conductor')
    channel = parent(G, conductor, 'channel')
    chip = parent(G, channel, 'chip')
    board = parent(G, chip, 'board')
    box = parent(G, board, 'face')
    wib = parent(G, board, 'wib')
    apa = parent(G, wib, 'apa')
    
    islot = G[apa][wib]['slot']
    iconn = G[wib][board]['connector']
    ichip = G[board][chip]['spot']
    iaddr = G[chip][channel]['address']
    return (iconn, islot, ichip, iaddr)

def channel_hash(iconn, islot, ichip, iaddr):
    return int("%d%d%d%02d" % (iconn+1, islot+1, ichip+1, iaddr+1))

def to_celltree_wires(G, face='face0'):
    '''
    Return list of tuples: (ch, plane, wip, sx, sy, sz, ex, ey, ez)

    corresponding to rows in the "ChannelWireGeometry" file used by

    https://github.com/bnlif/wire-cell-celltree

    for the wires in the given face.

    Note: this only returns the one face of wires but channel numbers
    are calculated with full knowledge of wrapped wires.
    '''
    ret = list()

    planes = list(neighbors_by_type(G, face, 'plane'))
    planes.sort(key = lambda p : G[face][p]['plane'])
    for plane in planes:
        wires = list(neighbors_by_type(G, plane, 'wire'))
        wires.sort(key = lambda w : G[plane][w]['wip'])
        iplane = G[face][plane]['plane']
        for wire in wires:
            iwire = G[plane][wire]['wip']

            pts = list(neighbors_by_type(G, wire, 'point'))[:2]
            head, tail = pts[0:2]
            if G[wire][head]['endpoint'] == 1:
                head, tail = pts[1], pts[0]
            ecm = [r/units.cm for r in G.node[head]['pos']]
            scm = [r/units.cm for r in G.node[tail]['pos']]

            channel = channel_hash(*channel_address(G, wire))
            one = [channel, iplane, iwire] + scm + ecm
            #print one
            ret.append(tuple(one))
    return ret

    
        

def wires_in_plane(G, plane):
    '''
    Return set of wire nodes connected to the given plane node.
    '''
    return neighbors_by_type(G, plane, 'wire')

def wires_in_chip(G, chip, intermediates=False):
    '''
    Return set of wire nodes connected to a chip node.  If
    intermediates is true, return the conductor and channel nodes that
    form the connection to the wires.
    '''
    channels = neighbors_by_type(G, chip, 'channel')
    conductors = set()
    for ch in channels:
        cs = neighbors_by_type(G, ch, 'conductor')
        conductors.update(cs)

    wires = set()
    for cond in conductors:
        w = neighbors_by_type(G, cond, 'wire')
        wires.update(w)

    if intermediates:
        return channels | conductors | wires
    return wires

def wires_graph(G, wires):
    '''
    Return a new graph with wire endpoints as nodes and a dictionary of 2D points
    '''
    newG = networkx.DiGraph()
    pos = dict()
    for wire in wires:
        pt1, pt2 = neighbors_by_type(G, wire, 'point')
        if G[wire][pt1]['endpoint'] == 2:
            pt1, pt2 = pt2, pt1
        pos1 = G.node[pt1]['pos']
        pos2 = G.node[pt2]['pos']
        pos[pt1] = (pos1.z, pos1.y)
        pos[pt2] = (pos2.z, pos2.y)
        newG.add_edge(pt1, pt2)
    return newG, pos

def conductors_graph(G, conductors):
    '''
    Like wires graph but swap sign of the 2D "X" (3D "Z") coordinates
    so a conductor zig-zags across a transparent frame.
    '''
    newG = networkx.DiGraph()
    pos = dict()
    for icond, cond in enumerate(conductors):
        wires = neighbors_by_type(G, cond, 'wire')
        for wire in wires:
            seg = G[cond][wire]['segment']
            sign = 1
            style="solid"
            if seg%2:
                sign = -1
                style="dashed"
            pt1, pt2 = neighbors_by_type(G, wire, 'point')        
            if G[wire][pt1]['endpoint'] == 2:
                pt1, pt2 = pt2, pt1
            pos1 = G.node[pt1]['pos']
            pos2 = G.node[pt2]['pos']
            pos[pt1] = (sign*pos1.z, pos1.y)
            pos[pt2] = (sign*pos2.z, pos2.y)
            newG.add_edge(pt1, pt2, style=style, icolor=icond)

    return newG, pos
