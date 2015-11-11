from __future__ import print_function
import sys
import os
import numpy
import desdb
import fitsio

from . import files

_wq_make_stubby_template="""
command: |
    medsconf="%(medsconf)s"
    coadd_run="%(coadd_run)s"
    band="%(band)s"
    desmeds-make-stubby-meds $medsconf $coadd_run $band

job_name: %(job_name)s
"""

_wq_make_meds_template="""
command: |
    medsconf="%(medsconf)s"
    coadd_run="%(coadd_run)s"
    band="%(band)s"
    desmeds-make-meds --from-stubby $medsconf $coadd_run $band

job_name: %(job_name)s
mode: bynode
"""

def release_is_sva1(release):
    if isinstance(release,basestring):
        return 'sva1' in release.lower()
    else:
        for r in release:
            if 'sva1' in r.lower():
                return True

    return False

class Generator(object):
    def __init__(self, medsconf, check=False):

        self.medsconf=medsconf
        self.conf=files.read_meds_config(medsconf)
        self.conn=desdb.Connection()

        self.check=check

        self.df=desdb.files.DESFiles()

    def load_coadd(self, coadd_run, band):
        """
        load all the relevant info for the specified coadd and band
        """
        self.coadd_run=coadd_run
        self.band=band

        print("loading coadd info and srclist")
        self.cf=desdb.files.Coadd(coadd_run=coadd_run,
                                  band=band,
                                  conn=self.conn)

        if self.check:
            do_srclist=True
        else:
            do_srclist=False

        self.cf.load(srclist=do_srclist)

        nmissing=0
        if self.check:
            nmissing += self._check_all()

        return nmissing

    def write_all(self):
        """
        write all part
        """
        self.write_make_stubby_wq()
        self.write_make_meds_wq()

    def write_make_meds_wq(self):
        """
        write the wq script
        """
        self._write_wq('meds')

    def write_make_stubby_wq(self):
        """
        write the wq script
        """
        self._write_wq('stubby')

    def _write_wq(self, type):
        """
        write the wq script
        """

        job_name='%s-%s' % (self.cf['tilename'],self.band)
        d={'medsconf':self.medsconf,
           'job_name':job_name,
           'coadd_run':self.cf['coadd_run'],
           'band':self.cf['band']}

        if type=='stubby':
            wq_file = files.get_meds_stubby_wq_file(self.medsconf,
                                                    self.cf['tilename'],
                                                    self.band)

            template=_wq_make_stubby_template
        else:
            wq_file = files.get_meds_wq_file(self.medsconf,
                                             self.cf['tilename'],
                                             self.band)

            template=_wq_make_meds_template

        text=template % d

        make_dirs(wq_file)
        print('writing wq script:',wq_file)

        with open(wq_file,'w') as fobj:
            fobj.write(text)

    def _check_all(self):
        nmissing = 0
        for r in self.cf.srclist:
            nmissing += self.do_check_inputs(r)
        print('nmissing: ',nmissing)

        return nmissing


    def do_check_inputs(self, r):
        nmissing=0
        for ftype in ['red_image','red_bkg','red_seg']:
            if not os.path.exists(r[ftype]):
                print("missing %s %s %s: %s" % (r['run'],r['expname'],ftype,r[ftype]))
                nmissing+=1

        return nmissing


def make_dirs(*args):

    for f in args:
        d=os.path.dirname(f)
        if not os.path.exists(d):
            print('making dir:',d)
            try:
                os.makedirs(d)
            except:
                pass

