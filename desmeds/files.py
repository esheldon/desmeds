import desdb

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
    import yaml
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

    allruns=desdb.files.get_release_runs(data['release'],
                                         withbands=withbands)

    keeptiles=data['tilenames']

    runs=[]
    for tile in keeptiles:
        for run in allruns:
            if tile in run:
                runs.append(run)
                continue

    print "kept %d/%d runs" % (len(runs), len(allruns))
    return runs
