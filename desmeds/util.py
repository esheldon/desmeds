#!/usr/bin/env python
from __future__ import print_function
import os
import subprocess

DEFVAL = -9999
IMAGE_INFO_TYPES = ['image','weight','seg','bmask','bkg']

def fitsio_header_to_dict(hdr):
    """
    convert a fitsio FITSHDR object to a dict, for saving as
    a JSON string
    """
    d = {}
    for key in hdr.keys():
        if key != 'HISTORY' or key != "COMMENT":
            d[key.lower()] = hdr.get(key)
    return d

def add_naxis_to_fitsio_header(hdr,extra_hdr):
    """
    scamp astro refine headers don't contain naxis, so add it
    from an extra input header
    """
    if 'ZNAXIS1' in extra_hdr or 'ZNAXIS2' in extra_hdr:
        hdr.add_record({'name':'ZNAXIS1','value':extra_hdr['ZNAXIS1']})
        hdr.add_record({'name':'ZNAXIS2','value':extra_hdr['ZNAXIS2']})

    if 'NAXIS1' in extra_hdr or 'NAXIS2' in extra_hdr:
        hdr.add_record({'name':'NAXIS1','value':extra_hdr['NAXIS1']})
        hdr.add_record({'name':'NAXIS2','value':extra_hdr['NAXIS2']})

    return hdr


def check_for_required_config(conf, required):
    """
    make sure configuration fields exist
    """
    missing=[]
    for key in required:
        if key not in conf:
            missing.append(key)

    if len(missing) > 0:
        missing=', '.join(missing)
        raise RuntimeError("there are missing required "
                           "configuration parameters: %s" % missing)

def fpack_file(fname):
    cmd='fpack %s' % fname
    print("fpacking with command: '%s'" % cmd)
    subprocess.check_call(cmd,shell=True)


def load_psfmap(fname):
    import psfex

    pmap={}
    with open(fname) as fobj:
        for line in fobj:
            ls=line.split()
            if ls[0]=='-9999':
                continue

            expname=ls[0]
            ccdstr=ls[1]
            path=os.path.expandvars(ls[2])

            key = '%s-%s' % (expname, ccdstr)

            if 'psfexcat' in path:
                print("loading psfex:",path)
                p=psfex.PSFEx(path)
            else:
                raise ValueError("only psfex for now")
            
            pmap[key] = p

    return pmap

