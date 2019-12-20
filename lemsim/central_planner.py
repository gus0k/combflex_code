import docplex.mp.model as cpx
import numpy as np


def solve_all(
    demands,
    prices_buy,
    prices_sell,
    max_costs,
    B_0,
    B_max,
    B_min,
    e_c,
    e_d,
    d_max,
    d_min,
    seed = 420
):

    opt_model = cpx.Model(name="Battery")
    opt_model.parameters.randomseed.set(seed)
    T = len(demands[0])
    N = len(demands)

    sum_lower_bound = B_min - B_0
    sum_upper_bound = B_max - B_0
    set_I = range(0, T)

    xcs = []
    xds = []
    tss = []
    max_ts = 0
    min_ts = 0
    for n in range(N):
        p_b = {i: prices_buy[n][i] for i in set_I}
        p_s = {i: prices_sell[n][i] for i in set_I}
        z = {i: demands[n][i] for i in set_I}
        max_t = (demands[n].max() + d_max) * prices_buy[n].max() / e_c
        max_ts += max_t
        min_t = (demands[n].min() + d_min) * prices_sell[n].max() / e_d
        min_ts += min_t

        x_c = {
            i: opt_model.continuous_var(lb=0, ub=d_max, name="xc{0}_{1}".format(i, n))
            for i in set_I
        }
        xcs.append(x_c)
        x_d = {
            i: opt_model.continuous_var(lb=0, ub=-d_min, name="xd{0}_{1}".format(i, n))
            for i in set_I
        }
        xds.append(x_d)
        t_s = {
            i: opt_model.continuous_var(
                lb=min_t, ub=max_t, name="t{0}_{1}".format(i, n)
            )
            for i in set_I
        }
        tss.append(t_s)

        {
            i: opt_model.add_constraint(
                ct=p_b[i] * (x_c[i] / e_c - x_d[i] * e_d + z[i]) <= t_s[i],
                ctname="constraintpb{0}_{1}".format(i, n),
            )
            for i in set_I
        }

        {
            i: opt_model.add_constraint(
                ct=p_s[i] * (x_c[i] / e_c - x_d[i] * e_d + z[i]) <= t_s[i],
                ctname="constraintps{0}_{1}".format(i, n),
            )
            for i in set_I
        }

        {
            i: opt_model.add_constraint(
                ct=opt_model.sum(x_c[j] - x_d[j] for j in range(0, i + 1))
                >= sum_lower_bound,
                ctname="constraintsumgt{0}_{1}".format(i, n),
            )
            for i in set_I
        }

        {
            i: opt_model.add_constraint(
                ct=opt_model.sum(x_c[j] - x_d[j] for j in range(0, i + 1))
                <= sum_upper_bound,
                ctname="constraintsumgt{0}_{1}".format(i, n),
            )
            for i in set_I
        }

        if max_costs[n] is not None:
            opt_model.add_constraint(
                ct=opt_model.sum(t_s[j] for j in range(T)) <= max_costs[n],
                ctname="require_minimum_cost_{0}".format(n),
            )

    tcps = []
    tcns = []
    for i in set_I:
        tcp = opt_model.continuous_var(
            lb=0, ub=max_ts, name="total_cons_pos{0}".format(i)
        )
        tcn = opt_model.continuous_var(
            lb=0, ub=-min_ts, name="total_cons_neg{0}".format(i)
        )
        opt_model.add_constraint(
            ct=opt_model.sum(
                [xcs[n][i] / e_c - xds[n][i] * e_d + demands[n][i] for n in range(N)]
            )
            - tcp
            + tcn
            == 0,
            ctname="aux_variable_tc{0}".format(i),
        )
        tcps.append(tcp)
        tcns.append(tcn)

    objective = opt_model.sum(tcps[i] + tcns[i] for i in set_I)
    opt_model.minimize(objective)

    try:
        opt_model.solve()

        sol_n = []
        for n in range(N):
            sol = np.array(
                [
                    xcs[n][k].solution_value / e_c - xds[n][k].solution_value * e_d
                    for k in set_I
                ]
            )
            sol_n.append(sol.copy())
        value = opt_model.objective_value
        status = opt_model.solution._solve_details.status

    except Exception:
        print("Cplex error")
        raise ValueError

    return status, value, sol_n, opt_model
