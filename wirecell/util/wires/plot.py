
from wirecell import units
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy
from collections import defaultdict

def plot_polyline(pts):
    cmap = plt.get_cmap('seismic')
    npts = len(pts)
    colors = [cmap(i) for i in numpy.linspace(0, 1, npts)]
    for ind, (p1, p2) in enumerate(zip(pts[:-1], pts[1:])):
        x = numpy.asarray((p1.x, p2.x))
        y = numpy.asarray((p1.y, p2.y))
        plt.plot(x, y,  linewidth=ind+1)
    


def oneplane(store, iplane, segments=None):
    '''
    Plot one plane of wires.

    This plot is in protodune-numbers document.
    '''
    fig,axes = plt.subplots(nrows=1, ncols=3)

    uvw = "UVW"

    widths = [1, 2, 3]
    wire_stride=20;

    iface = 0
    face = store.faces[iface]

    cmap = plt.get_cmap('rainbow')

    for iplane in range(3):
        ax = axes[iplane]

        planeid = face.planes[iplane]
        plane = store.planes[planeid]

        wires = [w for w in plane.wires[::wire_stride]]

        nwires = len(wires)
        colors = [cmap(i) for i in numpy.linspace(0, 1, nwires)]

        for wcount, wind in enumerate(wires):

            wire = store.wires[wind]
            if segments and not wire.segment in segments:
                continue

            color = colors[wcount]
            if not iplane:
                color = colors[nwires-wcount-1]

            p1 = store.points[wire.tail]
            p2 = store.points[wire.head]
            width = widths[wire.segment]
            ax.plot((p1.z/units.meter, p2.z/units.meter), (p1.y/units.meter, p2.y/units.meter),
                        linewidth = width, color=color)

            ax.locator_params(axis='x', nbins=5)
            ax.set_aspect('equal', 'box')
            ax.set_xlabel("Z [meter]")
            if not iplane:
                ax.set_ylabel("Y [meter]")
            ax.set_title("plane %d/%s" % (iplane,uvw[iplane]))

    return fig,ax

def select_channels(store, pdffile, channels):
    '''
    Plot wires for select channels.
    '''
    channels = set(channels)
    bychan = defaultdict(list)

    # find selected wires and their wire-in-plane index
    # fixme: there should be a better way!
    for anode in store.anodes:
        for iface in anode.faces:
            face = store.faces[iface]
            for iplane in face.planes:
                plane = store.planes[iplane]
                for wip,wind in enumerate(plane.wires):
                    wire = store.wires[wind]
                    if wire.channel in channels:
                        bychan[wire.channel].append((wire, wip))

    fig, ax = plt.subplots(nrows=1, ncols=1)

    for ch,wws in sorted(bychan.items()):
        wws.sort(key=lambda ww: ww[0].segment)
        for wire, wip in wws:
            p1 = store.points[wire.tail]
            p2 = store.points[wire.head]
            width = wire.segment + 1
            ax.plot((p1.z/units.meter, p2.z/units.meter), (p1.y/units.meter, p2.y/units.meter), linewidth = width)
            x = p2.z/units.meter
            y = p2.y/units.meter
            t='w:%d ch:%d\nident:%d seg:%d' %(wip, wire.channel, wire.ident, wire.segment)
            if x > 0:
                hal="left"
            else:
                hal="right"
            ax.text(x, y, t,
                        horizontalalignment=hal,
                        bbox=dict(facecolor='yellow', alpha=0.5, pad=10))
            ax.set_xlabel("Z [meter]")
            ax.set_ylabel("Y [meter]")
    fig.savefig(pdffile)

    

def allplanes(store, pdffile):
    '''
    Plot each plane of wires on a page of a PDF file.
    '''
    wire_step = 10                            # how many wires to skip

    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(pdffile) as pdf:
        for anode in store.anodes:
            for iface in anode.faces:
                face = store.faces[iface]
                for iplane in face.planes:
                    plane = store.planes[iplane]

                    #print ("anode:%d face:%d plane:%d" % (anode.ident, face.ident, plane.ident))

                    fig, ax = plt.subplots(nrows=1, ncols=1)
                    ax.set_aspect('equal','box')
                    for wind in plane.wires[::wire_step]:
                        wire = store.wires[wind]
                        p1 = store.points[wire.tail]
                        p2 = store.points[wire.head]
                        width = wire.segment + .1
                        ax.plot((p1.z/units.meter, p2.z/units.meter),
                                (p1.y/units.meter, p2.y/units.meter), linewidth = width)

                    for wcount, wind in enumerate([plane.wires[0], plane.wires[-1]]):
                        wire = store.wires[wind]
                        print ("\twcount:%d wind:%d wident:%d chan:%d" % (wcount,wind,wire.ident,wire.channel))
                        p1 = store.points[wire.tail]
                        p2 = store.points[wire.head]
                        x = p2.z/units.meter
                        y = p2.y/units.meter
                        hal="center"
