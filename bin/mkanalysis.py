#!/usr/bin/env python                                                          #
#                                                                              #
# Autor: Michela Negro, University of Torino.                                  #
# On behalf of the Fermi-LAT Collaboration.                                    #
#                                                                              #
# This program is free software; you can redistribute it and/or modify         #
# it under the terms of the GNU GengReral Public License as published by       #
# the Free Software Foundation; either version 3 of the License, or            #
# (at your option) any later version.                                          #
#                                                                              #
#------------------------------------------------------------------------------#


"""Analysis module
"""


import os
import imp
import numpy as np
import healpy as hp
import pyfits as pf


__description__ = 'Makes the analysis'



"""Command-line switches.
"""

import argparse
from GRATools import GRATOOLS_OUT
from GRATools.utils.logging_ import logger, startmsg
from GRATools.utils.matplotlib_ import pyplot as plt
from GRATools.utils.matplotlib_ import overlay_tag, save_current_figure

GRATOOLS_OUT_FLUX = os.path.join(GRATOOLS_OUT, 'output_flux')

formatter = argparse.ArgumentDefaultsHelpFormatter
PARSER = argparse.ArgumentParser(description=__description__,
                                 formatter_class=formatter)
PARSER.add_argument('--config', type=str, required=True,
                    help='the input configuration file')

def get_var_from_file(filename):
    f = open(filename)
    global data
    data = imp.load_source('data', '', f)
    f.close()

def mkAnalysis(**kwargs):
    """
    """
    logger.info('Starting analysis...')
    get_var_from_file(kwargs['config'])
    files_dict = data.FILES_DICT
    out_label = data.OUT_LABEL
    ebinning_file = data.EBINNING_FILE
    from  GRATools.utils.gFTools import get_energy_from_txt
    _emean, _emin, _emax = get_energy_from_txt(ebinning_file, get_binning=True)
    final_maps = []
    _fmean = [0]*len(_emean)
    for bin, labels in files_dict.iteritems():
        flux_bin = []
        _index = []
        bin_num = labels[0]
        en, emin, emax = _emean[bin_num], _emin[bin_num], _emax[bin_num]
        logger.info('considering bin: %i MeV...' %int(en))
        for label in labels[1:]:
            flux_map_name = label+'_flux_'+ bin + '.fits'
            flux_map = hp.read_map(os.path.join(GRATOOLS_OUT_FLUX, \
                                                    flux_map_name ))
            _index = np.where(flux_map != hp.UNSEEN)[0]
            flux_bin.append(flux_map)
        flux_bin_sum = flux_bin[0]
        for m in flux_bin[1:]:
            flux_bin_sum[_index] = flux_bin_sum[_index] + m[_index]
        final_maps.append(flux_bin_sum)
        mean_flux = np.sum(flux_bin_sum[_index])/len(flux_bin_sum[_index])
        _fmean[bin_num] = mean_flux
        out_name = os.path.join(GRATOOLS_OUT_FLUX, '%s_flux_%i-%i.fits' \
                                    %(out_label, int(emin), int(emin)) )
        hp.write_map(out_name, flux_bin_sum, coord='G')
        logger.info('Created %s' %out_name)

    plt.figure(figsize=(10, 7), dpi=80)
    _fmean = np.array(_fmean)
    plt.loglog(_emean, _fmean*_emean*_emean, 'o', basex=10, basey=10)
    plt.xlabel('Energy [MeV]')
    plt.ylabel('E$^{2}$ $\cdot$ Flux [MeV$^{-1}$ cm$^{-2}$ s$^{-1}$ sr$^{-1}$]')
    plt.title('Extra-Galactic Energy Spectrum')
    overlay_tag()
    save_current_figure(out_label+'_ESpec.png')    


if __name__ == '__main__':
    args = PARSER.parse_args()
    startmsg()
    mkAnalysis(**args.__dict__)