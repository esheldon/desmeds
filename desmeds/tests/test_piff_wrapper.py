import os
import numpy as np
import pytest

from ..desdm_maker import PIFFWrapper


@pytest.mark.skipif(
    os.environ.get('TEST_DESDATA', None) is None,
    reason=(
        'SEImageSlice can only be tested if '
        'test data is at TEST_DESDATA'))
@pytest.mark.parametrize("stamp_size", [24, 25])
def test_piff_wrapper_cen(se_image_data, stamp_size):
    psf = PIFFWrapper(
        se_image_data["source_info"]["piff_path"],
        color_name="IZ_COLOR",
        ccdnum=se_image_data["source_info"]["ccdnum"],
        stamp_size=stamp_size,
    )
    rng = np.random.RandomState(seed=10)

    for row in rng.uniform(low=56.0, high=1279.0, size=10):
        for col in rng.uniform(low=56.0, high=1279.0, size=10):
            psf_im = psf.piff_obj.draw(
                x=col,
                y=row,
                center=None,
                stamp_size=psf['stamp_size'],
                IZ_COLOR=0.2,
                chipnum=psf["chipnum"],
            )

            cen = psf.get_center(row, col)
            assert np.allclose(cen[0], row - psf_im.bounds.ymin)
            assert np.allclose(cen[1], col - psf_im.bounds.xmin)
