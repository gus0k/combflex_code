import sys
import numpy as np
import pandas as pd
import datetime
import lemsim.prosumer as lpro
import time
import lemsim.broker as lbro
from lemsim.central_planner import solve_all
from lemsim.read_data import get_data
import lemsim.core as lcore 
from itertools import product

def cost_given_prices(load, pb, ps):
    cost = 0
    for l, b, s in zip(load, pb, ps):
        cost += l * b if l >= 0 else l * s
    return cost

def simulation_run(nick, settings, N, b_min, b_max, eff_c,
                   eff_d, d_max, d_min, seed, PRICES_BUY, PRICES_SELL, T, PATHTODATA, DATE, DAYS, savepath):
    
    """
    
    Parameters
    -----------
    
    settings: dict
        `market_type`: which kind of auction to run ('muda', 'huang', 'p2p', 'combflex')
        `pre_trade`: whether to pre-trade or trade periodicaly ('True', 'False')
        `bid_type`: type of bid to use (`short`, `long`, `flex`)
        `signaling`: type of signaling (`none`, `ismarket`, `clearing price`)
    
    """
    
    start = time.time()
    r = np.random.RandomState(seed)
    r2 = np.random.RandomState(seed + 1)

    DATA = get_data(DATE, r2, N, N // 2, PATHTODATA)

    data = next(DATA)
    data = data[:T, :]

    prosumers = []
    for n in range(N // 4):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[1], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)
    for n in range(N // 4, N // 2):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[0], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)
    for n in range(N // 2, (3 * N) // 4):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[0], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)
    for n in range( (3 * N) // 4, N):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[1], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)

    brokers = [lbro.ProsumerBroker(pro) for pro in prosumers]

    
    sim = lcore.MainSim(brokers, r, settings['bid_type'], settings['pre_trade'],
                        settings['signaling'], settings['market_type'], nickname=nick, seed=seed)
    
    a = settings.get('combflex_alpha', 0)
    b = settings.get('combflex_beta', 1)
    for D in range(DAYS):
        sim.simulate_day(alpha=a, beta=b)
        data = next(DATA)
        packed = dict((p.owner_id, {'load': data[:, i].copy()}) for i, p in enumerate(prosumers))
        sim.change_day(packed)

    
    #print(param1, end - start)

    

    cons = [
        b.prosumer.register[0]['net_demand']
        for b in sim.brokers]
    tot_market = np.abs(np.sum(cons,axis=0)).sum()
    
    cost = [
        b.prosumer.register[0]['final_cost']
        for b in sim.brokers]
    tot_cost = np.sum(cost)
    
    max_inc, max_dec = 0, 0
    for b in sim.brokers:
        reg = b.prosumer.register[0]
        nl = reg.get('profile_only_battery')
        pb = reg.get('price_buy')
        ps = reg.get('price_sell')
        cost_battery = cost_given_prices(nl, pb, ps)
        cost_market = reg.get('final_cost')
        rel_change = round((cost_market - cost_battery) / np.abs(cost_battery) * 100, 4)
        if rel_change > max_inc:
            max_inc = rel_change
        elif rel_change < max_dec:
            max_dec = rel_change

    metric_results = {'auto_cons_market': tot_market, 'social_cost': tot_cost,
                     'maximum_increase_costs': max_inc, 'minimum_decrease_costs': max_dec}
    sim.metric_results = metric_results
    
    filename = savepath + nick + DATE
    sim.save(filename)
    end = time.time()
    
    print(nick, end - start)
    
    return sim


def global_metrics(N, b_min, b_max, eff_c,
                   eff_d, d_max, d_min, seed, PRICES_BUY, PRICES_SELL, T, PATHTODATA, DATE, DAYS, savepath):
    
    start = time.time()
    r = np.random.RandomState(seed)
    r2 = np.random.RandomState(seed + 1)

    DATA = get_data(DATE, r2, N, N // 2, PATHTODATA)

    data = next(DATA)
    data = data[:T, :]

    prosumers = []
    for n in range(N // 4):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[1], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)
    for n in range(N // 4, N // 2):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[0], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)
    for n in range(N // 2, (3 * N) // 4):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[0], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)
    for n in range( (3 * N) // 4, N):
        pro_1 = lpro.Prosumer(n, b_max, b_min, eff_c, eff_d, d_max, d_min, PRICES_BUY[1], PRICES_SELL[0], data[:, n], seed)
        prosumers.append(pro_1)

    brokers = [lbro.ProsumerBroker(pro) for pro in prosumers]

    
    prof_bat = [p.get_profile_only_battery(0) for p in prosumers]
    loads_ = [p.load for p in prosumers]
    pbs_ = [p.price_buy for p in prosumers]
    pss_ = [p.price_sell for p in prosumers]

    total_cost_default = 0
    for l, p, s in zip(loads_, pbs_, pss_):
        c_ = cost_given_prices(l, p, s)
        total_cost_default += c_
    
    total_cost_battery = 0
    for l, p, s in zip(prof_bat, pbs_, pss_):
        c_ = cost_given_prices(l, p, s)
        total_cost_battery += c_
    
    ## Best optimal case, no constraints
    
    status, obj, sol, om = solve_all(
            loads_, pbs_, pss_, [None] * len(loads_) , b_min, b_max, b_min, eff_c, eff_d, d_max, d_min
        )

    opt_loads_no_constraints = []
    for i, s in enumerate(sol):
        net = (s + loads_[i]).copy()
        opt_loads_no_constraints.append(net)
    opt_loads_no_constraints = np.array(opt_loads_no_constraints)    
    
    auto_cons_optimal_no_constraints = np.abs(np.sum(opt_loads_no_constraints,axis=0)).sum()
    #print('Optimal auto cons', auto_cons_optimal_no_constraints)
    
    ## Best case, at least good as alone
    
    costs_alone = []
    for s, pb_, ps_ in zip(prof_bat, pbs_, pss_):
        cost = cost_given_prices(s, pb_, ps_)
        costs_alone.append(cost)
    
    status, obj, sol, om = solve_all(
            loads_, pbs_, pss_, costs_alone , b_min, b_max, b_min, eff_c, eff_d, d_max, d_min
        )

    opt_loads_cost_constraints = []
    for i, s in enumerate(sol):
        net = (s + loads_[i]).copy()
        opt_loads_cost_constraints.append(net)
    opt_loads_cost_constraints = np.array(opt_loads_cost_constraints)    
    
    auto_cons_optimal_cost_constraints = np.abs(np.sum(opt_loads_cost_constraints,axis=0)).sum()
    #print('Optimal auto cons with cost constraints', auto_cons_optimal_cost_constraints)

    auto_cons_batt = np.vstack(prof_bat).sum(axis=0)
    auto_cons_batt = np.abs(auto_cons_batt).sum()
    
    end = time.time()
    print('Global metrics elapsed time:', end - start)
    
    results = {'optimal_auto_cons': auto_cons_optimal_no_constraints,
               'optimal_auto_cons_guarantee_battery': auto_cons_optimal_cost_constraints,
               'auto_cons_battery': auto_cons_batt,
               'social_cost_default': total_cost_default,
               'total_cost_battery': total_cost_battery
              }
    
    return results
