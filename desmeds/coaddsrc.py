from __future__ import print_function
import os
import shutil
import tempfile
import hashlib
import numpy
import fitsio

from . import files
from .coaddinfo import Coadd

class CoaddSrc(Coadd):
    """
    class to work with coadd sources (se images, etc.)
    """
    def __init__(self, *args, **kw):
        super(CoaddSrc,self).__init__(*args, **kw)
        self._set_finalcut_campaign()

    def get_info(self):
        """
        get info for the specified tilename and band
        """

        if hasattr(self,'_info_list'):
            info_list=self._info_list
        else:
            info_list = self._do_query()

            # sort the list to make code stable
            info_list = self._sort_list(info_list)

            # add full path info
            self._add_full_paths(info_list)

            self._info_list=info_list

        return info_list

    def _sort_list(self, info_list):
        """
        sort the list to make class stable against random return order
        from the database
        """

        # build hashes and sort
        hashes = []
        for i in range(len(info_list)):
            hash_str = "%s%s" % (
                info_list[i]['expnum'],
                info_list[i]['ccdnum'])
            hashes.append(hashlib.md5(hash_str.encode('utf-8')).hexdigest())
        inds = numpy.argsort(hashes)
        return [info_list[i] for i in inds]

    def _do_query(self):
        """
        get info for the specified tilename and band
        """

        if 'Y5' in self['campaign'] or 'Y6' in self['campaign']:
            query = _QUERY_COADD_SRC_BYTILE_Y5 % self
        elif 'COSMOS' in self['campaign']:
            query = _QUERY_COADD_SRC_BYTILE_Y3A2_COSMOS % self
        else:
            query = _QUERY_COADD_SRC_BYTILE_Y3 % self

        print(query)
        conn = self.get_conn()
        curs = conn.cursor()
        curs.execute(query)

        info_list=[]

        for row in curs:
            tile,expnum,ccdnum,path,fname,comp,band,pai,magzp = row
            info = {
                'tilename':tile,
                'expnum':expnum,
                'ccdnum':ccdnum,
                'filename':fname,
                'compression':comp,
                'path':path,
                'band':band,
                'pfw_attempt_id':pai,
                'magzp': magzp,
            }
            info_list.append(info)

        if 'Y6' in self['campaign']:
            imgs = ["'%s'" % info['filename'] for info in info_list]
            query = _QUERY_COADD_SRC_PIFF_FILES_Y6 % dict(
                piff_campaign=self['piff_campaign'],
                imgs=",".join(imgs)
            )

            print("cutting SE sources to those with piff files")
            conn = self.get_conn()
            curs = conn.cursor()
            curs.execute(query)
            piff_map = {}
            for row in curs:
                im, piff, path, band, expnum, ccdnum = row
                piff_map[(im, band, expnum, ccdnum)] = (path, piff)

            cut = 0
            new_info_list = []
            for info in info_list:
                key = (info['filename'], info['band'], info['expnum'], info['ccdnum'])
                if key in piff_map:
                    info['piff_path'] = os.path.join(piff_map[key][0], piff_map[key][1])
                    new_info_list.append(info)
                else:
                    cut += 1

            print("cut %d SE source for missing piff files" % cut)
            info_list = new_info_list

        return info_list


    def _add_full_paths(self, info_list):
        """
        seg maps have .fz for finalcut
        """


        for info in info_list:

            dirdict=self._get_all_dirs(info)

            info['image_path'] = os.path.join(
                dirdict['image']['local_dir'],
                info['filename']+info['compression'],
            )

            info['bkg_path'] = os.path.join(
                dirdict['bkg']['local_dir'],
                info['filename'].replace('immasked.fits','bkg.fits')+info['compression'],
            )

            info['seg_path'] = os.path.join(
                dirdict['seg']['local_dir'],
                info['filename'].replace('immasked.fits','segmap.fits')+info['compression'],
            )

            info['psf_path'] = os.path.join(
                dirdict['psf']['local_dir'],
                info['filename'].replace('immasked.fits','psfexcat.psf')
            )

            if "piff_campaign" in self:
                info['piff_path'] = os.path.join(
                    dirdict['piff']['local_dir'],
                    os.path.basename(info['piff_path']),
                )

    def _get_all_dirs(self, info):
        dirs={}

        path=info['path']
        dirs['image'] = self._get_dirs(path)
        dirs['seg']   = self._get_dirs(path, type='seg')
        dirs['bkg']   = self._get_dirs(path, type='bkg')
        dirs['psf']   = self._get_dirs(path, type='psf')
        if "piff_campaign" in self:
            dirs['piff'] = self._get_dirs(os.path.dirname(info['piff_path']), type='piff')
        return dirs

    def _extract_alt_dir(self, path, type):
        """
        extract the catalog path from an image path, e.g.

        OPS/finalcut/Y2A1v3/20161124-r2747/D00596130/p01/red/immask/

        would yield

        OPS/finalcut/Y2A1v3/20161124-r2747/D00596130/p01/red/bkg/
        OPS/finalcut/Y2A1v3/20161124-r2747/D00596130/p01/seg

        for piff we also replace the tag/campaign

        OPS/finalcut/Y6A1_PIFF/20181106-r5023/D00791633/p01/psf/
        """

        if type == "piff":
            return path

        ps = path.split('/')

        assert ps[-1]=='immask'

        if type=='bkg':
            ps[-1] = type
        elif type in ['seg', 'psf']:
            ps = ps[0:-1]
            assert ps[-1]=='red'
            ps[-1] = type if type != 'piff' else 'psf'

        return '/'.join(ps)

    def _set_finalcut_campaign(self):
        y3list=('Y3A1_COADD', 'Y3A2_COADD', )
        if self['campaign'] in y3list:
            self['finalcut_campaign']='Y3A1_FINALCUT'
        elif self['campaign']=='Y5A1_COADD':
            self['finalcut_campaign']='Y5A1_FINALCUT'
        elif self['campaign']=='Y3A2_COSMOS_COADD_TRUTH_V4':
            self['finalcut_campaign'] = 'COSMOS_COADD_TRUTH'
        elif self['campaign'] in ("Y6A2_COADD", "Y6A1_COADD"):
            self['finalcut_campaign'] = "Y6A1_COADD_INPUT"
            if "piff_campaign" not in self:
                self['piff_campaign'] = "Y6A1_PIFF"
        else:
            raise ValueError("determine finalcut campaign "
                             "for '%s'" % self['campaign'])


    def download(self, *args):
        raise NotImplementedError("use Coadd to download")
    def remove(self, *args):
        raise NotImplementedError("use Coadd to remove")


