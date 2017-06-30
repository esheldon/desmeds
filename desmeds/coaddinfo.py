from __future__ import print_function
import os
import numpy
import fitsio
import easyaccess as ea

class Coadd(object):
    def __init__(self, campaign='Y3A1_COADD'):
        self.campaign=campaign.upper()

    def download(self, tilename, band=None):
        """
        download a single tile
        """
        info=self.get_info(tilename)

        im_local_dir, im_remote_dir = self._get_dirs(info)

        cat_local_dir=extract_cat_dir(im_local_dir)
        cat_remote_dir=extract_cat_dir(im_remote_dir)

        dirs = [
            ('image',im_local_dir,im_remote_dir),
            ('cat',cat_local_dir,cat_remote_dir),
        ]
        for type, local_dir, remote_dir in dirs:

            if not os.path.exists(local_dir):
                print("making local directory:",local_dir)
                os.makedirs(local_dir)

            if band is not None:
                if type=='cat':
                    remote_pattern='%s/*_%s_cat.fits' % (remote_dir,band)
                else:
                    remote_pattern='%s/*_%s.fits*' % (remote_dir,band)
            else:
                remote_pattern='%s/' % remote_dir

            cmd = r"""
    rsync \
        -avP \
        --password-file $DES_RSYNC_PASSFILE \
        {remote_pattern} \
        {local_dir}/
        """.format(remote_pattern=remote_pattern,
                   local_dir=local_dir)
            cmd = os.path.expandvars(cmd)

            print(cmd)
            ret=os.system(cmd)

            if ret != 0:
                raise RuntimeError("rsync failed")


    def get_info(self, tilename, band='i'):
        """
        get info for the specified tilename and band
        """

        key = self.make_key(tilename, band)

        cache = self.get_cache()
        if key not in cache:
            raise ValueError("%s not found in cache" % key)
        return cache[key]

    def get_cache(self):
        """
        get the cache
        """
        if not hasattr(self,'_cache'):
            self.load_cache()

        return self._cache

    def load_cache(self):
        """
        load the cache into memory
        """

        fname=self.get_cache_file()
        if not os.path.join(fname):
            self.make_cache()

        print("loading cache:",fname)
        fcache=fitsio.read(fname)

        cache={}
        for i in xrange(fcache.size):
            c = fcache[i]

            tilename=c['tilename'].strip()
            path=c['path'].strip()
            filename=c['filename'].strip()
            band=c['band'].strip()
            comp=c['compression'].strip()
            
            key=self.make_key(tilename, band)
            cache[key] = {
                'tilename':tilename,
                'filename':filename,
                'compression':comp,
                'path':path,
                'band':band,
                'pfw_attemp_id':c['pfw_attemp_id'],
            }


        self._cache=cache

    def make_key(self, tilename, band):
        return '%s-%s' % (tilename, band)

    def make_cache(self):
        """
        cache all the relevant information for this campaign
        """

        fname=self.get_cache_file()

        print("writing to:",fname)
        q = _QUERY_ALL_TEMPLATE.format(
            campaign=self.campaign,
        )

        curs = self._doquery(q)

        dt=[
            ('tilename','S12'),
            ('path','S60'),
            ('filename','S35'),
            ('compression','S5'),
            ('band','S1'),
            ('pfw_attemp_id','i8'),

        ]

        info=numpy.fromiter(curs, dtype=dt)


        print("writing to:",fname)
        fitsio.write(fname, info, clobber=True)

    def get_cache_file(self):
        """
        path to the cache
        """
        dir=os.path.expandvars('$DESDATA/lists')

        fname='%s-coadd-cache.fits' % self.campaign

        fname = os.path.join(dir, fname)
        return fname


    def _doquery(self, query):

        print(query)
        conn=self.get_conn()
        curs = conn.cursor()
        curs.execute(query)

        return curs

    def _get_dirs(self, info):
        local_dir = '$DESDATA/%(path)s' % info
        remote_dir = '$DESREMOTE_RSYNC/%(path)s' % info

        local_dir=os.path.expandvars(local_dir)
        remote_dir=os.path.expandvars(remote_dir)

        return local_dir, remote_dir

    def _make_paths(self, info):
        tpath = '%(path)s/%(filename)s%(compression)s' % info

        local_path = '$DESDATA/%s' % tpath
        remote_path = '$DESREMOTE_RSYNC/%s' % tpath

        #local_path = os.path.expandvars(local_path)
        #remote_path = os.path.expandvars(remote_path)

        return local_path, remote_path

    def get_conn(self):
        if not hasattr(self, '_conn'):
            self._make_conn()

        return self._conn
    def _make_conn(self):
        self._conn=ea.connect(section='desoper')

def extract_cat_dir(path):
    """
    extract the catalog path from an image path, e.g.

    OPS/multiepoch/Y3A1/r2577/DES0215-0458/p01/coadd/

    would yield

    OPS/multiepoch/Y3A1/r2577/DES0215-0458/p01/cat/
    """

    ps = path.split('/')

    assert ps[-1]=='coadd'

    ps[-1] = 'cat'
    return '/'.join(ps)


def extract_cat_path(path):
    """
    extract the catalog path from an image path, e.g.

    OPS/multiepoch/Y3A1/r2577/DES0215-0458/p01/coadd/DES0215-0458_r2577p01_r.fits.fz

    would yield

    OPS/multiepoch/Y3A1/r2577/DES0215-0458/p01/cat/DES0215-0458_r2577p01_r_cat.fits
    """

    ps = path.split('/')

    assert ps[-2]=='coadd'

    fname=ps[-1]

    fname = fname.replace('.fits.fz','.fits')
    fname = fname.replace('.fits','_cat.fits')

    ps[-2] = 'cat'
    ps[-1] = fname

    return '/'.join(ps)

_QUERY_ALL_TEMPLATE="""
select
    m.tilename as tilename,
    fai.path as path,
    fai.filename as filename,
    fai.compression as compression,
    m.band as band,
    m.pfw_attempt_id as pfw_attempt_id

from
    prod.proctag t,
    prod.coadd m,
    prod.file_archive_info fai
where
    t.tag='{campaign}'
    and t.pfw_attempt_id=m.pfw_attempt_id
    and m.filetype='coadd'
    and fai.filename=m.filename
    and fai.archive_name='desar2home'\n"""

_QUERY_TEMPLATE="""
select
    fai.path as path,
    fai.filename as filename,
    fai.compression as compression,
    m.band as band,
    m.pfw_attempt_id as pfw_attempt_id

from
    prod.proctag t,
    prod.coadd m,
    prod.file_archive_info fai
where
    t.tag='{campaign}'
    and t.pfw_attempt_id=m.pfw_attempt_id
    and m.tilename='{tilename}'
    and m.filetype='coadd'
    and fai.filename=m.filename
    and fai.archive_name='desar2home' and rownum <= 10\n"""
