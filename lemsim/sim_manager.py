import time
import numpy as np
import pandas as pd
import pickle
import time
import matplotlib.pyplot as plt
from lemsim.simulation_runner import simulation_run, global_metrics
from lemsim.utils import create_bid

def run_one_day(day, PARAMS, onoff=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], nick=''):
    start = time.time()
    sims = []
    rows = []

    if onoff[0]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'none',
            'market_type': 'combflex'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[1]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'none',
            'market_type': 'combflex_split'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[2]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'none',
            'market_type': 'combflex_vcg'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[3]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'none',
            'market_type': 'combflex',
            'combflex_alpha': 0.5,
            'combflex_beta': 0.5
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[4]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'none',
            'market_type': 'combflex_split',
            'combflex_alpha': 0.5,
            'combflex_beta': 0.5
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[5]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'none',
            'market_type': 'combflex_vcg',
            'combflex_alpha': 0.5,
            'combflex_beta': 0.5
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)    

    if onoff[6]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'ismarket',
            'market_type': 'combflex'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[7]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'ismarket',
            'market_type': 'combflex_split'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[8]:
        param_ = {
            'bid_type': 'flexible',
            'pre_trade': 'yes',
            'signaling': 'ismarket',
            'market_type': 'combflex_vcg'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[9]:
        param_ = {
            'bid_type': 'long',
            'pre_trade': 'yes',
            'signaling': 'ismarket',
            'market_type': 'huang'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)    

    if onoff[10]:
        param_ = {
            'bid_type': 'short',
            'pre_trade': 'none',
            'signaling': 'none',
            'market_type': 'muda'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)

    if onoff[11]:
        param_ = {
            'bid_type': 'long',
            'pre_trade': 'yes',
            'signaling': 'ismarket',
            'market_type': 'muda'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)    

    if onoff[12]:
        param_ = {
            'bid_type': 'short',
            'pre_trade': 'none',
            'signaling': 'ismarket',
            'market_type': 'p2p'
        }
        sim_ = simulation_run(
        nick + '-'.join(map(str, param_.values())), settings=param_, DATE=day, **PARAMS
        )
        sims.append(sim_)    


    metrics = global_metrics(DATE=day, **PARAMS)
    r = (day, 'Optimal Auto-consumtion', 'Auto-consumption', metrics.get('optimal_auto_cons'))
    rows.append(r)
    r = (day, 'Optimal Auto-consumption Guarnatee', 'Auto-consumption', metrics.get('optimal_auto_cons_guarantee_battery'))
    rows.append(r)
    r = (day, 'Auto-consumption Battery', 'Auto-consumption', metrics.get('auto_cons_battery'))
    rows.append(r)
    r = (day, 'Social Cost Default', 'Total cost', metrics.get('social_cost_default'))
    rows.append(r)
    r = (day, 'Social Cost Battery', 'Total cost', metrics.get('total_cost_battery'))
    rows.append(r)

    for sim_ in sims:
        r = (day, sim_.nickname, 'Auto-consumption', sim_.metric_results.get('auto_cons_market'))
        rows.append(r)
        r = (day, sim_.nickname, 'Total cost', sim_.metric_results.get('social_cost'))
        rows.append(r)
        r = (day, sim_.nickname, 'Max Inc Cost', sim_.metric_results.get('maximum_increase_costs'))
        rows.append(r)
        r = (day, sim_.nickname, 'Max Dec Cost', sim_.metric_results.get('minimum_decrease_costs'))
        rows.append(r)
        

    end = time.time()
    print(end - start)
    
    df = pd.DataFrame(rows)
    name = PARAMS['savepath']
    name += nick
    name += day + '_' + '-'.join(map(str,[PARAMS[x] for x in ['N', 'seed', 'b_max', 'DAYS']]))
    name += '.csv'
    df.to_csv(name, index=False)
    
    #return rows, sims

