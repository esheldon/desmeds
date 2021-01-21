import os
import glob
from distutils.core import setup

scripts=[
    'desmeds-make-batch',
    'desmeds-make-batch-set',
    'desmeds-make-stubby-meds',
    'desmeds-make-meds-desdm',
    'desmeds-make-meds',
    'desmeds-coadd',

    'desmeds-rsync-meds-srcs',
    'desmeds-prep-tile',
    'desmeds-make-piff-map',
    'desmeds-plot-piff-examples',
    'desmeds-make-piff-blacklist',
    'desmeds-plot-blacklist',
]

scripts=[os.path.join('bin',s) for s in scripts]

setup(name="desmeds",
      version="0.9.11",
      description="DES specific MEDS code",
      license = "GPL",
      author="Erin Scott Sheldon",
      author_email="erin.sheldon@gmail.com",
      scripts=scripts,
      packages=['desmeds'])
