import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from batterycontroller import BatteryController
from central_planner import solve_bat


def get_cost(load, price_buy, price_sell):
    cost = 0
    for l, pb, ps in zip(load, price_buy, price_sell):
        cost += l * pb if l > 0 else l * ps
    return cost


def plot_results(df, day):

    df_ = df[df.date == day].copy()

    net_load = df_[df.type == "load"].iloc[:, 4:].values.sum(axis=0)
    net_batt = df_[df.type == "batt"].iloc[:, 4:].values.sum(axis=0)
    net_cng = df_[df.type == "central_gn"].iloc[:, 4:].values.sum(axis=0)
    net_cgl = df_[df.type == "central_gl"].iloc[:, 4:].values.sum(axis=0)
    net_cgb = df_[df.type == "central_gb"].iloc[:, 4:].values.sum(axis=0)
    fig, ax = plt.subplots()
    ax.plot(net_load, label="Net load {0}".format(np.abs(net_load).sum()))
    ax.plot(net_batt, label="Net batt {0}".format(np.abs(net_batt).sum()))
    ax.plot(net_cng, label="Net cng {0}".format(np.abs(net_cng).sum()))
    ax.plot(net_cgl, label="Net cgl {0}".format(np.abs(net_cgl).sum()))
    ax.plot(net_cgb, label="Net cgb {0}".format(np.abs(net_cgb).sum()))

    ax.legend()


def run_exp():

    ## Config

    SUN_TIMES = (15, 30)
    randomstate = np.random.RandomState(1234)
    T = 48

    price_1 = np.ones(T) * 12.0
    price_1[T // 2 :] = 16.0
    price_2 = np.ones(T) * 14.0
    price_s = np.ones(T) * 10.0

    b_max = 13
    b_min = 0
    e_c = 0.95
    e_d = 0.95
    d_max = 3
    d_min = -3
    battery = BatteryController(0, b_max, b_min, e_c, e_d, d_max, d_min)

    ## Reading data

    df = pd.read_csv("customers_data.csv")
    df["day"] = df.date.map(lambda x: x[:10])

    days_list = df.day.unique()
    users_list = df.customer.unique()
    N = len(users_list)

    ## Processing

    dataset = []

    start = time.time()

    for day in days_list[:5]:

        loads_ = []
        pss_ = []
        pbs_ = []
        costs_load_ = []
        costs_batt_ = []
        for i, user in enumerate(users_list[:]):

            load = df[(df.customer == user) & (df.day == day)].power.values.copy()
            solar = np.zeros_like(load)
            if i < N // 2:
                solar[SUN_TIMES[0] : SUN_TIMES[1]] = randomstate.uniform(
                    -1, 0, SUN_TIMES[1] - SUN_TIMES[0]
                )

            load += solar

            if (i > N // 4) and (i < N // 2):
                pb = price_2
            else:
                pb = price_1
            ps = price_s

            status, obj_bat, sol_bat = battery.find_optimal_step(load, pb, ps)
            if status != "optimal":
                raise ValueError("Optimization problem not optimal")

            cost_load = get_cost(load, pb, price_s)
            dataset.append((day, user, "load", cost_load) + tuple(load))
            dataset.append((day, user, "batt", obj_bat) + tuple(sol_bat + load))

            # Data for central planner
            loads_.append(load.copy())
            pbs_.append(pb.copy())
            pss_.append(ps.copy())
            costs_load_.append(cost_load)
            costs_batt_.append(obj_bat)

        status, obj, sol, om = solve_bat(
            loads_, pbs_, pss_, costs_load_, 0, 13, 0, 0.95, 0.95, 3, -3
        )
        if status != "optimal":
            raise ValueError("The big problem in day {0} broke".format(day))

        for i, s in enumerate(sol):
            net = (s + loads_[i]).copy()
            cost_ = get_cost(net, pbs_[i], pss_[i])
            dataset.append((day, users_list[i], "central_gl", cost_) + tuple(net))

        status, obj, sol, om = solve_bat(
            loads_, pbs_, pss_, costs_batt_, 0, 13, 0, 0.95, 0.95, 3, -3
        )
        if status != "optimal":
            raise ValueError("The big problem in day {0} broke".format(day))

        for i, s in enumerate(sol):
            net = (s + loads_[i]).copy()
            cost_ = get_cost(net, pbs_[i], pss_[i])
            dataset.append((day, users_list[i], "central_gb", cost_) + tuple(net))

        status, obj, sol, om = solve_bat(
            loads_, pbs_, pss_, [None] * len(loads_), 0, 13, 0, 0.95, 0.95, 3, -3
        )
        if status != "optimal":
            raise ValueError("The big problem in day {0} broke".format(day))

        for i, s in enumerate(sol):
            net = (s + loads_[i]).copy()
            cost_ = get_cost(net, pbs_[i], pss_[i])
            dataset.append((day, users_list[i], "central_gn", cost_) + tuple(net))

    columns = ["date", "user", "type", "cost"] + ["var{0}".format(x) for x in range(48)]
    final_dataset = pd.DataFrame(dataset)
    final_dataset.columns = columns

    elapsed = time.time() - start
    print("Elapsed time: {0}".format(elapsed))

    final_dataset.to_csv("final_dataset.csv", index=False)


if __name__ == "__main__":
    run_exp()
