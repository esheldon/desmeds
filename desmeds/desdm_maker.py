from __future__ import print_function
import os
from os.path import basename
import numpy
from numpy import zeros, sqrt, log, vstack, array
import json
import yaml

import fitsio
import esutil as eu

import meds
from meds.util import \
    make_wcs_positions, \
    get_meds_input_struct, \
    get_image_info_struct

from . import blacklists
from . import util

from . import util
from . import files
from .defaults import default_config

from .files import \
        TempFile, \
        StagedInFile, \
        StagedOutFile

# desdb is not needed in all scenarios
try:
    import desdb
except ImportError:
    pass


fwhm_fac = 2*sqrt(2*log(2))

from .maker import DESMEDSMaker

class Preparator(dict):
    """
    class to prepare inputs for the DESDM version
    of the MEDS maker

    This is not used by DESDM, but is useful for testing
    outside of DESDM
    """
    def __init__(self, medsconf, tilename, band):
        self._load_medsconf(medsconf)
        self['tilename']=tilename
        self['band']=band

    def go(self):
        self.download()

    def download(self):
        from .coaddinfo import Coadd
        from .coaddsrc import CoaddSrc

        c=Coadd(campaign=self['campaign'])
        csrc=CoaddSrc(campaign=self['campaign'])

        c.download(self['tilename'])
        csrc.download(self['tilename'], self['band'])

    def _load_medsconf(self, medsconf):
        with open(medsconf) as fobj:
            conf=yaml.load( fobj )

        self.update(conf)

