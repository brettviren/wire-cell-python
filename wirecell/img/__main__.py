#!/usr/bin/env python
'''
The wirecell-img main
'''
import os
import json
import click
import pathlib
from collections import Counter
import numpy
import matplotlib.pyplot as plt
from wirecell import units
from wirecell.util.functions import unitify

cmddef = dict(context_settings = dict(help_option_names=['-h', '--help']))

@click.group("img", **cmddef)
@click.pass_context
def cli(ctx):
    '''
    Wire Cell Toolkit Imaging Commands

    A cluster file is produced by ClusterFileSink and is an archive
    holding JSON or Numpy or as a special case may be a single JSON.

    '''

@cli.command("inspect")
@click.argument("cluster-file")
@click.pass_context
def inspect(ctx, cluster_file):
    '''
    Inspect a cluster file
    '''
    from . import converter, tap, clusters

    path = pathlib.Path(cluster_file)
    if not path.exists():
        print(f'no such file: {path}')
        return

    if path.name.endswith(".json"):
        print ('JSON file assuming from JsonClusterTap')
    elif '.tar' in path.name:
        print ('TAR file assuming from ClusterFileSink')

    graphs = list(tap.load(str(path)))
    print (f'number of graphs: {len(graphs)}')
    for ig, gr in enumerate(graphs):
        cm = clusters.ClusterMap(gr)

        print(f'{ig}: {gr.number_of_nodes()} vertices, {gr.number_of_edges()} edges')
        counter = Counter(dict(gr.nodes(data='code')).values())
        for code, count in sorted(counter.items()):
            print(f'\t{code}: {count} nodes')

            if code == 'b':
                q = sum([n['value'] for c,n in gr.nodes(data=True) if n['code'] == code])
                print(f'\t\ttotal charge: {q}')
                continue

            if code == 's':
                q=0
                for snode in cm.nodes_oftype('s'):
                    sdat = cm.gr.nodes[snode]
                    sig = sdat['signal']
                    q += sum([v['val'] for v in sig.values()])
                print(f'\t\ttotal charge: {q}')
                continue
        

@cli.command("paraview-blobs")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.argument("cluster-file")
@click.argument("paraview-file")
@click.pass_context
def paraview_blobs(ctx, speed, cluster_file, paraview_file):
    '''
    Convert a cluster file to a ParaView .vtu files of blobs

    A drift speed is used to convert the "x" dimension from time to
    distance.  Default "1.6*mm/us".
    '''
    from . import converter, tap
    from tvtk.api import write_data

    if not paraview_file.endswith(".vtu"):
        print ("warning: blobs are written as UnstructuredGrid and paraview expects a .vtu extension")

    speed = unitify(speed)
    
    def do_one(gr, n=0):
        gr = converter.undrift(gr, speed)
        if 0 == gr.number_of_nodes():
            click.echo("no verticies in %s" % cluster_file)
            return
        dat = converter.clusters2blobs(gr)
        fname = paraview_file
        if '%' in paraview_file:
            fname = paraview_file%n
        write_data(dat, fname)
        click.echo(fname)

    for n, gr in enumerate(tap.load(cluster_file)):
        do_one(gr, n)

    return


@cli.command("paraview-activity")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.argument("cluster-file")
@click.argument("paraview-file")
@click.pass_context
def paraview_activity(ctx, speed, cluster_file, paraview_file):
    '''
    Convert cluster files to ParaView .vti files of activity
    '''
    from . import converter, tap
    from tvtk.api import write_data
    
    if not paraview_file.endswith(".vti"):
        print("warning: activity is saved as an image and paraview expects a .vti extension")

    speed = unitify(speed)

    def do_one(gr, n=0):
        gr = converter.undrift(gr, speed)
        fname,ext=os.path.splitext(paraview_file)
        if '%' in fname:
            fname = fname%n

        if 0 == gr.number_of_nodes():
            click.echo("no verticies in %s" % cluster_file)
            return
        alldat = converter.clusters2views(gr)
        for wpid, dat in alldat.items():
            pname = f'{fname}-plane{wpid}{ext}'
            write_data(dat, pname)
            click.echo(pname)

    for n, gr in enumerate(tap.load(cluster_file)):
        do_one(gr, n)

    return


