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
from  GRATools.utils.gFTools import get_energy_from_fits
from GRATools.utils.gFTools import get_crbkg
from GRATools.utils.gSpline import xInterpolatedUnivariateSplineLinear

formatter = argparse.ArgumentDefaultsHelpFormatter
PARSER = argparse.ArgumentParser(description=__description__,
                                 formatter_class=formatter)
PARSER.add_argument('--config', type=str, required=True,
                    help='the input configuration file')
PARSER.add_argument('--udgrade', type=int, default=512,
                    help='down/up-grade of the maps')
PARSER.add_argument('--foresub', type=ast.literal_eval, choices=[True, False],
                    default=False,
                    help='galactic foreground subtractin activated')

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
    crbkg_file = data.CRBKG_FILE
    macro_bins = data.MACRO_BINS
    gamma = data.POWER_LOW_INDEX
    out_label = data.OUT_LABEL
    mask_label = data.MASK_LABEL
    binning_label = data.BINNING_LABEL
    in_labels_list = data.IN_LABELS_LIST
    new_txt_name = os.path.join(GRATOOLS_OUT, '%s_%s_%s_parameters.txt' \
                                    %(out_label, mask_label, binning_label))
    if os.path.exists(new_txt_name):
        new_txt_name = new_txt_name.replace('.txt','_2.txt')
    new_txt = open(new_txt_name,'w')
    new_txt.write('# \t E_MIN \t E_MAX \t E_MEAN \t F_MEAN \t FERR_MEAN \t CN \t FSKY \n')
    norm_list = []
    const_list = []
    fore_mean_list = []
    #all_counts, all_exps = [], []
    #flux_map = []
    for i, (minb, maxb) in enumerate(macro_bins):
        all_counts, all_exps = [], []
        flux_map = []
        micro_bins = np.arange(minb, maxb+1)
        print micro_bins
        logger.info('Considering bins from %i to %i...' %(minb, maxb-1))
        mask_file = data.MASK_FILE
        if type(mask_file) == list:
            mask_file = mask_file[i]
        mask = hp.read_map(mask_file)
        _unmask = np.where(mask != 0)[0]
        maxb = maxb + 1
        exists_counts_files, exists_exp_files = [], []
        for mb in micro_bins:
            micro_count_name = os.path.join(GRATOOLS_OUT, 
                                            'output_counts/%s_counts_%i.fits'
                                            %(out_label, mb))
            micro_exp_name = os.path.join(GRATOOLS_OUT,
                                          'output_counts/%s_exposure_%i.fits'
                                          %(out_label, mb))
            if os.path.exists(micro_count_name):
                exists_counts_files.append(micro_count_name)
                exists_exp_files.append(micro_exp_name)
        if len(exists_counts_files) == len(micro_bins):
            emin, emax, emean = [], [], []
            E_MIN, E_MAX, E_MEAN = 0, 0, 0
            txt_name = os.path.join(GRATOOLS_OUT, '%s_outfiles.txt' 
                                    %in_labels_list[0])
            txt = open(txt_name,'r')
            for line in txt:
                if 'gtbin' in line:
                    emin, emax, emean = get_energy_from_fits(line,
                                                             minbinnum=minb,
                                                             maxbinnum=maxb)
                    E_MIN, E_MAX = emin[0], emax[-1]
                    E_MEAN = np.sqrt(emax[0]*emin[-1])
            logger.info('Counts and exposure maps ready! Retriving them...')
            for j in range(0, len(micro_bins)):
                cc = hp.read_map(exists_counts_files[j])
                ee = hp.read_map(exists_exp_files[j])
                all_counts.append(cc)
                all_exps.append(ee)
        else:
            logger.info('Retriving count and exposure maps...')
            emin, emax, emean = [], [], []
            E_MIN, E_MAX, E_MEAN = 0, 0, 0
            count_map, exp_mean_map = [], []
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
                        emin, emax, emean = get_energy_from_fits(line,
                                                                 minbinnum=minb,
                                                                 maxbinnum=maxb)
                    
                        E_MIN, E_MAX = emin[0], emax[-1]
                        E_MEAN = np.sqrt(emax[0]*emin[-1])
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

            for i, cmap in enumerate(all_counts):
                micro_count_name = os.path.join(GRATOOLS_OUT, 
                                                'output_counts/%s_counts_%i.fits'
                                                %(out_label, micro_bins[i]))
                hp.write_map(micro_count_name, cmap)
                micro_exp_name = os.path.join(GRATOOLS_OUT, 
                                              'output_counts/%s_exposure_%i.fits'
                                              %(out_label, micro_bins[i]))
                hp.write_map(micro_exp_name, all_exps[i])

        logger.info('Computing the flux for each micro energy bin...')
        nside = kwargs['udgrade']
        npix = hp.nside2npix(nside)
        sr = 4*np.pi/npix
        iii = np.arange(npix)
        for i, cmap in enumerate(all_counts):
            flux_map.append(cmap/all_exps[i]/sr)
    
        # now I have finelly gridded (in energy) summed in time fluxes
        logger.info('Rebinning...')
        logger.info('Merging fluxes from %.2f to %.2f MeV' %(E_MIN, E_MAX))
        macro_fluxerr = (emean[0]/emean[0])**(-gamma)/(all_exps[0])**2
        macro_counts = all_counts[0]
        macro_flux = flux_map[0]

        # implement foreground subtraction
        if kwargs['foresub'] == True:
            from GRATools.utils.gFTools import get_foreground_integral_flux_map
            from GRATools.utils.gFTools import fit_foreground
            from GRATools.utils.gFTools import flux2counts
            out_fore_folder = os.path.join(GRATOOLS_OUT, 'output_fore')
            out_name_fore = os.path.join(out_fore_folder,'fore_%i-%i.fits'\
                                             %(E_MIN, E_MAX))
            out_name_forecount = os.path.join(out_fore_folder,
                                              out_label+'_forecount_%i-%i.fits'\
                                                  %(E_MIN, E_MAX))
            if not os.path.exists(out_fore_folder):
                os.makedirs(out_fore_folder)
            all_fore = []
            all_countfore = []
            for e1, e2 in zip(emin, emax):
                fore = get_foreground_integral_flux_map(fore_files, e1, e2)
                counts_fore = flux2counts(fore, all_exps[0])
                all_fore.append(fore)
                all_countfore.append(counts_fore)
            tot_counts = sum(all_counts)
            tot_flux = sum(flux_map)
            tot_fore = sum(all_fore)
            tot_countfore = sum(all_countfore)
            n0, c0 = fit_foreground(tot_fore, tot_flux)   
            #macro_flux = (all_counts[0] - n0*(all_countfore[0]))/all_exps[0]/sr
            
            macro_fore = all_fore[0]
            macro_countfore = all_countfore[0]
            CN = np.mean(all_counts[0][_unmask]/(all_exps[0][_unmask])**2)/sr
            for b in range(1, len(flux_map)):
                #n, c = fit_foreground(all_countfore[b], all_counts[b])
                #logger.info('Norm fact = %.3f'%n)
                fluxerr = (emean[b]/emean[0])**(-gamma)/(all_exps[b])**2
                macro_fluxerr = macro_fluxerr + fluxerr
                macro_flux = macro_flux+(all_counts[b] - n0*(all_countfore[b]))/\
                    all_exps[b]/sr
                macro_counts = macro_counts + all_counts[b]
                macro_fore = macro_fore + all_fore[b]
                macro_countfore = macro_countfore + all_countfore[b]
                CN = CN + np.mean(all_counts[b][_unmask]/ \
                                      (all_exps[b][_unmask])**2)/sr
            macro_flux = tot_flux - n0*tot_fore
            logger.info('CN (white noise) term = %e'%CN)
            macro_fluxerr = (np.sqrt(all_counts[0]*macro_fluxerr)/sr)
            macro_fore_masked = hp.ma(macro_fore)
            macro_fore_masked.mask = np.logical_not(mask)
            hp.write_map(out_name_fore, macro_fore, coord='G')
            hp.write_map(out_name_forecount, macro_countfore, coord='G')
            logger.info('Created %s' %out_name_fore)
            logger.info('Created %s' %out_name_forecount)
            FORE_MEAN = np.mean(macro_fore[_unmask])
            print 'MEAN FORE FLUX: ', FORE_MEAN
            fore_mean_list.append(FORE_MEAN)
        else:
            CN = np.mean(all_counts[0][_unmask]/(all_exps[0][_unmask])**2)/sr
            macro_flux = flux_map[0]
            for b in range(1, len(flux_map)):
                fluxerr = (emean[b]/emean[0])**(-gamma)/(all_exps[b])**2
                macro_fluxerr = macro_fluxerr + fluxerr
                macro_flux = macro_flux + flux_map[b]
                macro_counts = macro_counts + all_counts[b]
                CN = CN + np.mean(all_counts[b][_unmask]/ \
                                      (all_exps[b][_unmask])**2)/sr
            logger.info('CN (white noise) term = %e'%CN)
            macro_fluxerr = (np.sqrt(all_counts[0]*macro_fluxerr)/sr)
        
        out_count_folder = os.path.join(GRATOOLS_OUT, 'output_counts')
        if not os.path.exists(out_count_folder):
            os.makedirs(out_count_folder)
        out_counts_name = os.path.join(out_count_folder,out_label+'_counts_%i-%i.fits'\
                                      %(E_MIN, E_MAX))
        logger.info('Created %s' %out_counts_name)
        hp.write_map(out_counts_name, macro_counts, coord='G')
        # now mask the rebinned flux and error maps        
        macro_flux_masked = hp.ma(macro_flux)
        macro_fluxerr_masked = hp.ma(macro_fluxerr)
        macro_flux_masked.mask = np.logical_not(mask)
        macro_fluxerr_masked.mask = np.logical_not(mask)
        out_folder = os.path.join(GRATOOLS_OUT, 'output_flux')
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        out_name = os.path.join(out_folder,out_label+'_%s_flux_%i-%i.fits'\
                                      %(mask_label, E_MIN, E_MAX))
        out_name_err = os.path.join(out_folder, out_label+'_%s_fluxerr_%i-%i.fits'\
                                        %(mask_label, E_MIN, E_MAX))
        logger.info('Created %s' %out_name)
        logger.info('Created %s' %out_name_err)
        hp.write_map(out_name, macro_flux_masked, coord='G')
        hp.write_map(out_name_err, macro_fluxerr_masked, coord='G')
        F_MEAN = np.sum(macro_flux[_unmask])/len(macro_flux[_unmask])
        crbkg = get_crbkg(crbkg_file)
        logger.info('Subtracting CR residual bkg...')
        #F_MEAN = F_MEAN - (E_MAX-E_MIN)*crbkg(E_MEAN)/E_MEAN**2
        FERR_MEAN = np.sqrt(np.sum(macro_fluxerr[_unmask]**2))/\
                                   len(macro_flux[_unmask])
        FSKY = float(len(macro_flux[_unmask]))/float(len(macro_flux))
        logger.info('Fsky = %.3f'%FSKY)
        print 'F_MEAN, FERR_MEAN = ', F_MEAN, FERR_MEAN
        new_txt.write('%.2f \t %.2f \t %.2f \t %e \t %e \t %e \t %f \n' \
                          %(E_MIN, E_MAX, E_MEAN, F_MEAN, FERR_MEAN, CN, FSKY))
    if kwargs['foresub'] == True:
        new_txt.write('\n\n*** FOREGROUND PARAMETERS***\n\n')
        new_txt.write('MEAN FLUX \t %s\n' %str(fore_mean_list))
    new_txt.close()
    logger.info('Created %s' %os.path.join(GRATOOLS_OUT, 
                                     '%s_%s_%s_parameters.txt'\
                                      %(out_label, mask_label, binning_label)))   
    logger.info('done!')


if __name__ == '__main__':
    args = PARSER.parse_args()
    startmsg()
    mkRestyle(**args.__dict__)
