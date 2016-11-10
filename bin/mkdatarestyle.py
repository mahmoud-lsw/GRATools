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


"""Flux analysis
"""


import os
import imp
import numpy as np
import healpy as hp
import pyfits as pf

__description__ = 'Computes fluxes'



"""Command-line switches.
"""
import ast
import argparse
from scipy.optimize import curve_fit
from GRATools import GRATOOLS_OUT
from GRATools import GRATOOLS_CONFIG
from GRATools.utils.matplotlib_ import pyplot as plt
from GRATools.utils.logging_ import logger, startmsg

formatter = argparse.ArgumentDefaultsHelpFormatter
PARSER = argparse.ArgumentParser(description=__description__,
                                 formatter_class=formatter)
PARSER.add_argument('--config', type=str, required=True,
                    help='the input configuration file')
PARSER.add_argument('--udgrade', type=int, default=512,
                    help='down/up-grade of the maps')


def get_var_from_file(filename):
    f = open(filename)
    global data
    data = imp.load_source('data', '', f)
    f.close()

def mkRestyle(**kwargs):
    """
    """
    logger.info('Starting flux analysis...')
    get_var_from_file(kwargs['config'])
    fore_files = data.FORE_FILES_LIST
    macro_bins = data.MACRO_BINS
    gamma = data.POWER_LOW_INDEX
    out_label = data.OUT_LABEL
    binning_label = data.BINNING_LABEL
    in_labels_list = data.IN_LABELS_LIST
    new_txt_name = os.path.join(GRATOOLS_OUT, '%s_%s_parameters.txt' \
                                    %(out_label, binning_label))
    if os.path.exists(new_txt_name):
        new_txt_name = new_txt_name.replace('.txt','_2.txt')
    new_txt = open(new_txt_name,'w')
    new_txt.write('# \t E_MIN \t E_MAX \t E_MEAN \t F_MEAN \t FERR_MEAN \t CN \t FSKY \n')
    for i, (minb, maxb) in enumerate(macro_bins):
        mask_file = data.MASK_FILE
        if type(mask_file) == list:
            mask_file = mask_file[i]
        mask = hp.read_map(mask_file)
        _unmask = np.where(mask != 0)[0]
        maxb = maxb + 1
        logger.info('Considering bins from %i to %i...' %(minb, maxb-1))
        logger.info('Retriving count and exposure maps...')
        E_MIN, E_MAX, E_MEAN = 0, 0, 0
        count_map, exp_mean_map = [], []
        emin, emax, emean = [], [], []
        for label in in_labels_list:
            txt_name = os.path.join(GRATOOLS_OUT, '%s_outfiles.txt' %label)
            txt = open(txt_name,'r')
            logger.info('Ref: %s'%label)
            for line in txt:
                if 'gtbin' in line:
                    cmap = hp.read_map(line, field=range(minb, maxb))
                    cmap_repix = hp.pixelfunc.ud_grade(cmap,
                                                       kwargs['udgrade'], 
                                                       pess=True,
                                                       power=-2)
                    count_map.append(np.asarray(cmap_repix))
                    from  GRATools.utils.gFTools import get_energy_from_fits
                    emin, emax, emean = get_energy_from_fits(line,
                                                             minbinnum=minb,
                                                             maxbinnum=maxb)
                    
                    E_MIN, E_MAX = emin[0], emax[-1]
                    E_MEAN = (emax[0] + emin[-1])*0.5
                if 'gtexpcube2' in line:
                    emap = hp.read_map(line, field=range(minb, maxb+1))
                    emap_repix = hp.pixelfunc.ud_grade(emap,
                                                       kwargs['udgrade'], 
                                                       pess=True)
                    emap_mean = []
                    for i in range(0,len(emap_repix)-1):
                        emap_mean.append(np.sqrt(emap_repix[i]*emap_repix[i+1]))    
                    exp_mean_map.append(np.asarray(emap_mean))
            txt.close()
        logger.info('Summing in time...')
        all_counts, all_exps = count_map[0], exp_mean_map[0]
        for t in range(1, len(in_labels_list)):
            all_counts = all_counts + count_map[t]
            all_exps = all_exps + exp_mean_map[t]
        logger.info('Computing the flux for each micro energy bin...')
        flux_map = []
        nside = kwargs['udgrade']
        npix = hp.nside2npix(nside)
        sr = 4*np.pi/npix
        iii = np.arange(npix)
        for i, cmap in enumerate(all_counts):
            flux_map.append(cmap/all_exps[i]/sr)

        # now I have finelly gridded (in energy) summed in time fluxes
        logger.info('Rebinning...')
        logger.info('Merging fluxes from %.2f to %.2f MeV' %(E_MIN, E_MAX))
        from GRATools.utils.gFTools import get_foreground_integral_flux_map
        # implement fit of the foreground
        fore0 = get_foreground_integral_flux_map(fore_files,
                                                 emin[0], emax[0])
        fore0_max = fore0[np.argmax(fore0[_unmask])]
        vec0 = hp.pixelfunc.pix2vec(nside, np.argmax(fore0))
        region0 = hp.query_disc(nside, vec0, np.radians(2))
        region0 = np.array([i for i in region0 if not i in _unmask])
        fore0_max_region = np.average(fore0[region0])
        flux0_max_region = np.average(flux_map[0][region0])
        fore_norm0 = abs(fore0_max_region-flux0_max_region)/fore0_max_region
        logger.info('Foreground Normalization: %.3f'%fore_norm0)
        macro_flux = flux_map[0] - fore_norm0*fore0
        macro_fluxerr = (emean[0]/emean[0])**(-gamma)/(all_exps[0])**2
        CN = np.mean(all_counts[0][_unmask]/(all_exps[0][_unmask])**2)/sr
        for b in range(1, len(flux_map)):
            fore = get_foreground_integral_flux_map(fore_files,
                                                    emin[b], emax[b])
            fore_max = fore[np.argmax(fore)]
            vec = hp.pixelfunc.pix2vec(nside, np.argmax(fore))
            region = hp.query_disc(nside, vec, np.radians(1))
            region = np.array([i for i in region if not i in _unmask])
            fore_max_region = np.average(fore[region])
            flux_max_region = np.average(flux_map[b][region])
            fore_norm = abs(fore_max_region-flux_max_region)/fore_max
            logger.info('Foreground Normalization: %.3f'%fore_norm)
            macro_flux = macro_flux + flux_map[b] - fore_norm*fore
            macro_fluxerr = macro_fluxerr + \
                (emean[b]/emean[0])**(-gamma)/(all_exps[b])**2
            print 'Cn',b , np.mean(all_counts[b][_unmask]/ \
                                     (all_exps[b][_unmask])**2)/sr
            CN = CN + np.mean(all_counts[b][_unmask]/ \
                                     (all_exps[b][_unmask])**2)/sr            
        logger.info('CN (white noise) term = %e'%CN)
        macro_fluxerr = np.sqrt(all_counts[0]*macro_fluxerr)/sr
        """
        #now I want to subtract the foregrounds
        from GRATools.utils.gFTools import get_foreground_integral_flux_map
        fore_map = get_foreground_integral_flux_map(fore_files,
                                                    emin[0], emax[0])
        for e_min, e_max in zip(emin[1:], emax[1:]):
            fore = get_foreground_integral_flux_map(fore_files, 
                                                        e_min, e_max)
            fore_map = fore_map + fore
        macro_flux = macro_flux - fore_map
        """
        # now mask the rebinned flux and error maps        
        macro_flux_masked = hp.ma(macro_flux)
        macro_fluxerr_masked = hp.ma(macro_fluxerr)
        macro_flux_masked.mask = np.logical_not(mask)
        macro_fluxerr_masked.mask = np.logical_not(mask)
        out_folder = os.path.join(GRATOOLS_OUT, 'output_flux')
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        out_name = os.path.join(out_folder,out_label+'_flux_%i-%i.fits'\
                                      %(E_MIN, E_MAX))
        out_name_err = os.path.join(out_folder, out_label+'_fluxerr_%i-%i.fits'\
                                        %(E_MIN, E_MAX))
        logger.info('Created %s' %out_name)
        logger.info('Created %s' %out_name_err)
        hp.write_map(out_name, macro_flux_masked, coord='G')
        hp.write_map(out_name_err, macro_fluxerr_masked, coord='G')
        F_MEAN = np.sum(macro_flux[_unmask])/len(macro_flux[_unmask])
        FERR_MEAN = np.sqrt(np.sum(macro_fluxerr[_unmask]**2))/\
                                   len(macro_flux[_unmask])
        FSKY = float(len(macro_flux[_unmask]))/float(len(macro_flux))
        logger.info('Fsky = %.3f'%FSKY)
        print 'F_MEAN, FERR_MEAN = ', F_MEAN, FERR_MEAN
        new_txt.write('%.2f \t %.2f \t %.2f \t %e \t %e \t %e \t %f \n' \
                          %(E_MIN, E_MAX, E_MEAN, F_MEAN, FERR_MEAN, CN, FSKY))
    new_txt.close()
    logger.info('Created %s' %os.path.join(GRATOOLS_OUT, '%s_%s_parameters.txt'\
                                             %(out_label, binning_label)))
    
    logger.info('done!')


if __name__ == '__main__':
    args = PARSER.parse_args()
    startmsg()
    mkRestyle(**args.__dict__)