@cli.command("paraview-depos")
@click.option("--speed", default="1.6*mm/us",
              help="Apply a drift speed")
@click.argument("depo-npz-file")
@click.argument("paraview-file")
@click.pass_context
def paraview_depos(ctx, speed, depo_npz_file, paraview_file):
    '''
    Convert an NPZ file to a ParaView .vtp file of depos.

    If depos are pre-drift then speed should be set to 0.

    The default is non-zero assuming the depos are post-drift and the
    speed will be used to modify the depo "x" coordinate based on its
    "t".  Using zero speed on post-drift depos causes them all to
    appear "bunched up" on the response plane.
    '''
    from . import converter
    from tvtk.api import write_data
    
    if not paraview_file.endswith(".vtp"):
        print("Warning: depos are saved as PolyData, paraview expects a .vtp extension")

    speed = unitify(speed)

    fp = numpy.load(depo_npz_file)
    dat = fp['depo_data_0']

    # ((t,q,x,y,z,dl,dt), N)
    dat[2] -= dat[0]*speed

    ugrid = converter.depos2pts(dat);
    write_data(ugrid, paraview_file)
    click.echo(paraview_file)
    return

#    Bee support:   
#    http://bnlif.github.io/wire-cell-docs/viz/uploads/


@cli.command("bee-blobs")
@click.option('-o', '--output', help="The output Bee JSON file name")
@click.option('-g', '--geom', default="protodune",
              help="The name of the detector geometry")
@click.option('--rse', nargs=3, type=int, default=[0, 0, 0],
              help="The '<run> <subrun> <event>' numbers as a triple of integers")
@click.option('-s', '--sampling', type=click.Choice(["center","uniform"]), default="uniform",
              help="The sampling technique to turn blob volumes into points")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.option('-d', '--density', type=float, default=9.0,
              help="For samplings which care, specify target points per cc")
@click.argument("cluster-files", nargs=-1)
def bee_blobs(output, geom, rse, sampling, speed, density, cluster_files):
    '''
    Produce a Bee JSON file from a cluster file.
    '''
    from . import tap, converter

    speed = unitify(speed)

    dat = dict(runNo=rse[0], subRunNo=rse[1], eventNo=rse[2], geom=geom, type="wire-cell",
               x=list(), y=list(), z=list(), q=list()) # , cluster_id=list()

    def fclean(arr):
        return [round(a, 3) for a in arr]
        
    # given by user in units of 1/cc.  Convert to system of units 1/L^3.
    density *= 1.0/(units.cm**3)
    sampling_func = dict(
        center = converter.blob_center,
        uniform = lambda b : converter.blob_uniform_sample(b, density),
    )[sampling];

    for ctf in cluster_files:
        gr = list(tap.load(ctf))[0] # fixme: for now ignore subsequent graphs
        gr = converter.undrift(gr, speed)
        print ("got %d" % gr.number_of_nodes())
        if 0 == gr.number_of_nodes():
            print("skipping empty graph %s" % ctf)
            continue
        arr = converter.blobpoints(gr, sampling_func)
        print ("%s: %d points" % (ctf, arr.shape[0]))
        dat['x'] += fclean(arr[:,0]/units.cm)
        dat['y'] += fclean(arr[:,1]/units.cm)
        dat['z'] += fclean(arr[:,2]/units.cm)
        dat['q'] += fclean(arr[:,3])

    import json
    # monkey patch
    from json import encoder
    encoder.FLOAT_REPR = lambda o: format(o, '.3f')
    json.dump(dat, open(output,'w', encoding="utf8"))

#   Export 3D charge points for the use of JsonDepoSource
#   ref: wire-cell-toolkit/sio/JsonDepoSource.cxx
@cli.command("json-depos")
@click.option('-o', '--output', help="The output JSON depo file name")
@click.option('-s', '--sampling', type=click.Choice(["center","uniform"]), default="uniform",
              help="The sampling technique to turn blob volumes into points")
