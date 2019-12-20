import pytest
import numpy as np
from lemsim.core import MainSim
import lemsim.prosumer as lpro
import lemsim.broker as lbro


def test_simple_simulation():
    ### Data definition
    T = 5
    r = np.random.RandomState(420)
    p1 = np.ones(T)
    p2 = np.ones(T) * 2.0
    p3 = np.ones(T) * 3.0

    l1 = np.ones(T)
    l2 = np.zeros(T)
    l2[2]= -1

    b_max = 4
    b_min = 0
    eff_c = 0.95
    eff_d = 0.95
    d_max = 4
    d_min = -4

    N = 3
    prosumers = []
    for n in range(N):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, p2, p1, l1)
        pro_2 = lpro.Prosumer(n + N, b_max, b_min, eff_c, eff_d, d_max, d_min, p2, p1, l2)
        pro_3 = lpro.Prosumer(n + 2 * N, b_max, b_min, eff_c, eff_d, d_max, d_min, p3, p1, l1)
        prosumers.extend([pro_1, pro_2, pro_3])


    pro_4 = lpro.Prosumer(10, b_max, b_min, eff_c, eff_d, d_max, d_min, p2, p1, l2)
    pro_5 = lpro.Prosumer(11, b_max, b_min, eff_c, eff_d, d_max, d_min, p2, p1, l2)
    pro_6 = lpro.Prosumer(12, b_max, b_min, eff_c, eff_d, d_max, d_min, p2, p1, l2)
    pro_7 = lpro.Prosumer(13, b_max, b_min, eff_c, eff_d, d_max, d_min, p2, p1, l2)
    prosumers.extend([pro_4, pro_5, pro_6, pro_7])
    brokers = [lbro.ProsumerBroker(pro) for pro in prosumers]

    ### End definitions


    ### Core simulation start

    sim = MainSim(brokers, randomstate=r, sun_times=(2, 3))
    sim.simulate_day()

    for i, r in enumerate(sim.results[0]):
        if i != 2:
            assert sorted(r.results) == [(0, 0, 0), (1, 0, 0), (2, 0, 0), (6, 0, 0), (7, 0, 0), (8, 0, 0)]

        else:
            assert sorted(r.results) == [(0, 1.0, 1.4577),
                                         (1, 1.0, 1.4901499999999999),
                                         (2, 1.0, 1.4901499999999999),
                                         (3, -1.0, -1.4901499999999999),
                                         (4, -1.0, -1.4901499999999999),
                                         (5, -1.0, -1.4901499999999999),
                                         (6, 1.0, 1.4901499999999999),
                                         (7, 1.0, 1.4577),
                                         (8, 1.0, 1.4901499999999999),
                                         (10, 0, 0),
                                         (11, -1.0, -1.89),
                                         (12, -1.0, -1.89),
                                         (13, -1.0, -1.4901499999999999)]

    new_data = {10: {'load': np.array([0, -1, -1, 0, 0])}}
    sim.change_day(new_data)

    sim.simulate_day()

    for i, r in enumerate(sim.results[1]):
        if i in [0, 3]:
            assert sorted(r.results) == [(0, 0, 0), (1, 0, 0), (2, 0, 0), (6, 0, 0), (7, 0, 0), (8, 0, 0)]
        elif i == 4:
            assert sorted(r.results) == [(0, 0, 0), (1, 0, 0), (2, 0, 0), (6, 0, 0), (8, 0, 0)]
        elif i == 1:
            assert sorted(r.results) == [(0, 0, 0), (1, 0, 0), (2, 0, 0), (6, 0, 0), (7, 0, 0), (8, 0, 0), (10, 0, 0)]
        else:
            assert sorted(r.results) == [(0, 0, 0),
                                         (1, 0, 0),
                                         (2, 0, 0),
                                         (3, -1.0, -2.7),
                                         (4, 0, 0),
                                         (5, -1.0, -2.7),
                                         (6, 0, 0),
                                         (7, 3.2161, 8.87999176),
                                         (8, 0.7839, 2.1165300000000005),
                                         (10, 0, 0),
                                         (11, -1.0, -2.7),
                                         (12, 0, 0),
                                         (13, -1.0, -2.7)]

