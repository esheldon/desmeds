from __future__ import print_function
import sys
import os

from . import files

class Generator(dict):
    def __init__(self,
                 medsconf,
                 tilename,
                 band,
                 extra=None,
                 system='lsf',
                 missing=False):

        self['medsconf']=medsconf
        self['tilename']=tilename
        self['band']=band
        self.system=system
        self.missing=missing
        
        if extra is None:
            extra=''

        self['extra']=extra

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

        self['source_dir'] = files.get_source_dir(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )


        self['meds_file'] = files.get_meds_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
        )

        self.config=files.read_meds_config(medsconf)


    def write(self):
        """
        write the script and batch submission file
        """


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

        if 'coadd' in self.config:
            self._write_coadd_maker_script()
        else:
            self._write_maker_script()

    def _write_coadd_maker_script(self):
        make_dirs(self['script_file'])

        self['seed']=make_seed(self)

        script_file = os.path.expandvars(self['script_file'])
        with open(script_file, 'w') as fobj:
            text=_coadd_script_template % self
            fobj.write(text)


    '''
    def _write_coadd_script_old(self):
        make_dirs(self['script_file'])

        mf=self['meds_file']
        mf_nocoadd = mf.replace('.fits.fz','.fits')
        mf_nocoadd = mf_nocoadd.replace('.fits','-nocoadd.fits')
        self['meds_file_nocoadd'] = mf_nocoadd
        self['psfmap_file'] = files.get_psfmap_file(
            self['medsconf'], self['tilename'], self['band'],
        )

        if 'seed' not in self:
            # when making for a set, we do the seeds from
            # the global seed. Othewise generate it
            self['seed']=make_seed(self)

        script_file = os.path.expandvars(self['script_file'])
        with open(script_file,'w') as fobj:
            text=_coadd_script_template % self
            fobj.write(text)
    '''

    def _write_maker_script(self):
        make_dirs(self['script_file'])

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
            missing=self.missing,
        )
        lsf_file = os.path.expandvars(lsf_file)

        subfile=lsf_file+'.submitted'
        if self.missing and os.path.exists(self['meds_file']):
            if os.path.exists(lsf_file):
                os.remove(lsf_file)
            if os.path.exists(subfile):
                os.remove(subfile)
            return

        if os.path.exists(subfile):
            os.remove(subfile)

        self['file_front']=os.path.basename(
            lsf_file.replace(".lsf",'').replace('-missing','')
        )

        make_dirs(lsf_file)

        print("    writing lsf script:",lsf_file)
        with open(lsf_file,'w') as fobj:
            text=_lsf_template % self
            fobj.write(text)

        self._write_script()

    def _write_wq(self):
        """
        write the wq script
        """
        wq_file = files.get_meds_wq_file(
            self['medsconf'],
            self['tilename'],
            self['band'],
            missing=self.missing,
        )
        wq_file = os.path.expandvars(wq_file)

        if self.missing and os.path.exists(self['meds_file']):
            if os.path.exists(wq_file):
                os.remove(wq_file)
            wqlog=wq_file+'.wqlog'
            if os.path.exists(wqlog):
                os.remove(wqlog)
            return

        make_dirs(wq_file)
        print('    writing wq script:',wq_file)

        with open(wq_file, 'w') as fobj:
            text=_wq_make_meds_template % self
            fobj.write(text)

        self._write_script()

def make_dirs(*args):

    for f in args:
        d=os.path.dirname(f)
        if not os.path.exists(d):
            print('    making dir:',d)
            try:
                os.makedirs(d)
            except:
                pass

_lsf_template=r"""#!/bin/bash
#BSUB -J "meds-%(tilename)s-%(band)s"
#BSUB -oo ./%(file_front)s.oe
#BSUB -n 2
#BSUB -R span[hosts=1]
#BSUB -R "linux64 && rhel60 && (scratch > 20) && (!deft)"
#BSUB -W 48:00

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
N: 2
"""

_script_template=r"""#!/bin/bash

export OMP_NUM_THREADS=2

mkdir -p $TMPDIR

python -u $(which desmeds-make-meds) \
    --tmpdir=$TMPDIR \
    %(medsconf)s %(tilename)s %(band)s
"""

_coadd_script_template=r"""#!/bin/bash

export OMP_NUM_THREADS=2

mkdir -p $TMPDIR

python -u $(which desmeds-make-meds) \
    --tmpdir=$TMPDIR \
    --coadd \
    --seed=%(seed)d \
    %(medsconf)s %(tilename)s %(band)s
"""


_coadd_script_template_old=r"""#!/bin/bash

mkdir -p $TMPDIR
nocoadd_file=%(meds_file_nocoadd)s
band=%(band)s


(
    # we need to go into desdm mode in
    # a subshell.  Thes settings will not
    # persist

    echo "temporary loading DESDM framework"
    module unload anaconda
    source $HOME/eups/eups/desdm_eups_setup.sh
    setup pixcorrect 0.5.3+5
    setup MEPipelineAppIntg
    setup easyaccess
    setup pyyaml
    setup -r $HOME/exports/desdm_extra

    desmeds-make-meds \
        %(medsconf)s \
        %(tilename)s \
        ${band} \
        --tmpdir=$TMPDIR \
        --meds-file=${nocoadd_file}

)

desmeds-coadd \
        --tmpdir=$TMPDIR \
        %(medsconf)s  \
        ${nocoadd_file} \
        %(psfmap_file)s \
        %(seed)d \
        %(meds_file)s

echo "cleaning up temporary MEDS file"
rm -v ${nocoadd_file}

dir=$(dirname ${nocoadd_file})
ldir="${dir}/lists-${band}"
pdir="${dir}/psfs-${band}"

echo "cleaning temporary psf and list dirs"
rm -rv "${ldir}"
rm -rv "${pdir}"
"""

def make_seed(conf):
    """
    convert the input config file name to an integer for use
    as a seed
    """
    import hashlib

    s = '%s%s%s' % (conf['medsconf'], conf['tilename'], conf['band'])
    h = hashlib.sha256(s.encode('utf-8')).hexdigest()
    seed = int(h, base=16) % 2**30 
    return seed

