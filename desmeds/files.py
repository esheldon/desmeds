from __future__ import print_function
import os
import desdb
import yaml

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