#                        if wcount == 1:
#                            hal = "right"
                            
                        t='wip:%d ch:%d' %(wire.ident, wire.channel)
                        ax.text(x, y, t,
                                    horizontalalignment=hal,
                                    bbox=dict(facecolor='yellow', alpha=0.5, pad=10))


                    ax.set_xlabel("Z [meter]")
                    ax.set_ylabel("Y [meter]")
                    ax.set_title("Anode %d, Face %d, Plane %d every %dth wire" % \
                                 (anode.ident, face.ident, plane.ident, wire_step))
                    pdf.savefig(fig)
                    plt.close()


def face_in_allplanes(store, iface=0, segments=None):
    fig = plt.figure()
    ax = fig.add_subplot(111)

    face = store.faces[iface]
    for planeid in face.planes:
        plane = store.planes[planeid]
        for wind in plane.wires[::20]:
            wire = store.wires[wind]
            if segments and not wire.segment in segments:
                continue

            p1 = store.points[wire.tail]
            p2 = store.points[wire.head]

            width = wire.segment + 1
            ax.plot((p1.z, p2.z), (p1.y, p2.y), linewidth = width)

    return fig,ax

def allwires(store):
    fig = plt.figure()
    ax = fig.add_subplot(111)

    iplane=0
    plane = store.planes[store.faces[0].planes[iplane]]
    wires = [store.wires[w] for w in plane.wires]
    nwires = len(wires)

    cmap = plt.get_cmap('seismic')
    colors = [cmap(i) for i in numpy.linspace(0, 1, nwires)]

    for iwire, wire in enumerate(wires):
        p1 = store.points[wire.tail]
        p2 = store.points[wire.head]

        color = colors[iwire]
        ax.plot((p1.z, p2.z), (p1.y, p2.y), color=color)

    return fig,ax





















def plot_rect(rect, color="black"):
    ax = plt.axes()
    ax.add_patch(mpatches.Rectangle(rect.ll, rect.width, rect.height,
                                        color=color, fill=False))
    ax.set_xlabel("APA-local Z")
    ax.set_ylabel("APA-local Y")
    ax.set_title("Looking in anti-drift direction")
    

def plot_polyline(pts):
    cmap = plt.get_cmap('seismic')
    npts = len(pts)
    colors = [cmap(i) for i in numpy.linspace(0, 1, npts)]
    for ind, (p1, p2) in enumerate(zip(pts[:-1], pts[1:])):
        x = numpy.asarray((p1.x, p2.x))
        y = numpy.asarray((p1.y, p2.y))
        plt.plot(x, y,  linewidth=ind+1)
    

def plotwires(wires):
    cmap = plt.get_cmap('seismic')
    nwires = len(wires)

    chans = [w[2] for w in wires]
    minchan = min(chans)
    maxchan = max(chans)
    nchans = maxchan - minchan + 1

    colors = [cmap(i) for i in numpy.linspace(0, 1, nchans)]
    for ind, one in enumerate(wires):
        pitch, side, ch, seg, p1, p2 = one
        linestyle = 'solid'
        if side < 0:
            linestyle = 'dashed'
        color = colors[ch-minchan]

        x = numpy.asarray((p1.x, p2.x))
        y = numpy.asarray((p1.y, p2.y))
        plt.plot(x, y, color=color, linewidth = seg+1, linestyle = linestyle)

def plot_wires_sparse(wires, indices, group_size=40):
    for ind in indices:
        plotwires([w for w in wires if w[2]%group_size == ind])


def plot_some():
    rect = Rectangle(6.0, 10.0)
    plt.clf()
    direc = Point(1,-1);
    for offset in numpy.linspace(.1, 6, 60):
        start = Point(-3.0 + offset, 5.0)
        ray = Ray(start, start+direc)
        pts = wrap_one(ray, rect)
        plot_polyline(pts)


        

def plot_wires(wobj, wire_filter=None):
    bbmin, bbmax = wobj.bounding_box
    xmin, xmax = bbmin[2],bbmax[2]
    ymin, ymax = bbmin[1],bbmax[1]
    dx = xmax-xmin
    dy = ymax-ymin
    wires = wobj.wires

    #print (xmin,ymin), (dx,dy)
    #print bbmin, bbmax

    wirenums = [w.wire for w in wires]
    minwire = min(wirenums)
    maxwire = max(wirenums)
    nwires = maxwire-minwire+1

    if wire_filter:
        wires = [w for w in wires if wire_filter(w)]
        print ("filter leaves %d wires" % len(wires))
    ax = plt.axes()
    ax.set_aspect('equal', 'box') #'datalim')
    ax.add_patch(mpatches.Rectangle((xmin, ymin), dx, dy,
                                    color="black", fill=False))

    cmap = plt.get_cmap('rainbow')        # seismic is bluewhitered

    colors = [cmap(i) for i in numpy.linspace(0, 1, nwires)]
    for ind, one in enumerate(wires):
        color = colors[one.wire-minwire]
        x = numpy.asarray((one.beg[2], one.end[2]))
        y = numpy.asarray((one.beg[1], one.end[1]))
        plt.plot(x, y, color=color)

    plt.plot([ xmin + 0.5*dx ], [ ymin + 0.5*dy ], "o")

    plt.axis([xmin,xmax,ymin,ymax])
    
