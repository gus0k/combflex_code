import pytest

import numpy as np
import pandas as pd
import lemsim.prosumer as lpro
import lemsim.broker as lbro
import lemsim.market_interface as lmar

@pytest.fixture
def generate_bids():

    B = np.array([
        [1   , 1 , 0 , True  , 0] ,
        [1   , 2 , 1 , True  , 0] ,
        [1.5 , 3 , 2 , True  , 0] ,
        [1   , 2 , 3 , False , 0] ,
        [0.5 , 4 , 4 , False , 0] ,
        [1   , 1 , 5 , True  , 0] , # r=1, turns into 1.0061
        [0.7 , 1.0061 , 7 , False  , 0] ,
        [3.1 , 1.0061 , 2 , True  , 0] , #r=1, turns into 0.9226
        [5.1 , 4 , 0 , False  , 0] , #r=1, turns into 4.0932

    ])

    return B

def test_market_up(generate_bids):

    r = np.random.RandomState(1)
    mar = lmar.MarketInterface(r=r)
    data = generate_bids

    callback = lambda: True

    mar.accept_bid(data[0, :], callback)
    mar.accept_bid(data[1, :], callback)
    mar.accept_bid(data[2, :], callback)
    mar.accept_bid(data[3, :], callback)
    mar.accept_bid(data[4, :], callback)
    mar.accept_bid(data[5, :], callback)
    mar.accept_bid(data[6, :], callback)
    mar.accept_bid(data[7, :], callback)
    mar.accept_bid(data[8, :], callback)

    bids = mar.bm.get_df().values.astype(float)

    new_bids = data.copy()
    new_bids[5, 1] = 1.0061
    new_bids[7, 1] = 0.9296
    new_bids[8, 1] = 4.0932
    assert np.allclose(bids[:, :2], new_bids[:, :2])



def test_solve_and_clear(generate_bids):

    r = np.random.RandomState(1)
    mar = lmar.MarketInterface(r=r)
    data = generate_bids

    callback = lambda x, y, z: True

    N = 20
    for i in range(N):
        mar.accept_bid((1, 2, i, True, 0), callback)
        mar.accept_bid((0.5, 3, i, True, 0), callback)
    for i in range(N):
        mar.accept_bid((1, 1, i + 20, False, 0), callback)
        mar.accept_bid((1.5, 2, i + 20, False, 0), callback)


    mar.clear('muda', r=r)
    res = mar.results

    ## Check if the bought quantity is equal to the sold quantity
    pos = 0
    neg = 0
    for k, q, p in res:
        if q < 0:
            neg += q
        else:
            pos += q
    assert np.allclose(pos, -neg)

    ## Check if for each user, it was Incentive compatible to participate in the market
    for k, q, p in res:
        if k < 20: # If buying, did not pay more per unit than desired
            if q < 0.5:
                assert p < 3  * q
            else:
                assert p < 2.33 * q # weighted average of the price selling all
        else:
            if q > -1: # If sold less than 1 unit
                assert p < 1 * q
            else:
                assert p < 1.666 * q # weighted average of the price selling all



