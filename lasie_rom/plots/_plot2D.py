# -*- coding: utf-8 -*-
"""
Created on Tue Apr 11 12:25:57 2017

@author: afalaize
"""

from __future__ import absolute_import

import matplotlib.pyplot as plt
import numpy as np
from ..misc.tools import norm

NCOLS = None
CMAP = 'RdBu_r'
SIZE = None
FORMAT = 'png'
AXES = [0.88, 0.125, 0.01, 0.75]
PARAMS = {'left': 0.05,
          'bottom': 0.05,
          'right': 0.85,
          'top': 0.9,
          'wspace': None,
          'hspace': None}

CBAR = 'global'  # 'individual'

OPTIONS = {'ncols': NCOLS,
           'cmap': CMAP,
           'size': SIZE,
           'format': FORMAT,
           'axes': AXES,
           'params': PARAMS,
           'cbar': CBAR,
           }


def plot2d(a, shape, title=None, render='magnitude', savename=None, options=None):
    """
Plot of 2D data array.
    
Parameters
----------

a: array_like with shape (nx, nc, nm)
    array to plot where nx is the number of spatial discretization points, nc 
    is the number of spatial components, and nm is the number of elements to 
    plot.
    
shape: list of int
    Original grid shape (i.e. as returned by lasie_rom.grids.generate).
    
title: string (optional)

savename: string (optional)

options: dictionary (optional)
    options = {'ncols': None,
               'size': None,
               'format': 'png',
               'axes': [0.88, 0.125, 0.01, 0.75],
               'params': {'left': 0.05,
                          'bottom': 0.05,
                          'right': 0.85,
                          'top': 0.9,
                          'wspace': None,
                          'hspace': None},
               'cmap': 'RdBu_r',
               'cbar': 'global',
               }
    """
    

    opts = OPTIONS
    if options is None:
        options = {}
    opts.update(options)

    nx, nc, nm = a.shape
    ncols = opts['ncols']
    if ncols is None:
        ncols = int(np.ceil(np.sqrt(nm)))
    nrows = int(np.ceil(nm/float(ncols)))
    fig = plt.figure(figsize=opts['size'])

    if title is not None:
        plt.suptitle(title)

    all_v = list()
    minmax = (float('Inf'), -float('Inf'))
    for m in range(nm):
        d = a[:, :, m]
        if render == 'magnitude':
            v = norm(d)
        else:
            assert isinstance(render, int)
            assert 0 <= render < nc
            v = d[:, render]
        minmax = min([minmax[0], min(v)]), max([minmax[1], max(v)])
        all_v.append(v)
    for ind, v in enumerate(all_v):
        v_g = v.reshape(map(int, shape[1:]))
        plt.subplot(nrows, ncols, ind+1)
        plt.title('${}$'.format(ind))
        im = plt.imshow(v_g.T, cmap=opts['cmap'],
                        vmin=minmax[0], vmax=minmax[1])
        plt.axis('off')
        if opts['cbar'] == 'individual':
            plt.colorbar()
    if not opts['cbar'] == 'individual':
        if render == 'magnitude':
            cbar_label = 'Magnitude'
        else:
            assert isinstance(render, int)
            assert 0 <= render < nc
            cbar_label = 'Component {}'.format(render)
        cbar_ax = fig.add_axes(opts['axes'])
        fig.colorbar(im, cax=cbar_ax, label=cbar_label)
    plt.tight_layout()
    plt.subplots_adjust(**opts['params'])
    if savename is not None:
        plt.savefig('{}.{}'.format(savename, opts['format']),
                    format=opts['format'])
