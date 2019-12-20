import pytest

import numpy as np
import pandas as pd

DATA = 'tests/data/pre_tested_data.csv'
RESULTS = 'tests/data/results.csv'

@pytest.fixture
def new_battery():
    """
    Instanciates a new battery with some
    characteristics
    """
    import lemsim.batterycontroller as lbat

    owner_id = 'Owner1'
    b_max = 25
    b_min = 0
    eff_c = 0.95
    eff_d = 0.95
    d_max = 100
    d_min = -100
    bat = lbat.BatteryController(owner_id, b_max, b_min, eff_c, eff_d, d_max, d_min)

    return bat


@pytest.mark.skip(reason='Takes to long to test everytime')
def test_update(new_battery):
    """
    Tests that the battery controller provides the correct output
    for data already tested using several methods

    The data used is sampled every 15 minutes

    """
    bat = new_battery
    ps = np.ones(96) * 10.0
    pb = np.ones(96) * 12.0
    pb[28:92] = 15.0

    data = pd.read_csv(DATA, header=None).values * 0.25 # data is in power
    results = pd.read_csv(RESULTS, header=None).values[0]
    for i in range(data.shape[1]):
        load = data[:, i].copy()
        bat.reset(0)
        res = bat.find_optimal_step(load, pb, ps, commitment={}, reg=False)
        assert np.allclose(res[1], results[i])
