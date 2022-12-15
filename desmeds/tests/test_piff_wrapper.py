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
        color_name="GI_COLOR",
        ccdnum=se_image_data["source_info"]["ccdnum"],
        stamp_size=stamp_size,
    )
    rng = np.random.RandomState(seed=10)

    def _test(row, col):
        psf_im = psf.piff_obj.draw(
            x=col,
            y=row,
            center=None,
            stamp_size=psf['stamp_size'],
            GI_COLOR=0.2,
            chipnum=psf.ccdnum,
        )

        cen = psf.get_center(row, col)
        print(
            "row:", row, cen[0], row - psf_im.bounds.ymin,
            flush=True,
        )
        print(
            "col:", col, cen[1], col - psf_im.bounds.xmin,
            flush=True,
        )
        assert np.allclose(cen[0], row - psf_im.bounds.ymin)
        assert np.allclose(cen[1], col - psf_im.bounds.xmin)

    for row in [10.0, 50.0, 45.5, 500.5]:
        for col in [10.0, 50.0, 45.5, 500.5]:
            _test(row, col)

    for row in rng.uniform(low=56.0, high=1279.0, size=10):
        for col in rng.uniform(low=56.0, high=1279.0, size=10):
            _test(row, col)