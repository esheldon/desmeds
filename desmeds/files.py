from __future__ import print_function
import os
import desdb
import yaml
import tempfile

def get_config_dir():
    """
    the config directory
    """
    if 'DESMEDS_CONFIG_DIR' not in os.environ:
        raise RuntimeError("you need to define $DESMEDS_CONFIG_DIR")
    return os.environ['DESMEDS_CONFIG_DIR']

def get_meds_config_file(medsconf):
    """
    get the MEDS config file path

    $DESMEDS_CONFIG_DIR must be defined

    parameters
    ----------
    medsconf: string
        Identifier for the meds config, e.g. "013"
    """
    dir=get_config_dir()
    fname='meds%s.yaml' % medsconf
    return os.path.join(dir, fname)


def read_meds_config(medsconf):
    """
    read the MEDS config file

    $DESMEDS_CONFIG_DIR must be defined

    parameters
    ----------
    medsconf: string
        Identifier for the meds config, e.g. "013"
    """
    fname=get_meds_config_file(medsconf)

    print("reading:",fname)
    with open(fname) as fobj:
        data=yaml.load(fobj)

    return data

def get_testbed_config_file(testbed):
    """
    get the testbed config file path

    $DESMEDS_CONFIG_DIR must be defined

    parameters
    ----------
    testbed: string
        Identifier for the testbed, e.g. "sva1-2"
    """
    dir=get_config_dir()
    fname='testbed-%s.yaml' % testbed
    return os.path.join(dir, fname)

def read_testbed_config(testbed):
    """
    read the testbed configuration

    $DESMEDS_CONFIG_DIR must be defined

    parameters
    ----------
    testbed: string
        Identifier for the testbed, e.g. "sva1-2"
    """

    fname=get_testbed_config_file(testbed)

    print("reading:",fname)
    with open(fname) as fobj:
        data=yaml.load(fobj)

    return data

def get_testbed_runs(testbed, withbands=None):
    """
    read the testbed config and get the runlist
    """
    import desdb


    data=read_testbed_config(testbed)

    print("getting runs for testbed:",testbed)
    allruns=desdb.files.get_release_runs(data['release'],
                                         withbands=withbands)

    keeptiles=data['tilenames']

    runs=[]
    for tile in keeptiles:
        for run in allruns:
            if tile in run:
                runs.append(run)
                continue

    print("kept %d/%d runs" % (len(runs), len(allruns)))
    return runs


#
# directories
#

def get_meds_base():
    """
    The base directory $DESDATA/meds
    """
    d=os.environ['DESDATA']
    return os.path.join(d, 'meds')

def get_meds_data_dir(meds_vers, coadd_run):
    """
    get the meds data directory for the input coadd run

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    """

    bdir = get_meds_base()
    return os.path.join(bdir, meds_vers, coadd_run)

def get_meds_script_dir(meds_vers):
    """
    get the meds script directory

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    """

    bdir = get_meds_base()
    return os.path.join(bdir, meds_vers, 'scripts')

#
# file paths
#

def get_stubby_meds_file(coadd_run,band,medsconf):
    """
    a temporary file to hold the inputs to a MEDSMaker
    """
    dr = get_meds_dir(coadd_run,band,medsconf)
    tilename = coadd_run.split('_')[-1]
    return os.path.join(dr,'%s-%s-stubby-meds-%s.fits' % (tilename,band,medsconf))


def get_meds_file(meds_vers, coadd_run, tilename, band):
    """
    get the meds file for the input coadd run, tilename, band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds'
    ext='fits.fz'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)

def get_meds_stubby_file(meds_vers, coadd_run, tilename, band):
    """
    get the stubby meds file, holding inputs for the MEDSMaker

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds-stubby'
    ext='fits'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)

def get_meds_stats_file(meds_vers, coadd_run, tilename, band):
    """
    get the meds stats file for the input coadd run, tilename, band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds-stats'
    ext='yaml'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)

def get_meds_status_file(meds_vers, coadd_run, tilename, band):
    """
    get the meds status file for the input coadd run, tilename, band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds-status'
    ext='yaml'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)