#select imagename, mag_zero from ZEROPOINT where IMAGENAME='D00504555_z_c41_r2378p01_immasked.fits' and source='FGCM' and version='v2.0';

_QUERY_COADD_SRC="""
select
    i.tilename || '-' || j.band as key,
    i.tilename,
    fai.path,
    j.filename as filename,
    fai.compression,
    j.band as band,
    i.pfw_attempt_id,
    z.mag_zero as magzp
from
    image i,
    image j,
    proctag tme,
    proctag tse,
    file_archive_info fai,
    zeropoint z
where
    tme.tag='{campaign}'
    and tme.pfw_attempt_id=i.pfw_attempt_id
    and i.filetype='coadd_nwgint'
    -- and i.tilename='DES0215-0458'
    and i.expnum=j.expnum
    and i.ccdnum=j.ccdnum
    and j.filetype='red_immask'
    and j.pfw_attempt_id=tse.pfw_attempt_id
    and tse.tag='{finalcut_campaign}'
    and fai.filename=j.filename
    -- and z.imagename = j.filename
    -- and z.source='FGCM'
    -- and z.version='v2.0'
    -- and rownum < 1000
"""

_QUERY_COADD_SRC_BYTILE_Y5_old="""
select
    i.tilename,
    fai.path,
    j.filename as filename,
    fai.compression,
    j.band as band,
    i.pfw_attempt_id,
    i.mag_zero as magzp
from
    image i,
    image j,
    proctag tme,
    proctag tse,
    file_archive_info fai
where
    tme.tag='%(campaign)s'
    and tme.pfw_attempt_id=i.pfw_attempt_id
    and i.filetype='coadd_nwgint'
    and i.tilename='%(tilename)s'
    and i.band='%(band)s'
    and i.expnum=j.expnum
    and i.ccdnum=j.ccdnum
    and j.filetype='red_immask'
    and j.pfw_attempt_id=tse.pfw_attempt_id
    and tse.tag='%(finalcut_campaign)s'
    and fai.filename=j.filename
order by
    filename
"""

_QUERY_COADD_SRC_BYTILE_Y5="""
select
    i.tilename,
    i.expnum,
    i.ccdnum,
    fai.path,
    j.filename as filename,
    fai.compression,
    j.band as band,
    i.pfw_attempt_id,
    i.mag_zero as magzp
from
    image i,
    image j,
    proctag tme,
    pfw_attempt_val av,
    proctag tse,
    file_archive_info fai
where
    tme.tag='%(campaign)s'
    and tme.pfw_attempt_id=av.pfw_attempt_id
    and av.key='tilename'
    and av.val='%(tilename)s'
    and av.pfw_attempt_id=i.pfw_attempt_id
    and i.filetype='coadd_nwgint'
    and i.band='%(band)s'
    and i.expnum=j.expnum
    and i.ccdnum=j.ccdnum
    and j.filetype='red_immask'
    and j.pfw_attempt_id=tse.pfw_attempt_id
    and tse.tag='%(finalcut_campaign)s'
    and fai.filename=j.filename
order by
    filename
"""

