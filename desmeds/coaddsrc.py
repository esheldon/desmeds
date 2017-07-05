from __future__ import print_function
import os
import shutil
import tempfile
import numpy
import fitsio

from . import files
from .coaddinfo import CoaddCache, Coadd, make_cache_key

class CoaddSrc(Coadd):
    def get_info(self, tilename, band):
        """
        get info for the specified tilename and band
        """
        info_list = self.cache.get_info(tilename, band)

        # add full path info
        self._add_full_paths(info_list)

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


    def _set_cache(self):
        self.cache = CoaddSrcCache(self.campaign)

    def _get_all_dirs(self, info):
        dirs={}

        path=info['path']
        dirs['image'] = self._get_dirs(path)
        dirs['seg']   = self._get_dirs(path, type='seg')
        dirs['bkg']   = self._get_dirs(path, type='bkg')
        dirs['psf']   = self._get_dirs(path, type='psf')
        return dirs

    def _extract_alt_dir(self, path, type):
        """
        extract the catalog path from an image path, e.g.

        OPS/finalcut/Y2A1v3/20161124-r2747/D00596130/p01/red/immask/

        would yield

        OPS/finalcut/Y2A1v3/20161124-r2747/D00596130/p01/red/bkg/
        OPS/finalcut/Y2A1v3/20161124-r2747/D00596130/p01/seg

        """

        ps = path.split('/')

        assert ps[-1]=='immask'

        if type=='bkg':
            ps[-1] = type
        elif type in ['seg','psf']:
            ps = ps[0:-1]
            assert ps[-1]=='red'
            ps[-1] = type

        return '/'.join(ps)

    def download(self, *args):
        raise NotImplementedError("use Coadd to download")
    def remove(self, *args):
        raise NotImplementedError("use Coadd to remove")



class CoaddSrcCache(CoaddCache):
    """
    cache to hold path info for the sources of all
    coadds in the given campaign
    """
    def __init__(self, campaign='Y3A1_COADD'):
        self.campaign=campaign.upper()
        self._set_finalcut_campaign()

    def get_info(self, tilename, band):
        """
        get info for the specified tilename and band
        """
        cache=self.get_data()

        key = make_cache_key(tilename, band)
        w,=numpy.where(cache['key']==key)

        if w.size == 0:
            raise ValueError("tilename '%s' and band '%s' "
                             "not found" % (tilename,band))

        entries=[]

        for i in w:
            c=cache[i]

            tilename=c['tilename'].strip()
            path=c['path'].strip()
            filename=c['filename'].strip()
            band=c['band'].strip()
            comp=c['compression'].strip()

            entry = {
                'tilename':tilename,
                'filename':filename,
                'compression':comp,
                'path':path,
                'band':band,
                'pfw_attempt_id':c['pfw_attempt_id'],
            }

            entries.append(entry)


        return entries

    def get_data(self):
        """
        get the full cache data
        """
        if not hasattr(self,'_cache'):
            self.load_cache()
        return self._cache

    def load_cache(self):
        """
        load the cache into memory
        """

        fname=self.get_filename()
        if not os.path.join(fname):
            self.make_cache()

        print("loading cache:",fname)
        self._cache=fitsio.read(fname)

    def get_filename(self):
        """
        path to the cache
        """
        return files.get_coadd_src_cache_file(self.campaign)

    '''
    def _get_dtype(self):
        return [ 
            ('key','S14'),
            ('tilename','S12'),
            ('path','S65'),
            ('filename','S40'),
            ('compression','S3'),
            ('band','S1'),
            ('pfw_attempt_id','i8'),
        ]
    '''

    def _get_query(self):
        query = _QUERY_COADD_SRC.format(
            campaign=self.campaign,
            finalcut_campaign=self.finalcut_campaign,
        )
        return query

    def _set_finalcut_campaign(self):
        if self.campaign=='Y3A1_COADD':
            self.finalcut_campaign='Y3A1_FINALCUT'
        else:
            raise ValueError("determine finalcut campaign "
                             "for '%s'" % self.campaig)



_QUERY_COADD_SRC="""
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

_QUERY_COADD_SRC_OLD="""
SELECT
    hdr.tilename || '-' || msk.band as key,
    hdr.tilename,
    msk.band         as band,
    fhdr.path        as head_path,
    hdr.filename     as head_filename,
    fmsk.path        as immask_path,
    fmsk.filename    as immask_filename,
    fmsk.compression as immask_compression,
    msk.pfw_attempt_id
FROM
    proctag tc,
    proctag ts,
    image msk,
    image nwg,
    miscfile hdr,
    file_archive_info fhdr,
    file_archive_info fmsk
WHERE
    tc.tag='{campaign}'
    and ts.tag='{finalcut_campaign}'
    and ts.pfw_attempt_id=msk.pfw_attempt_id
    and tc.pfw_attempt_id=hdr.pfw_attempt_id
    -- and hdr.tilename='DES0158-3957'
    and nwg.tilename=hdr.tilename
    and msk.ccdnum=hdr.ccdnum
    and nwg.ccdnum=hdr.ccdnum
    and msk.expnum=hdr.expnum
    and nwg.expnum=hdr.expnum
    and hdr.filename=fhdr.filename
    and msk.filename=fmsk.filename
    and hdr.filetype='coadd_head_scamp'
    and msk.filetype='red_immask'
    and nwg.filetype='coadd_nwgint'
    and fhdr.archive_name='desar2home'
    --and rownum < 1000
"""