@click.option('-d', '--density', type=float, default=9.0,
              help="For samplings which care, specify target points per cc")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.option('-n', '--number', type=int, default=-1,
              help="The number of electrons per depo point")
@click.argument("cluster-files", nargs=-1)
def json_depos(output, sampling, speed, density, number, cluster_files):
    '''
    Make one JSON depo file from the blobs in a set of cluster files
    which are presumed to originate from one trigger.
    '''
    from . import tap, converter

    speed = unitify(speed)
    
    dat = dict(depos=list())
        
    # given by user in units of 1/cc.  Convert to system of units 1/L^3.
    density *= 1.0/(units.cm**3)
    sampling_func = dict(
        center = converter.blob_center,
        uniform = lambda b : converter.blob_uniform_sample(b, density),
    )[sampling];

    for ctf in cluster_files:
        gr = list(tap.load(ctf))[0] # fixme
        gr = converter.undrift(gr, speed)
        print ("got %d" % gr.number_of_nodes())
        if 0 == gr.number_of_nodes():
            print("skipping empty graph %s" % ctf)
            continue
        arr = converter.blobpoints(gr, sampling_func)
        print ("%s: %d points" % (ctf, arr.shape[0]))
        for depo in arr:
            onedepo = dict(n=round(depo[3], 3) if number<0 else number,
                           q=0, s=0, t=0*units.microsecond,
                           x=round(depo[0], 3)/units.mm,
                           y=round(depo[1], 3)/units.mm,
                           z=round(depo[2], 3)/units.mm)
            x = onedepo['x']
            y = onedepo['y']
            z = onedepo['z']
            dat['depos'] += [onedepo]
            # if x>-3100 and x<-1800 and y>2800 and y<6000 and z>3000 and z<4500:
            #     t0 = -1194.0 # microsecond
            #     onedepo['x'] -= t0* 1.6
            #     onedepo['t'] = t0*units.microsecond
            #     dat['depos'] += [onedepo]

    dat['depos'] += [dict()] # EOS

    import json
    # monkey patch
    from json import encoder
    encoder.FLOAT_REPR = lambda o: format(o, '.3f')
    json.dump(dat, open(output,'w', encoding="utf8"))


def divine_planes(nch):
    '''
    Return list of channels in each plane based on total.
    '''
    if nch == 2560:             # protodune
        return [400, 400, 400, 400, 480, 480]
    if nch == 8256:             # microboone
        return [2400, 2400, 3456]
    print(f'not a canonical number of channels in a known detector: {nch}')
    return [nch]

@cli.command("activity")
@click.option('-o', '--output', help="The output plot file name")
@click.option('-s', '--slices', nargs=2, type=int, 
              help="Range of slice IDs")
@click.option('-S', '--slice-line', type=int, default=-1,
              help="Draw a line down a slice")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.argument("cluster-file")
def activity(output, slices, slice_line, speed, cluster_file):
    '''
    Plot activity
    '''
    from matplotlib.colors import LogNorm
    from . import tap, clusters, plots

    speed = unitify(speed)

    gr = list(tap.load(cluster_file))[0]
    gr = converter.undrift(gr, speed)
    cm = clusters.ClusterMap(gr)
    ahist = plots.activity(cm)
    arr = ahist.arr
    print(f'channel x slice array shape: {arr.shape}')
    extent = list()
    if slices:
        arr = arr[:,slices[0]:slices[1]]
        extent = [slices[0], slices[1]]
    else:
        extent = [0, arr.shape[1]]
    extent += [ahist.rangey[1], ahist.rangey[0]]

    fig,ax = plt.subplots(nrows=1, ncols=1)
    fig.set_size_inches(8.5,11.0)

    cmap = plt.get_cmap('gist_rainbow')
    im = ax.imshow(arr, cmap=cmap, interpolation='none', norm=LogNorm(), extent=extent)
    if slice_line > 0:
        ax.plot([slice_line, slice_line], [ahist.rangey[0], ahist.rangey[1]],
                linewidth=0.1, color='black')

    boundary = 0
    for chunk in divine_planes(arr.shape[0]):
        boundary += chunk
        y = boundary + ahist.rangey[0]
        ax.plot(extent[:2], [y,y], color='gray', linewidth=0.1);

    from matplotlib.ticker import  AutoMinorLocator
    minorLocator = AutoMinorLocator()
    ax.yaxis.set_minor_locator(minorLocator)
    ax.tick_params(which="both", width=1)
    ax.tick_params(which="major", length=7)
    ax.tick_params(which="minor", length=3)

    try:
        plt.colorbar(im, ax=ax)
    except ValueError:
        print("colorbar complains, probably have zero data")
        print('total:', numpy.sum(arr))
        return
        pass
    ax.set_title(cluster_file)
    ax.set_xlabel("slice ID")
    ax.set_ylabel("channel IDs")
    fig.savefig(output)


