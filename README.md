# desmeds
code specific to des MEDS production

## generating scripts to make MEDS files for a DESDM release
```python
desmeds-gen-all-release medsconf
```
The above generates all the `wq` submit scripts.

For example meds config files, see https://github.com/esheldon/desmeds-config
An example is `medstb-y1a1-v01d.yaml`. Note you need the environment variable
`DESMEDS_CONFIG_DIR` set to point to the location of the config files.

## generating a single MEDS file

The `wq` submit scripts call the following scripts
```python
# first make a "stubby" meds, holding all the inputs for the MEDSMaker
# this is run first because it needs network and db access
desmeds-make-stubby-meds medsconf coadd_run band

# now make the full meds, which does not require db access
desmeds-make-meds medsconf coadd_run band
```

## installation
```
python setup.py install
python setup.py install --prefix=/some/path
```

## requirements

* meds (version >= 0.9.0)
* desdb (version >= 0.9.0)
* fitsio (use git master for now)
* esutil (version >= 0.5.3)
