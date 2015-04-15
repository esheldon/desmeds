import desdb

def get_meds_config_file(medsconf):
    """
    get the MEDS config file path

    $DESMEDS_CONFIG_DIR must be defined

    parameters
    ----------
    medsconf: string
        Identifier for the meds config, e.g. "meds013"
    """

    return desdb.files.get_url(type='medsconf',
                               medsconf=medsconf)

def read_meds_config(medsconf):
    """
    read the MEDS config file

    $DESMEDS_CONFIG_DIR must be defined

    parameters
    ----------
    medsconf: string
        Identifier for the meds config, e.g. "meds013"
    """
    import yaml
    fname=get_medsconf_file(medsconf)

    print("reading:",fname)
    with open(fname) as fobj:
        data=yaml.load(fobj)

    return data
