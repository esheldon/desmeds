from __future__ import print_function
import numpy as np
import os
from os.path import basename, expandvars
import numpy
from numpy import zeros, sqrt, log
import subprocess
import shutil
import yaml

import fitsio

import meds

from . import util

from . import files
from .defaults import default_config

from .files import \
        TempFile, \
        StagedOutFile

from .maker import DESMEDSMaker

fwhm_fac = 2*sqrt(2*log(2))


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
            meds_url: string
                path to the output meds file
    """
    def __init__(self,
                 medsconf,
                 fileconf,
                 tmpdir=None):

        self.medsconf = medsconf
        self.fileconf = fileconf
        self.tmpdir = tmpdir

        self._load_config(medsconf)
        self._load_file_config(fileconf)

        self._set_extra_config('none', self.file_dict['band'])

        # not relevant for this version
        self.DESDATA = 'rootless'

        self._load_coadd_info()
        self._read_coadd_cat()
        self._build_image_data()
        self._build_meta_data()
        self._build_object_data()

    def go(self, fname=None):
        """
        write the data using the MEDSMaker
        """

        maker = meds.MEDSMaker(
            self.obj_data,
            self.image_info,
            config=self,
            meta_data=self.meta_data,
            psf_data=self.psf_data,
            psf_info=self.psf_info,
        )

        if fname is None:
            fname = self.file_dict['meds_url']

        print("writing MEDS file:", fname)

        # this will do nothing if tmpdir is None; sf.path will
        # in fact equal fname and no move is performed

        if self.tmpdir is not None:
            with StagedOutFile(fname, tmpdir=self.tmpdir) as sf:
                if sf.path[-8:] == '.fits.fz':
                    self._write_and_fpack(maker, sf.path)
                else:
                    maker.write(sf.path)
        else:
            if fname[-8:] == '.fits.fz':
                self._write_and_fpack(maker, fname)
            else:
                maker.write(fname)

    def _get_image_id_len(self, srclist):
        """
        for y3 using string ids
        """
        image_id_len = len(self.cf['image_id'])

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

        fd = self.file_dict
        cf = {}

        iid = self._get_filename_as_id(fd['coadd_image_url'])

        cf['image_url'] = fd['coadd_image_url']
        cf['seg_url'] = fd['coadd_seg_url']
        cf['image_id'] = iid

        if 'coadd_psf_url' in fd:
            cf['psf_url'] = fd['coadd_psf_url']

        # probably from from header MAGZERO
        cf['magzp'] = fd['coadd_magzp']

        cf['srclist'] = self._load_srclist()
        for i in range(len(cf['srclist'])):
            ccdnum = (
                os.path.basename(cf['srclist'][i]['red_image'])
                .split("_")[2][1:]
            )
            band = (
                os.path.basename(cf['srclist'][i]['red_image'])
                .split("_")[1]
            )
            cf['srclist'][i]['ccdnum'] = int(ccdnum)
            cf['srclist'][i]['band'] = band

        if 'psf_flist' in fd or 'piff_flist' in fd:
            self.psf_data = self._load_psf_data(cf)
        else:
            self.psf_data = None

        # In this case, we can use refband==input band, since
        # not using a db query or anything
        self.cf = cf
        self.cf_refband = cf

    """
    def _get_wcs(self, file_id):
        try:
            print('trying piff wcs')
            # this works for the PIFFWrapper psfs
            pobj = self.psf_data[file_id]
            wcs = pobj.get_wcs()
            print('got piff wcs')
        except AttributeError:
            wcs = super()._get_wcs(file_id)

        return wcs
    """

    def _read_coadd_cat(self):
        """
        read the DESDM coadd catalog, sorting by the number field (which
        should already be the case)
        """

        fname = self.file_dict['coadd_cat_url']
        fname = expandvars(fname)

        print('reading coadd cat:', fname)
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
        srclist = self._load_source_image_info()
        nepoch = len(srclist)

        fd = self.file_dict

        if nepoch > 0:

            # now add in the other file types
            bkg_info = self._read_generic_flist('bkg_flist')
            seg_info = self._read_generic_flist('seg_flist')

            if len(bkg_info) != nepoch:
                raise ValueError(
                    "bkg list has %d elements, source image "
                    "list has %d elements" % (len(bkg_info), nepoch)
                )
            if len(seg_info) != nepoch:
                raise ValueError(
                    "seg list has %d elements, source image "
                    "list has %d elements" % (len(seg_info), nepoch)
                )

            if 'psf_flist' in fd:
                assert 'coadd_psf_url' in fd, \
                        'coadd_psf_url must be set of SE psfs are set'

                psf_flist = self._read_generic_flist('psf_flist')

                if len(psf_flist) != nepoch:
                    raise ValueError(
                        "psf list has %d elements, source image "
                        "list has %d elements" % (len(psf_flist), nepoch)
                    )

            if 'piff_flist' in fd:
                assert 'coadd_psf_url' in fd, \
                        'coadd_psf_url must be set of SE psfs are set'

                piff_flist = self._read_generic_flist('piff_flist')

                if len(piff_flist) != nepoch:
                    raise ValueError(
                        "piff list has %d elements, source image "
                        "list has %d elements" % (len(piff_flist), nepoch)
                    )

            for i, src in enumerate(srclist):
                src['red_bkg'] = bkg_info[i]
                src['red_seg'] = seg_info[i]

                if 'psf_flist' in fd:
                    src['red_psf'] = psf_flist[i]
                if 'piff_flist' in fd:
                    src['red_psf_piff'] = piff_flist[i]

            self._verify_src_info(srclist)

        return srclist

    def _load_psf_data(self, cf):
        """
        load all psfs into a list
        """

        print('loading psf data')

        assert 'coadd_psf_url' in self.file_dict, \
            'you must set both coadd_psf_url and psf_flist or piff_flist'

        assert 'psf' in self, 'you must have a psf entry when loading psfs'

        if 'psf_info' in self.file_dict:
            print('loading psf info from:', self.file_dict['psf_info'])
            self.psf_info = fitsio.read(
                self.file_dict['psf_info'], lower=True
            )
            assert 'filename' in self.psf_info.dtype.names
        else:
            self.psf_info = None

        psf_data = []

        psf = self._load_one_psf(cf['psf_url'], self['psf']['coadd'])
        psf_data.append(psf)

        if self['psf']['se']['type'] == "piff":
            flist = [src['red_psf_piff'] for src in cf['srclist']]
        else:
            flist = [src['red_psf'] for src in cf['srclist']]
        ccdnums = [src['ccdnum'] for src in cf['srclist']]
        bands = [src['band'] for src in cf['srclist']]

        for f, ccdnum, band in zip(flist, ccdnums, bands):
            if self.psf_info is not None:
                assert os.path.basename(f) in self.psf_info['filename']

            if self['psf']['se'].get("use_color", False):
                psf = self._load_one_psf(
                    f, self['psf']['se'], ccdnum=ccdnum, band=band
                )
            else:
                psf = self._load_one_psf(f, self['psf']['se'])

            psf_data.append(psf)

        return psf_data

    def _load_one_psf(self, f, conf, ccdnum=None, band=None):
        """
        load a psf of the given type
        """
        if conf['type'] == 'psfex':
            return self._load_one_psfex(f)
        elif conf['type'] == 'piff':
            return self._load_one_piff(f, conf, ccdnum=ccdnum, band=band)
        else:
            raise ValueError('only psfex or piff supported')

    def _load_one_psfex(self, f):
        """
        load a single psfex psf
        """
        import psfex
        print('loading psfex data:', f)
        return psfex.PSFEx(f)

    def _load_one_piff(self, f, conf, ccdnum=None, band=None):
        """
        load a single psf
        """
        print('loading piff data:', f)
        if band is not None:
            if band in ["g", "r", "i"]:
                color_name = "GI_COLOR"
            else:
                color_name = "IZ_COLOR"
        else:
            color_name = None
        print(
            '    setting piff ccdnum|color_name|band:',
            ccdnum,
            color_name,
            band,
        )

        return PIFFWrapper(
            f,
            stamp_size=conf['stamp_size'],
            ccdnum=ccdnum,
            color_name=color_name,
        )

    def _verify_src_info(self, srclist):
        """
        make sure the lists match by exp, band, ccd

        D00502664_r_c36_r2378p01_immasked.fits.fz
        D00502664_r_c36_r2378p01_bkg.fits.fz
        D00502664_r_c36_r2378p01_segmap.fits.fz
        """
        for src in srclist:
            rs = basename(src['red_image']).split('_')
            bs = basename(src['red_bkg']).split('_')
            ss = basename(src['red_seg']).split('_')

            assert rs[0] == bs[0], "exp ids don't match"
            assert rs[0] == ss[0], "exp ids don't match"

            assert rs[1] == bs[1], "bands don't match"
            assert rs[1] == ss[1], "bands don't match"

            assert rs[2] == bs[2], "ccds don't match"
            assert rs[2] == ss[2], "ccds don't match"

            if 'psf_flist' in self.file_dict:
                ps = basename(src['red_psf']).split('_')
                assert rs[0] == ps[0], "psf exp ids don't match"
                assert rs[1] == ps[1], "psf bands don't match"
                assert rs[2] == ps[2], "psf ccds don't match"

    def _read_generic_flist(self, key):
        """
        read a list of file paths, one per line
        """
        fname = expandvars(self.file_dict[key])
        print("reading:", key, 'from:', fname)

        flist = []
        with open(fname) as fobj:
            for line in fobj:
                line = line.strip()
                if line == '':
                    continue

                flist.append(line)
        return flist

    def _extract_source_image_line(self, line):
        """
        the source image lines are
            path magzp
        """
        line = line.strip()
        if line == '':
            return None, None

        ls = line.split()
        if len(ls) != 2:
            raise ValueError("got %d elements for line in "
                             "source image list: '%s'" % line)

        path = ls[0]
        magzp = float(ls[1])

        return path, magzp

    def _load_source_image_info(self):

        # for coadd-only this should be set to False
        have_se_images = self.file_dict.get('have_se_images', True)
        if not have_se_images:
            res = []

        elif 'finalcut_flist' in self.file_dict:
            assert self['source_type'] == 'finalcut', \
                'source type should be finalcut'

            res = self._load_src_info_fromfile(
                self.file_dict['finalcut_flist'],
            )

        else:
            res = self._load_source_image_info_fromdb()

        return res

    def _load_src_info_fromfile(self, finalcut_flist):
        finalcut_flist = expandvars(finalcut_flist)

        print('reading finalcut info from:', finalcut_flist)
        # print('using ohead files for the wcs')
        src_info = []

        with open(finalcut_flist) as fobj:
            for line in fobj:
                ls = line.split()

                red_path = expandvars(ls[0])
                ohead_path = expandvars(ls[1])
                magzp = float(ls[2])

                if self['use_astro_refine']:
                    img_hdr = fitsio.read_header(
                        red_path,
                        ext=self['se_image_ext'],
                    )
                    wcs_hdr = fitsio.read_scamp_head(ohead_path)
                    wcs_hdr = util.add_naxis_to_fitsio_header(wcs_hdr, img_hdr)
                else:
                    wcs_hdr = None

                sid = self._get_filename_as_id(red_path)
                entry = {
                    'id': sid,
                    'flags': 0,
                    'red_image': red_path,
                    'magzp': magzp,
                    'wcs_header': wcs_hdr,
                }

                src_info.append(entry)

        return src_info

    def _load_source_image_info_fromdb(self):
        """
        Load all meta information needed from the
        ngmwint files
        """

        # read the full coadd info that we dumped to file
        fname = files.get_coaddinfo_file(
            self['medsconf'],
            self.file_dict['tilename'],
            self.file_dict['band'],
        )
        fname = expandvars(fname)

        print("reading full coaddinfo:", fname)
        with open(fname) as fobj:
            ci = yaml.safe_load(fobj)

        if self['source_type'] == 'nullwt':
            # refined astrometry already present
            entry = 'nullwt_path'
            self['use_astro_refine'] = False
        else:
            entry = 'image_path'

        red_info = []

        for s in ci['src_info']:

            path = expandvars(s[entry])

            sid = self._get_filename_as_id(path)

            # now mock up the structure of the Coadd.srclist

            if self['use_astro_refine']:
                img_hdr = fitsio.read_header(path, ext=self['se_image_ext'])
                head_path = expandvars(s['head_path'])
                wcs_hdr = fitsio.read_scamp_head(head_path)
                wcs_hdr = util.add_naxis_to_fitsio_header(wcs_hdr, img_hdr)
            else:
                wcs_hdr = fitsio.read_header(path, ext=self['se_image_ext'])

            wcs_hdr = util.fitsio_header_to_dict(wcs_hdr)
            s = {
                'id': sid,
                'flags': 0,  # assume no problems!
                'red_image': path,
                'magzp': s['magzp'],
                'wcs_header': wcs_hdr,
            }

            red_info.append(s)

        return red_info

    def _get_coadd_objects_ids(self):
        """
        mock up the query to the database
        """

        dt = [
            ('object_number', 'i4'),
            ('coadd_objects_id', 'i8'),
            ('wcs_color', 'f4'),
            ('psf_color', 'f4'),
        ]

        nobj = self.coadd_cat.size

        iddata = zeros(nobj, dtype=dt)

        fname = expandvars(self.file_dict['coadd_object_map'])
        print('reading id map:', fname)
        idmap = fitsio.read(fname, lower=True)

        s = numpy.argsort(idmap['object_number'])

        iddata['object_number'] = idmap['object_number'][s]
        iddata['coadd_objects_id'] = idmap['id'][s]

        # pixmappy always uses g-i
        gmi = idmap['gi_color'][s].copy()
        gi_color_range = self["psf"]["se"].get(
            "gi_color_range",
            [-np.inf, np.inf],
        )
        gmi = numpy.clip(gmi, gi_color_range[0], gi_color_range[1])
        iddata['wcs_color'] = gmi

        # piff in gri uses g-i, uses i-z in zY
        if self.file_dict["band"].lower() in ["g", "r", "i"]:
            iddata["psf_color"] = iddata["wcs_color"]
        else:
            imz = idmap['iz_color'][s].copy()
            iz_color_range = self["psf"]["se"].get(
                "iz_color_range",
                [-np.inf, np.inf],
            )
            imz = numpy.clip(imz, iz_color_range[0], iz_color_range[1])
            iddata['psf_color'] = imz

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

        note desdm names things randomly so we can't assert
        any consistency between the internal config name
        and the file name
        """

        self.update(default_config)

        if isinstance(medsconf, dict):
            conf = medsconf
        else:
            with open(medsconf) as fobj:
                conf = yaml.safe_load(fobj)

        util.check_for_required_config(conf, ['medsconf', 'source_type'])
        self.update(conf)

        assert self['source_type'] in ['finalcut', 'nullwt']

        assert 'psf' in self

    def _load_file_config(self, fileconf):
        """
        load the yaml file config
        """
        if isinstance(fileconf, dict):
            fd = fileconf
        else:
            fd = files.read_yaml(fileconf)

        self.file_dict = fd

    def _write_and_fpack(self, maker, fname):
        local_fitsname = fname.replace('.fits.fz', '.fits')

        with TempFile(local_fitsname) as tfile:
            maker.write(tfile.path)

            # this will fpack to the proper path, which
            # will then be staged out if tmpdir is not None
            # if the name is wrong, the staging will fail and
            # an exception raised
            util.fpack_file(tfile.path)