def get_meds_srclist_file(meds_vers, coadd_run, tilename, band):
    """
    get the meds source list file for the input coadd run, tilename, band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds-srclist'
    ext='dat'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)

def get_meds_input_file(meds_vers, coadd_run, tilename, band):
    """
    get the meds input catalog file for the input coadd run, tilename, band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds-input'
    ext='dat'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)

def get_meds_coadd_objects_id_file(meds_vers, coadd_run, tilename, band):
    """
    get the coadd objects id file for the input coadd run, tilename, band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    type='meds-coadd-objects-id'
    ext='dat'
    return get_meds_datafile_generic(meds_vers,
                                     coadd_run,
                                     tilename,
                                     band,
                                     type,
                                     ext)


def get_meds_datafile_generic(meds_vers, coadd_run, tilename, band, type, ext):
    """
    get the meds directory for the input coadd run

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    coadd_run: string
        For SV and Y1, e.g. '20130828000021_DES0417-5914'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    type: string
        e.g. 'meds' 'meds-stats' etc.
    ext: string
        extension, e.g. 'fits.fz' 'yaml' etc.
    """

    dir = get_meds_data_dir(meds_vers, coadd_run)

    fname='%(tilename)s-%(band)s-%(type)s-%(meds_vers)s.%(ext)s'
    fname = fname % dict(tilename=tilename,
                         band=band,
                         type=type,
                         meds_vers=meds_vers,
                         ext=ext)
    return os.path.join(dir, fname)





def get_meds_script_file(meds_vers, tilename, band):
    """
    get the meds script maker file for the given tilename and band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    ext='sh'
    return get_meds_script_file_generic(meds_vers, tilename, band, ext)

def get_meds_wq_file(meds_vers, tilename, band):
    """
    get the meds wq script file for the given tilename and band

    parameters
    ----------
    meds_vers: string
        A name for the meds version or config.  e.g. '013'
        or 'y1a1-v01'
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    """

    ext='yaml'
    return get_meds_script_file_generic(meds_vers, tilename, band, ext)


def get_meds_script_file_generic(meds_vers, tilename, band, ext):
    """
    get the meds script maker file for the given tilename and band

    parameters
    ----------
    tilename: string
        e.g. 'DES0417-5914'
    band: string
        e.g. 'i'
    ext: string
        extension, e.g. 'sh' 'yaml'
    """
    dir=get_meds_script_dir(meds_vers)
    fname = '%(tilename)s-%(band)s-meds.%(ext)s'
    fname = fname % dict(tilename=tilename,
                         band=band,
                         ext=ext)

    return os.path.join(dir, fname)


class StagedInFile(object):
    """
    A class to represent a staged file
    If tmpdir=None no staging is performed and the original file path is used

    parameters
    ----------
    fname: string
        original file location
    tmpdir: string, optional
        If not sent, no staging is done.

    examples
    --------
    # using a context for the staged file
    fname="/home/jill/output.dat"
    tmpdir="/tmp"
    with StagedInFile(fname,tmpdir=tmpdir) as sf:
        with open(sf.path) as fobj:
            # read some data

    """
    def __init__(self, fname, tmpdir=None):

        self._set_paths(fname, tmpdir=tmpdir)
        self.stage_in()

    def _set_paths(self, fname, tmpdir=None):
        fname=expandpath(fname)

        self.original_path = fname

        if tmpdir is not None:
            self.tmpdir = expandpath(tmpdir)
        else:
            self.tmpdir = tmpdir

        self.was_staged_in = False
        self._stage_in = False

        if self.tmpdir is not None:
            bdir,bname = os.path.split(self.original_path)
            self.path = os.path.join(self.tmpdir, bname)

            if self.tmpdir == bdir:
                # the user sent tmpdir as the source dir, no
                # staging is performed
                self._stage_in = False
            else:
                self._stage_in = True

    def stage_in(self):
        """
        make a local copy of the file
        """
        import shutil

        if self._stage_in:
            if not os.path.exists(self.original_path):
                raise IOError("file not found:",self.original_path)

            if os.path.exists(self.path):
                print("removing existing file:",self.path)
                os.remove(self.path)
            else:
                makedir_fromfile(self.path)

            print("staging in",self.original_path,"->",self.path)
            shutil.copy(self.original_path,self.path)

            self.was_staged_in = True

    def cleanup(self):
        if os.path.exists(self.path) and self.was_staged_in:
            print("removing temporary file:",self.path)
            os.remove(self.path)
            self.was_staged_in = False

    def __del__(self):
        self.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.cleanup()


