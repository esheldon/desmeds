from __future__ import print_function
import numpy as np
import os
import meds


class DESMEDSCoadder(meds.MEDSCoadder):
    """
    implement DES specific stuff for postage stamp coadding
    """
    def _get_psf_obs(self, obs, file_id, meta, row, col):
        """
        psfex specific code here

        for psfex we need to add 0.5 to get an offset
        that is the same as used for the object
        """
        import ngmix
        assert self['psf']['type']=='psfex',"only psfex for now"

        pmeta={}

        ii=self.m.get_image_info()
        path=ii['image_path'][file_id]
        key = extract_nullwt_key(path)

        rowget=row+0.5
        colget=col+0.5
        p = self.psfmap[key]
        pim = p.get_rec(rowget, colget)
        pcen = p.get_center(rowget, colget)
        ccen=(np.array(pim.shape)-1.0)/2.0

        # for psfex we assume the jacobian is the same, not
        # quite right
        pjac = obs.jacobian.copy()
        pjac.set_cen(row=pcen[0], col=pcen[1])

        pmeta['offset_pixels']=dict(
            row_offset=pjac.row0-ccen[0],
            col_offset=pjac.col0-ccen[1],
        )

        """
        print("psf dims:",pim.shape)
        print("ccen:",ccen)
        print("pcen:",pcen)
        print("image offset pixels:",meta['offset_pixels'])
        print("psf   offset pixels:",pmeta['offset_pixels'])
        """

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