_QUERY_COADD_SRC_PIFF_FILES_Y6 = """
select
    d2.filename as redfile,
    fai.filename as filename,
    fai.path as path,
    m.band as band,
    m.expnum as expnum,
    m.ccdnum as ccdnum
from
    desfile d1,
    desfile d2,
    proctag t,
    opm_was_derived_from wdf,
    miscfile m,
    file_archive_info fai
where
    d2.filename in (%(imgs)s)
    and d2.id = wdf.parent_desfile_id
    and wdf.child_desfile_id = d1.id
    and d1.filetype = 'piff_model'
    and d1.pfw_attempt_id = t.pfw_attempt_id
    and t.tag = '%(piff_campaign)s'
    and d1.filename = m.filename
    and d1.id = fai.desfile_id
    and fai.archive_name = 'desar2home'
"""


_QUERY_COADD_SRC_BYTILE_Y3="""
select
    i.tilename,
    i.expnum,
    i.ccdnum,
    fai.path,
    j.filename as filename,
    fai.compression,
    j.band as band,
    i.pfw_attempt_id,
    z.mag_zero as magzp
from
    image i,
    image j,
    proctag tme,
    proctag tse,
    file_archive_info fai,
    zeropoint z
where
    tme.tag='%(campaign)s'
    and tme.pfw_attempt_id=i.pfw_attempt_id
    and i.filetype='coadd_nwgint'
    and i.band='%(band)s'
    and i.tilename='%(tilename)s'
    and i.expnum=j.expnum
    and i.ccdnum=j.ccdnum
    and j.filetype='red_immask'
    and j.pfw_attempt_id=tse.pfw_attempt_id
    and tse.tag='%(finalcut_campaign)s'
    and fai.filename=j.filename
    and z.imagename = j.filename
    and z.source='FGCM'
    and z.version='v2.0'
order by
    filename
"""

_QUERY_COADD_SRC_BYTILE_Y3A2_COSMOS = """
select
    i.tilename,
    i.expnum,
    i.ccdnum,
    fai.path,
    j.filename as filename,
    fai.compression,
    j.band as band,
    i.pfw_attempt_id,
    z.mag_zero as magzp
from
    image i,
    image j,
    proctag tme,
    proctag tse,
    file_archive_info fai,
    zeropoint z
where
    tme.tag='%(campaign)s'
    and tme.pfw_attempt_id=i.pfw_attempt_id
    and i.filetype='coadd_nwgint'
    and i.band='%(band)s'
    and i.tilename='%(tilename)s'
    and i.expnum=j.expnum
    and i.ccdnum=j.ccdnum
    and j.filetype='red_immask'
    and j.pfw_attempt_id=tse.pfw_attempt_id
    and tse.tag='%(finalcut_campaign)s'
    and fai.filename=j.filename
    and z.imagename = j.filename
    -- and z.source='FGCM'
    -- and z.version='v2.0'
    and ((z.source='FGCM' and z.version='y4a1_v1.5' and z.flag<16)
            or(z.source='PGCM_FORCED' and z.version='Y3A2_MISC' and z.flag<16))
order by
    filename
"""


_ZP_QUERY="""
select
    imagename,
    mag_zero as magzp
from
    zeropoint
where
    source='FGCM'
    and version='v2.0'
"""

_QUERY_COADD_SRC_old2="""
select
    i.tilename || '-' || j.band as key,
    i.tilename,
    fai.path,
    j.filename as filename,
    fai.compression,
    j.band as band,
    i.pfw_attempt_id
from
    image i,
    image j,
    proctag tme,
    proctag tse,
    file_archive_info fai
where
    tme.tag='{campaign}'
    and tme.pfw_attempt_id=i.pfw_attempt_id
    and i.filetype='coadd_nwgint'
    -- and i.tilename='DES0215-0458'
    and i.expnum=j.expnum
    and i.ccdnum=j.ccdnum
    and j.filetype='red_immask'
    and j.pfw_attempt_id=tse.pfw_attempt_id
    and tse.tag='{finalcut_campaign}'
    and fai.filename=j.filename
    --and rownum < 1000
"""