class StagedOutFile(object):
    """
    A class to represent a staged file
    If tmpdir=None no staging is performed and the original file
    path is used
    parameters
    ----------
    fname: string
        Final destination path for file
    tmpdir: string, optional
        If not sent, or None, the final path is used and no staging
        is performed
    must_exist: bool, optional
        If True, the file to be staged must exist at the time of staging
        or an IOError is thrown. If False, this is silently ignored.
        Default False.
    examples
    --------

    fname="/home/jill/output.dat"
    tmpdir="/tmp"
    with StagedOutFile(fname,tmpdir=tmpdir) as sf:
        with open(sf.path,'w') as fobj:
            fobj.write("some data")

    """
    def __init__(self, fname, tmpdir=None, must_exist=False):

        self.must_exist = must_exist
        self.was_staged_out = False

        self._set_paths(fname, tmpdir=tmpdir)


    def _set_paths(self, fname, tmpdir=None):
        fname=expandpath(fname)

        self.final_path = fname

        if tmpdir is not None:
            self.tmpdir = expandpath(tmpdir)
        else:
            self.tmpdir = tmpdir

        fdir = os.path.dirname(self.final_path)

        if self.tmpdir is None:
            self.is_temp = False
            self.path = self.final_path
        else:
            if not os.path.exists(self.tmpdir):
                os.makedirs(self.tmpdir)

            bname = os.path.basename(fname)
            self.path = os.path.join(self.tmpdir, bname)

            if self.tmpdir==fdir:
                # the user sent tmpdir as the final output dir, no
                # staging is performed
                self.is_temp = False
            else:
                self.is_temp = True

    def stage_out(self):
        """
        if a tempdir was used, move the file to its final destination
        note you normally would not call this yourself, but rather use a
        context, in which case this method is called for you
        with StagedOutFile(fname,tmpdir=tmpdir) as sf:
            #do something
        """
        import shutil

        if self.is_temp and not self.was_staged_out:
            if not os.path.exists(self.path):
                if self.must_exist:
                    raise IOError("temporary file not found:",self.path)

            if os.path.exists(self.final_path):
                print("removing existing file:",self.final_path)
                os.remove(self.final_path)

            makedir_fromfile(self.final_path)

            print("staging out '%s' -> '%s'" % (self.path,self.final_path))
            shutil.move(self.path,self.final_path)

        self.was_staged_out=True

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.stage_out()

class TempFile(object):
    """
    A class to represent a temporary file

    parameters
    ----------
    fname: string
        The full path for file

    examples
    --------

    # using a context for the staged file
    fname="/home/jill/output.dat"
    with TempFile(fname,tmpdir=tmpdir) as sf:
        with open(sf.path,'w') as fobj:
            fobj.write("some data")

            # do something with the file
    """
    def __init__(self, fname):
        self.path = fname

        self.was_cleaned_up = False

    def cleanup(self):
        """
        remove the file if it exists, if not already cleaned up
        """
        import shutil

        if not self.was_cleaned_up:
            if os.path.exists(self.path):
                os.remove(self.path)

            self.was_cleaned_up=True

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.cleanup()


def expandpath(path):
    """
    expand environment variables, user home directories (~), and convert
    to an absolute path
    """
    path=os.path.expandvars(path)
    path=os.path.expanduser(path)
    path=os.path.abspath(path)
    return path


def makedir_fromfile(fname):
    """
    extract the directory and make it if it does not exist
    """
    dname=os.path.dirname(fname)
    try_makedir(dname)

def try_makedir(dir):
    """
    try to make the directory
    """
    if not os.path.exists(dir):
        try:
            print("making directory:",dir)
            os.makedirs(dir)
        except:
            # probably a race condition
            pass

def get_temp_dir():
    """
    get a temporary directory.  Check for batch system specific
    directories in environment variables, falling back to TMPDIR
    """
    tmpdir=os.environ.get('_CONDOR_SCRATCH_DIR',None)
    if tmpdir is None:
        tmpdir=os.environ.get('TMPDIR',None)
        if tmpdir is None:
            tmpdir = tempfile.mkdtemp()
    return tmpdir


