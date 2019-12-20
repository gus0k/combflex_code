import sys
import numpy as np
import pandas as pd
import datetime
import lemsim.prosumer as lpro
import time
import lemsim.broker as lbro
from itertools import product
from collections import defaultdict
from lemsim.utils import create_bid
from lemsim.wdp import WinnerDeterminationProblem


def simple_split_mechanism(bids, r=None, alpha=0, beta=1, seed=420):
    
    EPS = 1e-4
    T = 48
    if r is None:
        r = np.random.RandomState(1)
        
    left, right = [], []
    for b in bids:
        if r.rand() < 0.5:
            left.append(b)
        else:
            right.append(b)
    
    bid_sides = [left, right]
    
    wdp_left = WinnerDeterminationProblem(T, alpha, beta, seed=seed)
    wdp_right = WinnerDeterminationProblem(T, alpha, beta, seed=seed)  
    wdp_sides = [wdp_left, wdp_right]
    
    for (b, w) in zip(bid_sides, wdp_sides):
        for b_ in b:
            w.add_bid(b_)
            
    models = []
    for w in wdp_sides:
        m = w.build_problem()
        w.solve()
        models.append(m)
        
    l_left = wdp_left.get_prices()
    l_right = wdp_right.get_prices()
    prices = [l_right, l_left] # Inverted on purpose
    
    for p, w in zip(prices, wdp_sides):
        for t in range(T):
            limit_buy = p[t][0]
            limit_sell = p[t][1]
            
            for var in w.vars_buying[t]:
                unitcost = w.vars_unitcost[var.name]
                if np.allclose(limit_buy, -1): #  kill variable
                    var.upBound = 0
                elif (limit_buy - unitcost > EPS):
                    var.upBound = 0
            for var in w.vars_selling[t]:
                unitcost = w.vars_unitcost[var.name]
                if np.allclose(limit_sell, -1): #  kill variable
                    var.upBound = 0
                elif (unitcost - limit_sell > EPS):
                    var.upBound = 0
     
    a_l, b_l, c_l, (vb_l, vs_l, pay_l), _ = wdp_left.solve()
    a_r, b_r, c_r, (vb_r, vs_r, pay_r), _ = wdp_right.solve()
    
    costs_left = wdp_left.get_costs(*zip(*l_right))
    costs_right = wdp_right.get_costs(*zip(*l_left))
    
    
    vb = {**vb_l, **vb_r}
    vs = {**vs_l, **vs_r}
    costs = {**costs_left, **costs_right}
    

    return wdp_sides, vb, vs, costs



def vcg_mechanism(bids, r=None, alpha=0, beta=1, seed=420):
    
    EPS = 1e-4
    T = 48
    if r is None:
        r = np.random.RandomState(1)

        
    wdp = WinnerDeterminationProblem(T, alpha, beta, seed=seed)
    [wdp.add_bid(bd) for bd in bids]
    wdp.build_problem()
    _, _, _, (vb, vs, _), costs = wdp.solve()
    total_cost = sum(costs.values())
    
    #print(total_cost, costs)
    
    vcg_payments = defaultdict(float)
    
    for bd in bids:
        uid = bd.uid
        #print(uid)
        new_bids = [bd_ for bd_ in bids if bd_.uid != uid]
        wdp_ = WinnerDeterminationProblem(T, alpha, beta, seed=seed)
        [wdp_.add_bid(bd_2) for bd_2 in new_bids]
        wdp_.build_problem()
        _, _, _, (vb_bd, vs_bd, _), costs_bd = wdp_.solve()
        new_total_cost = sum(costs_bd.values())
        payment = total_cost - costs[uid] - new_total_cost
        vcg_payments[uid] = payment
    
    return wdp, vb, vs, vcg_payments
     
    
