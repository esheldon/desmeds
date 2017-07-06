from __future__ import print_function
import sys
import os

from . import files

class Generator(dict):
    def __init__(self, medsconf, tilename, band, extra=None, system='lsf'):

        self['medsconf']=medsconf
        self['tilename']=tilename
        self['band']=band
        
        if extra is None:
            extra=''

        self['extra']=extra
        self.system=system

        self['script_file']=files.get_meds_script(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        self['log_file'] = files.get_meds_log_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

    def write(self):
        """
        write the script and batch submission file
        """

        self._write_script()

        if self.system=="lsf":
            self._write_lsf()
        elif self.system=="wq":
            self._write_wq()
        else:
            raise ValueError("bad system '%s'" % self.system)

    def _write_script(self):
        """
        write the shell script
        """

        make_dirs(self['script_file'])

        print("writing script:",self['script_file'])
        with open(self['script_file'],'w') as fobj:
            text=_script_template % self
            fobj.write(text)


    def _write_lsf(self):
        """
        write the lsf file for making the MEDS file
        """

        lsf_file = files.get_meds_lsf_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        self['file_front']=os.path.basename(lsf_file.replace(".lsf",''))

        make_dirs(lsf_file)

        print("writing lsf script:",lsf_file)
        with open(lsf_file,'w') as fobj:
            text=_lsf_template % self
            fobj.write(text)

    def _write_wq(self, type):
        """
        write the wq script
        """
        wq_file = files.get_meds_wq_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        make_dirs(wq_file)
        print('writing wq script:',wq_file)

        with open(wq_file,'w') as fobj:
            text=_wq_make_meds_template % self
            fobj.write(text)


def make_dirs(*args):

    for f in args:
        d=os.path.dirname(f)
        if not os.path.exists(d):
            print('making dir:',d)
            try:
                os.makedirs(d)
            except:
                pass

_lsf_template=r"""#!/bin/bash
#BSUB -J "meds-%(tilename)s-%(band)s"
#BSUB -oo ./%(file_front)s.oe
#BSUB -R "linux64 && rhel60 && scratch > 20"
#BSUB -n 1
#BSUB -W 12:00

export TMPDIR=/scratch/$USER/$LSB_JOBID-$LSB_JOBINDEX

mkdir -pv $TMPDIR

log_file=%(log_file)s
tmp_log=$(basename $log_file)
tmp_log="$TMPDIR/$tmp_log"

bash %(script_file)s &> ${tmp_log}

mv -fv "${tmp_log}" "${log_file}" 1>&2

rm -rv $TMPDIR
"""


_wq_make_meds_template=r"""
command: |
    %(extra)s

    tmpdir=$TMPDIR/meds-%(tilename)s-%(band)s
    export TMPDIR=$tmpdir

    mkdir -pv $TMPDIR

    log_file=%(log_file)s
    tmp_log=$(basename $log_file)
    tmp_log="$TMPDIR/$tmp_log"

    bash %(script_file)s &> ${tmp_log}

    mv -fv "${tmp_log}" "${log_file}" 1>&2

    rm -rv $tmpdir

job_name: "meds-%(tilename)s-%(band)s"
"""

_script_template=r"""#!/bin/bash

mkdir -p $TMPDIR

desmeds-make-meds \
    --tmpdir=$TMPDIR \
    %(medsconf)s %(tilename)s %(band)s
"""