class Preparator(dict):
    """
    class to prepare inputs for the DESDM version
    of the MEDS maker

    This is not used by DESDM, but is useful for testing
    outside of DESDM

    TODO:
        - write psf map file
        - write file config
    """
    def __init__(self, medsconf, tilename, band, no_temp=False):
        from .coaddinfo import Coadd
        from .coaddsrc import CoaddSrc

        if isinstance(medsconf, dict):
            conf = medsconf
        else:
            conf = files.read_meds_config(medsconf)
        self.update(conf)

        self['tilename'] = tilename
        self['band'] = band

        if self.get("piff_campaign", None) is not None:
            kwargs = {"piff_campaign": self.get("piff_campaign", None)}
        else:
            kwargs = {}

        csrc = CoaddSrc(
            self['medsconf'],
            self['tilename'],
            self['band'],
            campaign=self['campaign'],
            no_temp=no_temp,
            **kwargs,
        )

        self.coadd = Coadd(
            self['medsconf'],
            self['tilename'],
            self['band'],
            campaign=self['campaign'],
            sources=csrc,
            no_temp=no_temp,
            **kwargs,
        )
        self['nullwt_dir'] = files.get_nullwt_dir(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        self['psfmap_file'] = files.get_psfmap_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        self['psf_dir'] = files.get_psf_dir(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        self['lists_dir'] = files.get_lists_dir(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

    def go(self):
        """
        download the data and make the null weight images
        """
        print("downloading all data")
        info = self.coadd.download()

        self._make_objmap(info)
        self._copy_psfs(info)

        if self['source_type'] == 'nullwt':
            self._make_nullwt(info)

        fileconf = self._write_file_config(info)

        self._write_finalcut_flist(info['src_info'], fileconf)

        if self['source_type'] == 'nullwt':
            self._write_nullwt_flist(info['src_info'], fileconf)

        self._write_seg_flist(info['src_info'], fileconf)
        self._write_bkg_flist(info['src_info'], fileconf)
        self._write_psf_flist(info['src_info'], fileconf)
        self._write_piff_flist(info['src_info'], fileconf)

        self._write_coaddinfo(info)

    def clean(self):
        """
        remove all sources and nullwt files
        """
        self.clean_sources()
        if self['source_type'] == 'nullwt':
            self.clean_nullwt()

    def clean_sources(self):
        """
        remove the downloaded source files
        """
        self.coadd.clean()

    def clean_nullwt(self):
        """
        remove all the generated nullwt files
        """
        print("removing nullwt images:", self['nullwt_dir'])
        shutil.rmtree(self['nullwt_dir'])

    def _make_objmap(self, info):
        fname = files.get_desdm_objmap(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        fname = expandvars(fname)
        dir = os.path.dirname(fname)
        if not os.path.exists(dir):
            print("making directory:", dir)
            os.makedirs(dir)

        objmap = self.coadd.get_objmap(info)
        print("writing objmap:", fname)
        fitsio.write(fname, objmap, extname='OBJECTS', clobber=True)

    def _write_finalcut_flist(self, src_info, fileconf):
        fname = expandvars(fileconf['finalcut_flist'])
        print("writing:", fname)
        with open(fname, 'w') as fobj:
            for sinfo in src_info:
                stup = (
                    sinfo['image_path'],
                    sinfo['head_path'],
                    sinfo['magzp'],
                )
                fobj.write("%s %s %.16g\n" % stup)

    def _write_nullwt_flist(self, src_info, fileconf):
        fname = expandvars(fileconf['nwgint_flist'])
        print("writing:", fname)
        with open(fname, 'w') as fobj:
            for sinfo in src_info:
                stup = sinfo['nullwt_path'], sinfo['magzp']
                fobj.write("%s %.16g\n" % stup)

    def _write_seg_flist(self, src_info, fileconf):
        fname = expandvars(fileconf['seg_flist'])
        print("writing:", fname)
        with open(fname, 'w') as fobj:
            for sinfo in src_info:
                fobj.write("%s\n" % sinfo['seg_path'])

    def _write_bkg_flist(self, src_info, fileconf):
        fname = expandvars(fileconf['bkg_flist'])
        print("writing:", fname)
        with open(fname, 'w') as fobj:
            for sinfo in src_info:
                fobj.write("%s\n" % sinfo['bkg_path'])

    def _write_psf_flist(self, src_info, fileconf):
        fname = expandvars(fileconf['psf_flist'])
        print("writing:", fname)
        with open(fname, 'w') as fobj:
            for sinfo in src_info:
                fobj.write("%s\n" % sinfo['psf_path'])

    def _write_piff_flist(self, src_info, fileconf):
        fname = expandvars(fileconf['piff_flist'])
        print("writing:", fname)
        with open(fname, 'w') as fobj:
            for sinfo in src_info:
                fobj.write("%s\n" % sinfo['piff_path'])

    def _write_coaddinfo(self, info):
        fname = files.get_coaddinfo_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        fname = expandvars(fname)

        print("writing full coaddinfo:", fname)
        with open(fname, 'w') as fobj:
            yaml.dump(info, fobj)

    def _write_file_config(self, info):
        fname = files.get_desdm_file_config(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        fname = expandvars(fname)

        finalcut_flist = files.get_desdm_finalcut_flist(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        seg_flist = files.get_desdm_seg_flist(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        bkg_flist = files.get_desdm_bkg_flist(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        psf_flist = files.get_desdm_psf_flist(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        piff_flist = files.get_desdm_piff_flist(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )
        objmap = files.get_desdm_objmap(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        coaddinfo = files.get_coaddinfo_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        do_fpack = self.get('fpack', True)
        if do_fpack:
            ext = 'fits.fz'
        else:
            ext = 'fits'

        meds_file = files.get_meds_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
            ext=ext,
        )
        output = {
            'band': self['band'],
            'tilename': self['tilename'],
            'coadd_image_url': info['image_path'],
            'coadd_cat_url': info['cat_path'],
            'coadd_seg_url': info['seg_path'],
            'coadd_psf_url': info['psf_path'],
            'coadd_magzp': info['magzp'],
            'coadd_object_map': objmap,

            'coaddinfo': coaddinfo,
            'finalcut_flist': finalcut_flist,
            'seg_flist': seg_flist,
            'bkg_flist': bkg_flist,
            'psf_flist': psf_flist,
            'piff_flist': piff_flist,

            'meds_url': meds_file,
        }
        if self['source_type'] == 'nullwt':
            output['nwgint_flist'] = files.get_desdm_nullwt_flist(
                    self['medsconf'],
                    self['tilename'],
                    self['band'],
                )

        print("writing file config:", fname)
        with open(fname, 'w') as fobj:
            for key in output:
                value = output[key]
                if key == "coadd_magzp":
                    value = '%.16g' % value

                fobj.write("%s: %s\n" % (key, value))

        return output

    def _make_nullwt(self, info):

        src_info = info['src_info']
        self._add_nullwt_paths(src_info)

        dir = self['nullwt_dir']
        if not os.path.exists(dir):
            print("making directory:", dir)
            os.makedirs(dir)

        print("making nullweight images")
        for sinfo in src_info:
            if os.path.exists(sinfo['nullwt_path']):
                continue

            cmd = _NULLWT_TEMPLATE % sinfo

            subprocess.check_call(cmd, shell=True)

    def _add_nullwt_paths(self, src_info):
        for sinfo in src_info:

            sinfo['nullwt_config'] = files.get_nwgint_config(self['campaign'])

            sinfo['nullwt_path'] = files.get_nullwt_file(
                self['medsconf'],
                self['tilename'],
                self['band'],
                sinfo['image_path'],
            )

    def _copy_psfs(self, info):

        psf_dir = expandvars(self['psf_dir'])

        if not os.path.exists(psf_dir):
            print("making directory:", psf_dir)
            os.makedirs(psf_dir)

        psfmap_file = expandvars(self['psfmap_file'])

        print("writing psfmap:", psfmap_file)
        with open(psfmap_file, 'w') as psfmap_fobj:
            print("copying psf files")

            psfs = self._get_psf_list(info)
            for psf_file in psfs:

                psf_file = expandvars(psf_file)

                bname = basename(psf_file)
                ofile = os.path.join(psf_dir, bname)

                fs = bname.split('_')
                if 'DES' in fs[0]:
                    # this is the coadd psf, so fake it
                    expnum = -9999
                    ccdnum = -9999

                else:
                    # single epoch psf
                    expnum = fs[0][1:]
                    ccdnum = fs[2][1:]

                ttup = expnum, ccdnum, ofile
                psfmap_fobj.write("%s %s %s\n" % ttup)

                if os.path.exists(ofile):
                    continue

                print("copying: %s -> %s" % (psf_file, ofile))
                shutil.copy(psf_file, ofile)

    def _get_psf_list(self, info):
        psfs = []
        psfs.append(info['psf_path'])

        for sinfo in info['src_info']:
            psfs.append(sinfo['psf_path'])

        return psfs


_NULLWT_TEMPLATE = r"""
coadd_nwgint                  \
   -i "%(image_path)s"        \
   -o "%(nullwt_path)s"       \
   --headfile "%(head_path)s" \
   --max_cols 50              \
   -v                         \
   --interp_mask TRAIL,BPM    \
   --invalid_mask EDGE        \
   --null_mask BPM,BADAMP,EDGEBLEED,EDGE,CRAY,SSXTALK,STREAK,TRAIL \
   --me_wgt_keepmask STAR     \
   --block_size 5             \
   --tilename %(tilename)s    \
   --hdupcfg "%(nullwt_config)s"
"""


class PIFFWrapper(dict):
    """
    provide an interface consistent with the PSFEx class
    """
    def __init__(self, psf_path, color_name=None, ccdnum=None, stamp_size=25):

        import piff

        self.piff_obj = piff.read(psf_path)

        self['filename'] = psf_path
        self['stamp_size'] = stamp_size
        self['rec_shape'] = (stamp_size, stamp_size)
        self.color_name = color_name
        self.ccdnum = ccdnum

    def get_rec_shape(self, *args, **kwargs):
        return self['rec_shape']

    def get_rec(self, row, col, color=None):
        """
        get the psf reconstruction as a numpy array

        image is normalized
        """

        if self.color_name is not None:
            kwargs = {
                self.color_name: color
            }
        else:
            kwargs = {}

        if self.ccdnum is not None:
            kwargs["chipnum"] = self.ccdnum

        # draw it where the object is - drawing at center causes a bias
        # this means center=None
        gsim = self.piff_obj.draw(
            x=col,
            y=row,
            center=None,
            stamp_size=self['stamp_size'],
            **kwargs,
        )
        im = gsim.array

        im *= (1.0/im.sum())

        return im

    def get_center(self, row, col):
        """
        get the center location
        """
        sa = np.array(self.get_rec_shape(row, col))

        # this snippet is from the piff internals
        # it returns the central pixel of the image
        # https://github.com/rmjarvis/Piff/blob/releases/1.2/piff/psf.py#L177
        col_cen = int(np.ceil(col - (0.5 if sa[1] % 2 == 1 else 0)))
        row_cen = int(np.ceil(row - (0.5 if sa[0] % 2 == 1 else 0)))

        # these are the offset of the PSF position from the central pixel
        dcol = col - col_cen
        drow = row - row_cen

        # now we add those offsets to the offset from the central pixel
        # galsim rounds up for even images
        row_cutout = ((sa[0] - 1)/2 if sa[0] % 2 == 1 else sa[0]/2) + drow
        col_cutout = ((sa[1] - 1)/2 if sa[1] % 2 == 1 else sa[1]/2) + dcol

        return np.array([
            row_cutout,
            col_cutout,
        ])

    def get_sigma(self):
        """
        pixels
        """
        return np.sqrt(4.0/2.0)

    def get_wcs(self):
        if self.ccdnum is not None:
            return GalsimWCSWrapper(self.piff_obj.wcs[self.ccdnum])
        else:
            return GalsimWCSWrapper(self.piff_obj.wcs[0])


# default G-I color for pixmappy
DEFAULT_COLOR = 1.1


class GalsimWCSWrapper(object):
    """
    wrapper for the galsim wcs, designed to be consistent
    with esutil WCS
    """
    def __init__(self, wcs, naxis=None):
        self._wcs = wcs
        self.set_naxis(naxis)

    def sky2image(self, ra, dec, color=None):

        if np.ndim(ra) == 0:
            ra = np.array(ra, copy=False, ndmin=1)
            dec = np.array(dec, copy=False, ndmin=1)
            if color is not None:
                color = np.array(color, copy=False, ndmin=1)

            is_scalar = True
        else:
            is_scalar = False

        if color is None:
            color = ra*0 + DEFAULT_COLOR

        ra = np.radians(ra)
        dec = np.radians(dec)
        x, y = self._wcs._xy(ra, dec, c=color)

        x += self._wcs.x0
        y += self._wcs.y0

        if is_scalar:
            x = x[0]
            y = y[0]

        return x, y

    def image2sky(self, col, row, color=None):
        if np.ndim(col) == 0:
            is_scalar = True
            col = np.array(col, copy=False, ndmin=1)
            row = np.array(row, copy=False, ndmin=1)

            if color is not None:
                color = np.array(color, copy=False, ndmin=1)
        else:
            is_scalar = False

        if color is None:
            color = row*0 + DEFAULT_COLOR

        x = col - self._wcs.x0
        y = row - self._wcs.y0
        ra, dec = self._wcs._radec(x, y, c=color)
        ra = np.degrees(ra)
        dec = np.degrees(dec)

        if is_scalar:
            ra = ra[0]
            dec = dec[0]
        return ra, dec

    def get_jacobian(self, x, y, color=None):

        if color is None:
            color = x*0 + DEFAULT_COLOR

        if np.ndim(x) > 0:
            num = len(x)
            dudcol = np.zeros(num)
            dudrow = np.zeros(num)
            dvdcol = np.zeros(num)
            dvdrow = np.zeros(num)
            for i in range(num):
                tdudcol, tdudrow, tdvdcol, tdvdrow = \
                    self._get_jacobian(x[i], y[i], color[i])
                dudcol[i] = tdudcol
                dudrow[i] = tdudrow
                dvdcol[i] = tdvdcol
                dvdrow[i] = tdvdrow
        else:
            dudcol, dudrow, dvdcol, dvdrow = \
                self._get_jacobian(x, y, color)

        return dudcol, dudrow, dvdcol, dvdrow

    def _get_jacobian(self, x, y, color):
        import galsim

        pos = galsim.PositionD(x=x, y=y)
        gs_jac = self._wcs.jacobian(image_pos=pos, color=color)

        dudcol = gs_jac.dudx
        dudrow = gs_jac.dudy
        dvdcol = gs_jac.dvdx
        dvdrow = gs_jac.dvdy

        return dudcol, dudrow, dvdcol, dvdrow

    def set_naxis(self, naxis):
        self._naxis = naxis

    def get_naxis(self):
        if self._naxis is not None:
            return self._naxis.copy()
        else:
            None
