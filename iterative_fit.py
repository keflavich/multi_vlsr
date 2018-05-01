__author__ = 'mcychen'


#=======================================================================================================================
import numpy as np
import astropy.io.fits as fits
import FITS_tools
from astropy import units as u
from astropy.stats import mad_std
from skimage.morphology import remove_small_objects,disk,opening # ,binary_erosion, closing
from spectral_cube import SpectralCube
from radio_beam import Beam


import multi_v_fit as mvf



#=======================================================================================================================

def test():
    workDir = "/Users/mcychen/Documents/Data/GAS_NH3/DRMC_rebase3/L1448"
    cubename = "{0}/L1448_NH3_11_all_rebase_multi.fits".format(workDir)
    #GAS beam is 30.79''
    savename = "{0}/L1448_NH3_11_all_rebase_multi_conv62as.fits".format(workDir)
    return convolve_sky_byfactor(cubename, 2, savename)


def convolve_sky_byfactor(cube, factor, savename):

    factor = factor*1.0

    if not isinstance(cube, SpectralCube):
        cube = SpectralCube.read(cube)

    hdr = cube.header

    #sanity check
    if hdr['CUNIT1'] != hdr['CUNIT2']:
        print "[ERROR]: the axis units for the do not match each other!"
        return None

    beamunit = getattr(u, hdr['CUNIT1'])
    bmaj = hdr['BMAJ']*beamunit*factor
    bmin = hdr['BMIN']*beamunit*factor
    pa = hdr['BPA']

    beam = Beam(major=bmaj, minor=bmin, pa=pa)

    # convolve
    cnv_cube = convolve_sky(cube, beam, snrmasked = True)
    if cnv_cube.fill_value is not np.nan:
        cnv_cube = cnv_cube.with_fill_value(np.nan)

    # regrid the convolved cube
    nhdr = FITS_tools.downsample.downsample_header(hdr, factor=factor, axis=1)
    nhdr = FITS_tools.downsample.downsample_header(nhdr, factor=factor, axis=2)

    #ncube_data = FITS_tools.cube_regrid.regrid_cube(cnv_cube._data, hdr, nhdr, preserve_bad_pixels=True)
    newcube = cnv_cube.reproject(nhdr, order='bilinear')

    if savename is not None:
        #newcube = SpectralCube(ncube_data, header=nhdr)
        newcube.write(savename, overwrite=True)

    return newcube


#def convolve_sky(cube, beamsize, savename=None, beamunit=u.arcsec, snrmasked = True):
def convolve_sky(cube, beam, snrmasked = True):

    if not isinstance(cube, SpectralCube):
        cube = SpectralCube.read(cube)

    if cube.fill_value is not np.nan:
        cube = cube.with_fill_value(np.nan)

    if snrmasked:
        planemask = snr_mask(cube, snr_min=3.0)
        mask = np.isfinite(cube._data)*planemask
        maskcube = cube.with_mask(mask.astype(bool))

    cnv_cube=maskcube.convolve_to(beam)

    return cnv_cube



def cubefit(cubename):
    pcube = mvf.cubefit_gen(cubename, ncomp=2, paraname = None, modname = None, chisqname = None, guesses = None, errmap11name = None,
            multicore = 1, mask_function = None, snr_min=3.0, linename="oneone")


def snr_mask(cube, snr_min=3.0, errmappath=None):

    if errmappath is not None:
        errmap = fits.getdata(errmappath)

    else:
        # make a quick RMS estimate using median absolute deviation (MAD)
        errmap = mad_std(cube._data, axis=0)
        print "median rms: {0}".format(np.nanmedian(errmap))

    snr = cube.filled_data[:].value/errmap
    peaksnr = np.max(snr,axis=0)

    def default_masking(snr, snr_min=5.0):
        planemask = (snr>snr_min)
        if planemask.size > 100:
            planemask = remove_small_objects(planemask,min_size=40)
            planemask = opening(planemask,disk(1))
        return(planemask)

    planemask = default_masking(peaksnr,snr_min=snr_min)

    return planemask


