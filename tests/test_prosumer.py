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
    d_max = 1
    d_min = -1
    load = np.array([0, 1, 1])
    pb = np.array([2, 10, 11])
    ps = np.array([1, 1, 1])

    data = (owner_id, b_max, b_min, eff_c, eff_d, d_max,
           d_min, pb, ps, load)
    return data

@pytest.fixture
def new_prosumer_2():
    """
    Instanciates a new battery with some
    characteristics
    """

    owner_id = 1
    b_max = 4
    b_min = 0
    eff_c = 1
    eff_d = 1
    d_max = 4
    d_min = -4
    load = np.array([1, 1, 1, 1])
    pb = np.array([2, 4, 1, 3])
    ps = np.array([0, 0, 0, 0])

    data = (owner_id, b_max, b_min, eff_c, eff_d, d_max,
           d_min, pb, ps, load)
    return data


def test_basic(new_prosumer_1):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_1)
    bro = lbro.ProsumerBroker(pro)

    profile = np.array([1, 1, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Time-slot 1, charging
    b1 = pro.get_bid()
    bs1 = bro.market_bid()
    assert np.allclose([[1, 2, True]], b1)
    assert np.allclose([(1, 2, 0, True, 0)], bs1)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 2, consuming from the grid
    pro.move_forward()
    b2 = pro.get_bid()
    bs2 = bro.market_bid()
    assert np.allclose([[1, 10, True]], b2)
    assert np.allclose([(1, 10, 0, True, 1)], bs2)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 3, discharging
    pro.move_forward()
    b3 = pro.get_bid()
    bs3 = bro.market_bid()
    assert np.allclose([], b3)
    assert np.allclose([], bs3)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 12)


def test_1_commitment(new_prosumer_1):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_1)

    profile = np.array([1, 1, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Time-slot 1, charging
    b1 = pro.get_bid()
    assert np.allclose([[1, 2, True]], b1)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 2, consuming from the grid
    pro.move_forward()
    b2 = pro.get_bid()
    assert np.allclose([[1, 10, True]], b2)
    pro.add_commitment(1, 0.5)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 3, discharging
    pro.move_forward()
    b3 = pro.get_bid()
    assert np.allclose([], b3)
    pro.add_commitment(2, 0.5)
    pro.take_action()
    assert np.allclose(pro.charge, 0.499)

    assert np.allclose(pro.get_final_cost(0), 17.489)



def test_2_commitment(new_prosumer_1):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_1)

    profile = np.array([1, 1, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Add commitments before taking actions
    pro.add_commitment(1, 0.5)
    pro.add_commitment(2, 0.5)

    # Time-slot 1, charging
    b1 = pro.get_bid()
    assert np.allclose([[1, 2, True]], b1)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 2, consuming from the grid
    pro.move_forward()
    b2 = pro.get_bid()
    assert np.allclose([[0.501, 10, True]], b2)
    pro.take_action()
    assert np.allclose(pro.charge, 0.501)

    # Time-slot 3, discharging
    pro.move_forward()
    b3 = pro.get_bid()
    assert np.allclose([[0.499, 11, True]], b3)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 12.499)


def test_long_bid_basic(new_prosumer_2):
    """

    """
    pro = lpro.Prosumer(*new_prosumer_2)
    bro = lbro.ProsumerBroker(pro)

    profile = np.array([2, 0, 2, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Time-slot 1, charging
    b1 = pro.get_bid(bid_type='long')
    bs1 = bro.market_bid()
    assert np.allclose([[2, 2, True], [4, 1, True]], b1)
    assert np.allclose([(2, 2, 1, True, 0), (2, 1, 1, True, 0)], bs1)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 2, discharging
    pro.move_forward()
    b2 = pro.get_bid(bid_type = 'long')
    bs2 = bro.market_bid()
    print(b2)
    assert np.allclose([[2, 1, True]], b2)
    assert np.allclose([(2, 1, 1, True, 1)], bs2)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 3, charging
    pro.move_forward()
    b3 = pro.get_bid(bid_type = 'long')
    bs3 = bro.market_bid()
    assert np.allclose([2, 1, True], b3)
    assert np.allclose([(2, 1, 1, True, 2)], bs3)
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 4, discharging
    pro.move_forward()
    b4 = pro.get_bid(bid_type = 'long')
    bs4 = bro.market_bid()
    assert np.allclose([], b4)
    assert np.allclose([], bs4)
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 6)


def test_changing_days(new_prosumer_2):
    """
    The data used is sampled every 15 minutes

    """
    pro = lpro.Prosumer(*new_prosumer_2)

    profile = np.array([2, 0, 2, 0])
    assert np.allclose(pro.get_profile_only_battery(0), profile)
    assert np.allclose(pro.charge, 0)

    # Time-slot 1, charging
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 2, discharging
    pro.move_forward()
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 3, charging
    pro.move_forward()
    pro.take_action()
    assert np.allclose(pro.charge, 1)

    # Time-slot 4, discharging
    pro.move_forward()
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 6)

    ##
    ### Data for the new day
    ##
    pb = np.array([5, 2, 1, 5])
    ps = np.array([1, 2, 1, 1])
    load = np.array([1, 1, 1, 2])

    pro.finish_day()
    pro.new_day(pb, ps, load)

    new_profile = np.array([1, 1, 3, 0])
    assert np.allclose(pro.get_profile_only_battery(1), new_profile)
    assert np.allclose(pro.charge, 0)


    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 2, discharging
    pro.move_forward()
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    # Time-slot 3, charging
    pro.move_forward()
    pro.take_action()
    assert np.allclose(pro.charge, 2)

    # Time-slot 4, discharging
    pro.move_forward()
    pro.take_action()
    assert np.allclose(pro.charge, 0)

    assert np.allclose(pro.get_final_cost(0), 6)
    assert np.allclose(pro.get_final_cost(1), 10)
