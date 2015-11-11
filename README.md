# desmeds
code specific to des MEDS production

## generating a single MEDS file

```bash
# first make a "stubby" meds, holding all the inputs for the MEDSMaker
# this is run first because it needs network and db access
desmeds-make-stubby-meds medsconf coadd_run band

# now make the full meds, which does not require db access
desmeds-make-meds medsconf coadd_run band

# a worked example
medsconf="tb-y1a1-v01d"
coadd_run="20141105000042_DES0347-5540"
band="z"
desmeds-make-stubby-meds $medsconf $coadd_run $band
desmeds-make-meds $medsconf $coadd_run $band
```

## generating scripts to make MEDS files for a DESDM release
```python
desmeds-gen-all-release medsconf
```
The above generates all the [wq](https://github.com/esheldon/wq) submit scripts.
The `wq` submit scripts call `des-make-meds`

For example meds config files, see https://github.com/esheldon/desmeds-config
An example testbed is `medstb-y1a1-v01d.yaml`. Note you need the environment variable
`DESMEDS_CONFIG_DIR` set to point to the location of the config files.

## installation
```
python setup.py install
python setup.py install --prefix=/some/path
```

## requirements

* [meds](https://github.com/esheldon/meds) (version >= 0.9.0)
* [desdb](https://github.com/esheldon/desdb) (version >= 0.9.0)
* [fitsio](https://github.com/esheldon/fitsio) (use git master for now)
* [esutil](https://github.com/esheldon/esutil) (version >= 0.5.3)
* The `$DESDATA` environment variable should point to the
    root of the des data on your system
* The `$DESMEDS_CONFIG_DIR` environment variable should point to the location of the config files
