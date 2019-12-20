import pytest

import numpy as np
import pandas as pd
import lemsim.prosumer as lpro
import lemsim.broker as lbro


@pytest.fixture
def new_prosumer_1():
    """
    Instanciates a new battery with some
    characteristics
    """

    owner_id = 0
    b_max = 3
    b_min = 0
    eff_c = 1
    eff_d = 1
    d_max = 2
    d_min = -2
    load = np.array([1, -2, 1, 1])
    pb = np.array([2, 2, 4, 2])
    ps = np.array([1, 1, 1, 1])

    data = (owner_id, b_max, b_min, eff_c, eff_d, d_max,
           d_min, pb, ps, load)
    return data

def test_basic(new_prosumer_1):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_1)

    profile = np.array([1, 0, 0, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Time-slot 1, charging
    b1 = pro.get_bid()
    assert np.allclose([[1, 2, True]], b1)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 2, consuming from the grid
    pro.move_forward()
    b2 = pro.get_bid()
    assert np.allclose([], b2)
    pro.take_action()
    assert np.allclose(pro.charge, 2)

    # Time-slot 3, discharging
    pro.move_forward()
    b3 = pro.get_bid()
    assert np.allclose([], b3)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 3, discharging
    pro.move_forward()
    b4 = pro.get_bid()
    assert np.allclose([], b4)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 2)

def test_long_basic(new_prosumer_1):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_1)
    bro = lbro.ProsumerBroker(pro)

    profile = np.array([1, 0, 0, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Time-slot 1, charging
    b1 = pro.get_bid(bid_type = 'long')
    bs1 = bro.market_bid()
    assert np.allclose([[1, 2, True]], b1)
    assert np.allclose([(1, 2, 0, True, 0)], bs1)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 2, consuming from the grid
    pro.move_forward()
    b2 = pro.get_bid(bid_type = 'long')
    bs2 = bro.market_bid()
    assert np.allclose([[1, 2, False], [2, 4, False]], b2)
    assert np.allclose([(1, 2, 0, False, 1), (1, 4, 0, False, 1)], bs2)
    pro.take_action()
    assert np.allclose(pro.charge, 2)

    # Time-slot 3, discharging
    pro.move_forward()
    b3 = pro.get_bid(bid_type = 'long')
    bs3 = bro.market_bid()
    assert np.allclose([], b3)
    assert np.allclose([], bs3)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 3, discharging
    pro.move_forward()
    b4 = pro.get_bid(bid_type = 'long')
    bs4 = bro.market_bid()
    assert np.allclose([], b4)
    assert np.allclose([], bs4)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 2)

def test_long_commitment(new_prosumer_1):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_1)
    bro = lbro.ProsumerBroker(pro)

    profile = np.array([1, 0, 0, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    pro.add_commitment(2, 0.5)

    # Time-slot 1, charging
    b1 = pro.get_bid(bid_type = 'long')
    bs1 = bro.market_bid()
    assert np.allclose([[1, 2, True]], b1)
    assert np.allclose([(1, 2, 0, True, 0)], bs1)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 2, consuming from the grid
    pro.move_forward()
    b2 = pro.get_bid(bid_type = 'long')
    bs2 = bro.market_bid()
    assert np.allclose([[0.499, 1, False], [1.499, 2, False], [2, 4, False]], b2)
    assert np.allclose([(0.499, 1, 0, False, 1), (1, 2, 0, False, 1), (0.501, 4, 0, False, 1)], bs2)
    pro.take_action()
    assert np.allclose(pro.charge, 1.501)

    # Time-slot 3, discharging
    pro.move_forward()
    b3 = pro.get_bid(bid_type = 'long')
    bs3 = bro.market_bid()
    assert np.allclose([[0.499, 4, True], [0.499, 2, True]], b3)
    assert np.allclose([(0.499, 4, 0, True, 2)], bs3)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 3, discharging
    pro.move_forward()
    b4 = pro.get_bid(bid_type = 'long')
    bs4 = bro.market_bid()
    assert np.allclose([], b4)
    assert np.allclose([], bs4)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 3.497)