@cli.command("blob-activity-mask")
@click.option('-o', '--output', help="The output plot file name")
@click.option('-s', '--slices', nargs=2, type=int, 
              help="The output plot file name")
@click.option('-S', '--slice-line', type=int, default=-1,
              help="Draw a line down a slice")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.option('--found/--missed', default=True,
              help="Mask what blobs found or missed")
@click.argument("cluster-file")
def blob_activity_mask(output, slices, slice_line, speed, found, cluster_file):
    '''
    Plot blobs as maskes on channel activity.
    '''
    from . import tap, clusters, plots

    speed = unitify(speed)

    gr = list(tap.load(cluster_file))[0] # fixme
    gr = converter.undrift(gr, speed)
    cm = clusters.ClusterMap(gr)
    ahist = plots.activity(cm)
    bhist = ahist.like()
    plots.blobs(cm, bhist)
    if found:
        sel = lambda a: a>= 1
        title="found mask"
    else:
        sel = lambda a: a < 1
        title="missed mask"
    extent = list()
    if slices:
        a = ahist.arr[:,slices[0]:slices[1]]
        b = bhist.arr[:,slices[0]:slices[1]]
        extent = [slices[0], slices[1]]
    else:
        a = ahist.arr
        b = bhist.arr
        extent = [0, a.shape[1]]
    extent += [ahist.rangey[1], ahist.rangey[0]]

    fig,ax = plots.mask_blobs(a, b, sel, extent)
    if slice_line > 0:
        ax.plot([slice_line, slice_line], [ahist.rangey[0], ahist.rangey[1]],
                linewidth=0.1, color='black')
    ax.set_title("%s %s" % (title, cluster_file))
    ax.set_xlabel("slice ID")
    ax.set_ylabel("channel IDs")
    fig.savefig(output)


@cli.command("wire-slice-activity")
@click.option('-o', '--output', help="The output plot file name")
@click.option('-s', '--sliceid', type=int, help="The slice ID to plot")
@click.option("--speed", default="1.6*mm/us",
              help="Drift speed (with units)")
@click.argument("cluster-file")
def wire_slice_activity(output, sliceid, speed, cluster_file):
    '''
    Plot the activity in one slice as wires and blobs
    '''
    from . import tap, clusters, plots
    speed = unitify(speed)
    gr = next(tap.load(cluster_file))
    gr = converter.undrift(gr, speed)
    cm = clusters.ClusterMap(gr)
    fig, axes = plots.wire_blob_slice(cm, sliceid)
    fig.savefig(output)


@cli.command("anidfg")
@click.option("-o", "--output", default="anidfg.gif", help="Output file")
@click.argument("logfile")
def anidfg(output, logfile):
    '''
    Produce an animated graph visualization from a log produced by
    TbbFlow with "dfg" output.
    '''
    from . import anidfg
    log = anidfg.parse_log(open(logfile))
    ga = anidfg.generate_graph(log)
    anidfg.render_graph(ga, output)


def main():
    cli(obj=dict())

if '__main__' == __name__:
    main()
    
    