class DESMEDSMakerDESDM(DESMEDSMaker):
    """
    This is the class for use by DESDM.  For this version,
    all inputs are explicit rather than relying on database
    queries

    No "stubby" meds file is created, because DESDM does
    not allow pipelines

    parameters
    ----------
    medconf: string
        path to a meds config file.  see docs for DESMEDSMaker
    fileconf: string
        path to a yaml file configuration

        Required fields in the yaml file:
            band: band in string form
            coadd_image_url: string
            coadd_seg_url: string
            coadd_magzp: float
            nwgint_flist: string
                path to the nwgint file list
            seg_flist: string
                path to the seg file list
            bkg_flist: string
                path to the bkg file list
    """
    def __init__(self,
                 medsconf,
                 fileconf):

        self.medsconf=medsconf
        self.fileconf=fileconf

        self._load_config(medsconf)
        self._load_file_config(fileconf)

        self._set_extra_config('none', self.file_dict['band'])

        # not relevant for this version
        self.DESDATA = 'rootless'

    def go(self):
        """
        make the MEDS file
        """

        self._load_coadd_info()
        self._read_coadd_cat()
        self._build_image_data()
        self._build_meta_data()
        self._build_object_data()

        self._write_meds_file() # does second pass to write data

    def _get_image_id_len(self, srclist):
        """
        for y3 using string ids
        """
        image_id_len=len(self.cf['image_id'])

        slen = len(self._get_portable_url(self.cf,'image_url'))
        for s in srclist:
            tlen = len(s['id'])
            if tlen > image_id_len:
                image_id_len = tlen

        return image_id_len

    def _load_coadd_info(self):
        """
        Mock up the results of querying the database for Coadd
        info
        """
        print('getting coadd info and source list')

        fd=self.file_dict
        cf={}

        iid = self._get_filename_as_id(fd['coadd_image_url'])

        cf['image_url'] = fd['coadd_image_url']
        cf['seg_url']   = fd['coadd_seg_url']
        cf['image_id']  = iid

        # probably from from header MAGZERO
        cf['magzp']     = fd['coadd_magzp']

        cf['srclist'] = self._load_srclist()

        # In this case, we can use refband==input band, since
        # not using a db query or anything
        self.cf=cf
        self.cf_refband=cf

    def _read_coadd_cat(self):
        """
        read the DESDM coadd catalog, sorting by the number field (which
        should already be the case)
        """

        fname=self.file_dict['coadd_cat_url']

        print('reading coadd cat:',fname)
        self.coadd_cat = fitsio.read(fname, lower=True)

        # sort just in case, not needed ever AFIK
        q = numpy.argsort(self.coadd_cat['number'])
        self.coadd_cat = self.coadd_cat[q]

    def _get_srclist(self):
        """
        mock up the interface for the Coadd class
        """
        return self.cf['srclist']

    def _load_srclist(self):
        """
        get all the necessary information for each source image
        """
        # this is a list of dicts
        srclist=self._load_nwgint_info()
        nepoch = len(srclist)

        # now add in the other file types
        bkg_info=self._read_generic_flist('bkg_flist')
        seg_info=self._read_generic_flist('seg_flist')

        if len(bkg_info) != nepoch:
            raise ValueError("bkg list has %d elements, nwgint "
                             "list has %d elements" % (len(bkg_info),nepoch))
        if len(seg_info) != nepoch:
            raise ValueError("seg list has %d elements, nwgint "
                             "list has %d elements" % (len(seg_info),nepoch))

        for i,src in enumerate(srclist):
            src['red_bkg'] = bkg_info[i]
            src['red_seg'] = seg_info[i]

        return srclist

    def _read_generic_flist(self, key):
        """
        read a list of file paths, one per line
        """
        fname=self.file_dict[key]
        print("reading:",key)

        flist=[]
        with open(fname) as fobj:
            for line in fobj:
                line=line.strip()
                if line=='':
                    continue

                flist.append(line)
        return flist

    def _extract_nwgint_line(self, line):
        """
        the nwgint (red image) lines are 
            path magzp
        """
        line=line.strip()
        if line=='':
            return None,None

        ls=line.split()
        if len(ls) != 2:
            raise ValueError("got %d elements for line in "
                             "nwgint list: '%s'" % line)

        path=ls[0]
        magzp=float(ls[1])

        return path, magzp


    def _load_nwgint_info(self):
        """
        Load all meta information needed from the
        ngmwint files
        """
        fname=self.file_dict['nwgint_flist']
        print("reading nwgint list and loading headers:",fname)

        red_info=[]
        with open(fname) as fobj:
            for line in fobj:

                path, magzp = self._extract_nwgint_line(line)
                if path==None:
                    continue

                sid = self._get_filename_as_id(path)

                # now mock up the structure of the Coadd.srclist

                wcs_hdr = fitsio.read_header(path, ext=self['se_image_ext'])
                wcs_header = util.fitsio_header_to_dict(wcs_hdr)

                s={
                    'id':sid,
                    'flags':0,  # assume no problems!
                    'red_image':path,
                    'magzp':magzp,
                    'wcs_header':wcs_header,
                }

                red_info.append(s)

        return red_info

    def _get_coadd_objects_ids(self):
        """
        mock up the query to the database
        """

        dt=[
            ('object_number','i4'),
            ('coadd_objects_id','i8')
        ]

        nobj=self.coadd_cat.size

        iddata=numpy.zeros(nobj, dtype=dt)

        idmap = fitsio.read(
            self.file_dict['coadd_object_map'],
            lower=True,
        )

        s=numpy.argsort(idmap['object_number'])

        iddata['object_number']    = idmap['object_number'][s]
        iddata['coadd_objects_id'] = idmap['id'][s]

        return iddata

    def _get_portable_url(self, file_dict, name):
        """
        We don't have DESDATA defined when DESDM is running
        the code, so just return the path
        """

        return file_dict[name]

    def _load_config(self, medsconf):
        """
        load the default config, then load the input config
        """

        self.update(default_config)

        with open(medsconf) as fobj:
            conf=yaml.load( fobj )

        util.check_for_required_config(conf, ['medsconf'])
        self.update(conf)


    def _load_file_config(self, fileconf):
        """
        load the yaml file config
        """
        with open(fileconf) as fobj:
            self.file_dict=yaml.load( fobj )

    def _write_meds_file(self):
        """
        write the data using the MEDSMaker
        """

        maker=meds.MEDSMaker(
            self.obj_data,
            self.image_info,
            config=self,
            meta_data=self.meta_data,
        )

        fname=self.file_dict['meds_url']
        print("writing MEDS file:",fname)
        maker.write(fname)

