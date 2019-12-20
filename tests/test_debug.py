import pytest
import numpy as np
import datetime
import lemsim.core as lcore
import lemsim.prosumer as lpro
import lemsim.broker as lbro


def test_prosumer_wrong_commitment():


    T = 48
    p1 = np.ones(T) * 12.0
    p1[: T // 2] = 16.0
    p2 = np.ones(T) * 14.0
    ps = np.ones(T) * 10.0

    b_max = 14
    b_min = 0
    eff_c = 1
    eff_d = 1
    d_max = 3
    d_min = -3

    load = np.array([ 0.615     ,  0.144     ,  0.049     ,  0.049     ,  0.111     ,
            0.053     ,  0.064     ,  0.086     ,  0.079     ,  0.048     ,
            0.066     ,  0.093     ,  0.069     ,  0.05      ,  0.206     ,
           -0.39525724, -1.08462362, -1.08087823, -1.53270993, -1.17240596,
           -1.55071192, -1.84035319, -1.83289682, -0.86718152, -2.253281  ,
           -1.91336425, -2.13403477, -0.79818386, -1.2204372 , -1.69690974,
           -0.446     , -0.409     , -0.302     , -0.114     , -0.08      ,
            0.083     ,  0.17      ,  0.363     ,  0.829     ,  0.198     ,
            0.207     ,  0.229     ,  0.284     ,  0.26      ,  0.234     ,
            0.098     ,  0.076     ,  0.426     ])

    pro_1 = lpro.Prosumer(0, b_max, b_min, eff_c, eff_d, d_max, d_min, p1, ps, load)
 
    ps_ = pro_1.price_sell.copy()
    pb_ = pro_1.price_buy.copy()
    ps_[15:30] *= 1.1
    pb_[15:30] *= 0.9

    pro_1.update_expected_price(pb_, buying=True)
    pro_1.update_expected_price(ps_, buying=False)

    #print(pro_1.expected_price_buy, pro_1.expected_price_sell)
    for t in range(T):
        bid = pro_1.get_bid(bid_type='long')
        if t == 15:
            pro_1.add_commitment(t, -0.3953)
        pro_1.take_action()
        pro_1.move_forward()

