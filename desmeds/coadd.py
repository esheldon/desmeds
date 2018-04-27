from __future__ import print_function
import numpy as np
import os
import meds
from . import util
try:
    xrange
except:
    xrange=range

from .files import (
    TempFile,
    StagedOutFile,
)

class DESMEDSCoaddMaker(meds.MEDSCoaddMaker):
    def write(self, fname, obj_range=None):
        """
        write the data using the MEDSMaker
        """

        print("writing MEDS file:",fname)

        if self.tmpdir is not None:
            with StagedOutFile(fname,tmpdir=self.tmpdir) as sf:
                self._dowrite(sf.path, obj_range=obj_range)
        else:
            self._dowrite(fname, obj_range=obj_range)

    def _dowrite(self, path, obj_range=None):
        if path[-8:] == '.fits.fz':
            self._write_and_fpack(path, obj_range=obj_range)
        else:
            self._write(path, obj_range=obj_range)

    def _write_and_fpack(self, fname, obj_range=None):
        local_fitsname = fname.replace('.fits.fz','.fits')
        assert local_fitsname != fname

        with TempFile(local_fitsname) as tfile:
            self._write(tfile.path, obj_range=obj_range)

            # this will fpack to the proper path, which
            # will then be staged out if tmpdir is not None
            # if the name is wrong, the staging will fail and
            # an exception raised
            util.fpack_file(tfile.path)

    def _write(self, fname, obj_range=None):
        super(DESMEDSCoaddMaker,self).write(
            fname,
            obj_range=obj_range,
        )

    def _set_psf_layout(self):
        print("setting psf layout")

        # to fool the maker; need to make psf type
        # more natural
        self.psf_data=1

        max_box_size=0

        m=self.m

        self.total_psf_pixels=0
        for iobj in xrange(m.size):

            # get the max of the epochs
            ncutout=m['ncutout'][iobj]
            if ncutout > 1:
                tsizemax=0
                for icut in xrange(1,m['ncutout'][iobj]):
                    file_id=m['file_id'][iobj, icut]

                    pim, pcen = self.coadder._get_psf_im(
                        file_id,
                        500,
                        500,
                    )
                    tsizemax = max(tsizemax, pim.size)
                    max_box_size = max(max_box_size, pim.shape[0])

                self.total_psf_pixels += tsizemax

        print("max box size:",max_box_size)
        self.total_psf_pixels = int(1.1*self.total_psf_pixels)

class DESMEDSCoadder(meds.MEDSCoadder):
    """
    implement DES specific stuff for postage stamp coadding
    """

    '''
    def _set_target_jacobian(self):
        """
        use median coadd jacobian info
        """
        import ngmix
        # center doesn't matter

        w,= np.where(self.m['ncutout'] > 0)
        dudrow = np.median(self.m['dudrow'][w,0])
        dudcol = np.median(self.m['dudcol'][w,0])
        dvdrow = np.median(self.m['dvdrow'][w,0])
        dvdcol = np.median(self.m['dvdcol'][w,0])

        self.target_jacobian=ngmix.Jacobian(
            row=15, col=15,
            dudrow=dudrow,
            dudcol=dudcol,
            dvdrow=dvdrow,
            dvdcol=dvdcol,
        )
    '''

    def _set_target_jacobian(self):
        import ngmix
        # center doesn't matter

        self.target_jacobian=ngmix.Jacobian(
            row=15, col=15,
            dudrow=-0.263,
            dudcol=0.0,
            dvdrow=0.0,
            dvdcol=-0.263,
        )

    def _get_psf_im(self, file_id, row, col):
        ii=self.m.get_image_info()
        path=ii['image_path'][file_id]
        key = extract_nullwt_key(path)

        p = self.psfmap[key]
        pim = p.get_rec(row, col)

        pcen = p.get_center(row, col)

        return pim, pcen


    def _get_psf_obs(self, obs, file_id, meta, row, col):
        """
        psfex specific code here

        for psfex we need to add 0.5 to get an offset
        that is the same as used for the object
        """
        import ngmix
        assert self['psf']['type']=='psfex',"only psfex for now"

        pmeta={}

        if self['dither_psfs']:
            rowget=row+0.5
            colget=col+0.5
        else:
            #print("not dithering psfs")
            rowget=int(row)
            colget=int(col)
        pim, pcen = self._get_psf_im(file_id, rowget, colget)
        ccen=(np.array(pim.shape)-1.0)/2.0

        # for psfex we assume the jacobian is the same, not
        # quite right
        pjac = obs.jacobian.copy()
        pjac.set_cen(row=pcen[0], col=pcen[1])

        pmeta['offset_pixels']=dict(
            row_offset=pjac.row0-ccen[0],
            col_offset=pjac.col0-ccen[1],
        )
        #print("psf offsets:",pmeta['offset_pixels'])

        psf_weight=np.zeros(pim.shape) + 1.0/0.001**2

        psf_obs = ngmix.Observation(
            pim,
            weight=psf_weight,
            jacobian=pjac,
            meta=pmeta,
        )
        return psf_obs

def extract_nullwt_key(path):
    """
    expecting D00239652_i_c14_r2362p01_immasked_nullwt.fits
    """
    path=makestr(path)
    bname=os.path.basename(path).strip()
    bs=bname.split('_')
    expname=bs[0][1:]
    ccdstr=bs[2][1:]

    key='%s-%s' % (expname, ccdstr)
    return key

def makestr(data):
    try:
        s=str(data,'utf8')
    except:
        s=str(data)
    return s
