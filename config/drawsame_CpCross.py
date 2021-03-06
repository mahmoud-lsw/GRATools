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

import os
import numpy as np
from GRATools import GRATOOLS_OUT, GRATOOLS_CONFIG
from GRATools.utils.logging_ import logger, startmsg
from GRATools.utils.matplotlib_ import pyplot as plt
from GRATools.utils.matplotlib_ import overlay_tag, save_current_figure
from GRATools.utils.gWindowFunc import get_psf_ref
from GRATools.utils.gFTools import cl_parse

Cl_FILES = [os.path.join(GRATOOLS_OUT, 'Allyrs_UCV_t56_maskweighted-mE-mW_13bins_cross.txt'),
            #os.path.join(GRATOOLS_OUT, 'Allyrs_UCV_t56_maskweighted-mN-mS_13bins_cross.txt')
            ]

#OUT_LABEL = 'CpCross_t56_maskweight_north-south'
OUT_LABEL = 'CpCross_t56_maskweight_east-west'

rebinning = np.unique(np.int64(np.logspace(0, 3, 31)))
psf_ref_file = os.path.join(GRATOOLS_CONFIG, 'ascii/PSF_UCV_PSF1.txt')
psf_ref = get_psf_ref(psf_ref_file)
_l_min = [ 49, 49, 49, 49, 49, 49, 49, 49, 49, 49, 49, 49, 49]
_l_max = [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 
          1000, 1000, 1000, 1000]
cps_tocompare, cperrs_tocompare = [], []
emins, emaxs, emeans = [], [], []

for f in Cl_FILES:
    emin, emax, emean, cls, clerrs = cl_parse(f)
    emins.append(emin)
    emaxs.append(emax)
    emeans.append(emean)
    cps, cperrs = [], []
    for i, aps in enumerate(cls):
        psf_en = psf_ref(emean[i])
        l_max = _l_max[i]#min(600, 1.9*(np.pi/np.radians(psf_en)))
        l_min = _l_min[i]#min(60, max(60-i*5,10))
        logger.info('fitting Cl(%i:%i)'%(l_min, l_max))
        _l_rebin, _cls_rebin,  _clerrs_rebin = [], [], []
        for bmin, bmax in zip(rebinning[:-1], rebinning[1:]):
            _l_rebin.append(np.sqrt(bmin*bmax))
            clmean = np.average(aps[bmin:bmax])
            clmeanerr = np.sqrt(np.sum(clerrs[i][bmin:bmax]**2))/\
                np.sqrt(len(aps[bmin:bmax]))
            _cls_rebin.append(clmean)
            _clerrs_rebin.append(clmeanerr)
        _l_rebin = np.array(_l_rebin)
        _cls_rebin = np.array(_cls_rebin)
        _clerrs_rebin = np.array(_clerrs_rebin)
        l_range_fit = np.where(np.logical_and(_l_rebin>=l_min, _l_rebin<l_max))
        cp, cpV =  np.polyfit(_l_rebin[l_range_fit], _cls_rebin[l_range_fit], 
                              0, w=1/_clerrs_rebin[l_range_fit], full=False, cov=True)
        logger.info('Cp = %e' %cp)
        cps.append(cp[0])
        cperrs.append(np.sqrt(cpV[0][0]))
    cps_tocompare.append(np.array(cps))
    cperrs_tocompare.append(np.array(cperrs))

from GRATools.utils.gDrawRef import ref_cp_band
plt.figure(figsize=(10, 7), dpi=80)
lab = []
leg = []
leg_ref, lab_ref = ref_cp_band()
for i, f in enumerate(Cl_FILES):
    lab.append(os.path.basename(f).replace('_13bins_cross.txt', ''))
    leg.append(plt.errorbar(emeans[i]/1000, 
             cps_tocompare[i]*(emeans[i]/1000)**4/((emaxs[i]-emins[i])/1000)**2,
             fmt='o', markersize=3, elinewidth=1,
             xerr=[(emeans[i]-emins[i])/1000, (emaxs[i]-emeans[i])/1000],
             yerr=cperrs_tocompare[i]*(emeans[i]/1000)**4/((emaxs[i]-emins[i])/1000)**2))
plt.xlabel('E [GeV]')
plt.ylabel('E$^{4}$/$\Delta$E$^{2}$ $\cdot$ C$_{P}$')
plt.xscale('log')
#plt.yscale('log', nonposy='clip')
plt.legend([leg_ref]+leg, [lab_ref]+lab, loc=2)
save_current_figure(OUT_LABEL+'.png')

plt.figure(figsize=(10, 7), dpi=80)
lab = []
leg = []
for i, f in enumerate(Cl_FILES):
    lab.append(os.path.basename(f).replace('_13bins_cross.txt', ''))
    leg.append(plt.errorbar(emeans[i]/1000, 
             abs(0-cps_tocompare[i]),
             fmt='o', markersize=3, elinewidth=1,
             xerr=[(emeans[i]-emins[i])/1000, (emaxs[i]-emeans[i])/1000],
             yerr=cperrs_tocompare[i]))
plt.xlabel('E [GeV]')
plt.ylabel('|$0$-C$_{P}$|')
plt.xscale('log')
plt.yscale('log', nonposy='clip')
plt.legend(leg, lab, loc=2)
save_current_figure(OUT_LABEL+'_residuals.png')
    

