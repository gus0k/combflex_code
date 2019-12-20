import sys
import pdb
import cplex
import random
import pandas as pd
import numpy as np
import docplex.mp.model as cpx
from cplex.exceptions import CplexSolverError

def solve_bat(
    demand,
    price_buy,
    price_sell,
    B_0,
    B_max,
    B_min,
    e_c,
    e_d,
    d_max,
    d_min,
    commitments={},
    reg=False,
    eps=1e-3,
    seed=420
):

#    print(price_buy, price_sell)
    assert (price_buy >= price_sell).all()
    #commitment = None
    #print(commitment)
    opt_model = cpx.Model(name="Battery")
    opt_model.parameters.randomseed.set(seed)
    T = len(demand)

    sum_lower_bound = B_min - B_0
    sum_upper_bound = B_max - B_0
    set_I = range(0, T)
    p_b = {i:price_buy[i] for i in set_I}
    p_s = {i:price_sell[i] for i in set_I}
    z = {i:demand[i] for i in set_I}
    #print(demand, d_max)
    max_t = (demand.max() + d_max) * price_buy.max() * 1.5 / e_c
    min_t = (demand.min() + d_min) * price_sell.max() * 1.5 / e_d

    x_c  = {i: opt_model.continuous_var(lb=0, ub=d_max, name="xc{0}".format(i)) for i in set_I}
    x_d  = {i: opt_model.continuous_var(lb=0, ub=-d_min, name="xd{0}".format(i)) for i in set_I}
    t_s  = {i: opt_model.continuous_var(lb=min_t, ub=max_t, name="t{0}".format(i)) for i in set_I}

    cons_pb = {i : 
        opt_model.add_constraint(
        ct=p_b[i] * (x_c[i] / e_c - x_d[i] * e_d + z[i]) <= t_s[i],
        ctname="constraintpb{0}".format(i))
        for i in set_I
    }

    cons_ps = {i : 
        opt_model.add_constraint(
        ct=p_s[i] * (x_c[i] / e_c - x_d[i] * e_d + z[i]) <= t_s[i],
        ctname="constraintps{0}".format(i))
        for i in set_I
    }

    cons_sum_gt = {i : 
        opt_model.add_constraint(
        ct=opt_model.sum(x_c[j] - x_d[j] for j in range(0, i + 1)) >= sum_lower_bound,
        ctname="constraintsumgt{0}".format(i))
        for i in set_I
    }

    cons_sum_lt = {i : 
        opt_model.add_constraint(
        ct=opt_model.sum(x_c[j] - x_d[j] for j in range(0, i + 1)) <= sum_upper_bound,
        ctname="constraintsumgt{0}".format(i))
        for i in set_I
    }

    #i = 0
    #print('-' * 50)
    #print(sum([1 for k,v in commitments.items() if v is not None]))
    for k, v in commitments.items():
        if v is not None:
            #print(v)
            if v > 0:
                cons = max((v - eps), 0)
                #print(k, v, v - eps, cons)
                opt_model.add_constraint(ct=(x_c[k] / e_c - x_d[k] * e_d + z[k]) >= cons, ctname=f"commitment{k}")
            else:
                cons = min(0, v + eps)
                #print(k, v, cons)
                opt_model.add_constraint(ct=(x_c[k] / e_c - x_d[k] * e_d + z[k]) <= cons, ctname=f"commitment{k}")

    reg_coef = np.arange(T) / 1000


    objective = opt_model.sum(t_s[i] for i in set_I)
    if reg:
        reg_c = opt_model.sumsq(reg_coef[i] / x_c[i] for i in set_I)
        reg_d = opt_model.sumsq(reg_coef[i] * x_d[i] for i in set_I)
        objective = opt_model.sum([objective, reg_c, reg_d])
    opt_model.minimize(objective)

    try:
        opt_model.solve()

        sol = np.array([x_c[k].solution_value - x_d[k].solution_value for k in set_I])
        value = opt_model.objective_value
        status = opt_model.solution._solve_details.status
    
    except Exception as e:
        print('Cplex error')
        print(price_buy, price_sell)
        print(demand, B_0, commitments, min_t, max_t)
        #pdb.set_trace()
        raise ValueError
    #print(opt_model.solve_details)
    #print(opt_model.solution._solve_details)


    return status, value, sol, opt_model
    #return opt_model, x_c, x_d, t_s

if __name__ == '__main__':
    import scipy.io as sio
    from glob import glob

    B_0 = 0
    B_max = 25
    B_min = 0
    e_ch = 0.95
    e_dis = 0.95
    del_max = 100
    del_min = -100
    h = 0.25

    price_sell = np.ones(96) * 10.0
    price_buy = np.ones(96) * 12.0
    price_buy[28:92] = 15.0
    print(price_buy)
    flist = glob('/home/guso/app/data/*.mat')
    for f in sorted(flist):
        demand = sio.loadmat(f)['forecasts'][:, 0]
        params = (
            demand,
            price_buy,
            price_sell,
            B_0,
            B_max,
            B_min,
            e_ch,
            e_dis,
            del_max,
            del_min,
            h
        )
        print('-' * 100)
        print(f)
        v_1, st_1, sol_1 = solve_bat(*params)
        #sol_1 = np.array([c[k].solution_value - d[k].solution_value for k in c])
        #print(sol_1)
        #print(m.objective_value)
        #print(m.get_solve_status())

        v_2, st_2, sol_2 = solve_bat(*params, reg=True)
        #sol_2 = np.array([c[k].solution_value - d[k].solution_value for k in c])
        #print(sol_2)
        #print(m.objective_value)
        #print(m.get_solve_status())
        print(st_1, st_2, 'Distance', np.linalg.norm(sol_1 - sol_2))
        #print(m.solve_details)
        #print([x.solution_value for k,x in c.items()])
        #print([x.solution_value for k,x in d.items()])
        #print([x.solution_value for k,x in t.items()])
