import numbers
import numpy as np
from lemsim.bid import Bid

CONSUME_CHARGE_BUY = 0
CONSUME_IDLE_BUY = 1
CONSUME_DISCHARGE_BUY = 2
CONSUME_DISCHARGE_NONE = 3
CONSUME_DISCHARGE_SELL = 4
NONE_CHARGE_BUY = 5
NONE_IDLE_NONE = 6
NONE_DISCHARGE_SELL = 7
PRODUCE_CHARGE_BUY = 8
PRODUCE_CHARGE_NONE = 9
PRODUCE_CHARGE_SELL = 10
PRODUCE_IDLE_SELL = 11
PRODUCE_DISCHARGE_SELL = 12

BUYING_STATES = [
    CONSUME_CHARGE_BUY,
    CONSUME_IDLE_BUY,
    NONE_CHARGE_BUY,
    NONE_IDLE_NONE,
    PRODUCE_CHARGE_BUY,
    PRODUCE_CHARGE_NONE,
]

SELLING_STATES = [
    PRODUCE_CHARGE_SELL,
    PRODUCE_CHARGE_NONE,
    PRODUCE_IDLE_SELL,
]

def derive_bid(load, bat_usage, price_buy, price_sell):
    
    EPS = 1e-9
    
    bat_usage = bat_usage
    load = load
    
    net = bat_usage + load
    #print('Net', net)
    
    action = []
    for l, b, n in zip(load, bat_usage, net):
        ac = ""
        if np.allclose(l, 0):
            ac += "NONE_"
        elif l > 0:
            ac += "CONSUME_"
        elif l < 0:
            ac += "PRODUCE_"
        if np.allclose(b, 0):
            ac += "IDLE_"
        elif b > 0:
            ac += "CHARGE_"
        elif b < 0:
            ac += "DISCHARGE_"
        if np.allclose(n, 0):
            ac += "NONE"
        elif n > 0:
            ac += "BUY"
        elif n < 0:
            ac += "SELL"

        action.append(eval(ac))

    bid_list = []

    cant_ = 0
    for t, a in enumerate(action):
        if a in [CONSUME_CHARGE_BUY, CONSUME_IDLE_BUY]:
            cant_ = load[t]
        elif a == CONSUME_DISCHARGE_BUY:
            cant_ = net[t]
        if cant_ > EPS:
            bid_ = ('buyone', t, cant_)
            bid_list.append(bid_)
            cant_ = 0

    build_buy_cant = 0
    building_buy = False
    building_buy_start_time = -1
    building_buy_end_time = -1
    for t, a in enumerate(action):
        #print(t, build_buy_cant)
        if a in BUYING_STATES and (not building_buy):
            building_buy = True
            building_buy_start_time = t
            pb_start = price_buy[t]
            bb_remove = []
        if (a not in BUYING_STATES) and (building_buy is True) and (price_buy[t] <= pb_start):
            building_buy = False
            building_buy_end_time = t - 1
            bid_ = ('buybundle', building_buy_start_time, building_buy_end_time, build_buy_cant, bb_remove)
            if build_buy_cant > EPS:
                bid_list.append(bid_)
            build_buy_cant = 0
            bb_remove = []
        if building_buy is True:
            bb_remove.append(min(load[t], 0))
            if a in [CONSUME_CHARGE_BUY, NONE_CHARGE_BUY]:
                build_buy_cant += bat_usage[t]
            elif a == PRODUCE_CHARGE_BUY:
                build_buy_cant += net[t]

    build_sell_cant = 0
    building_sell = False
    building_sell_start_time = -1
    building_sell_end_time = -1
    for t, a in enumerate(action):
        if a in SELLING_STATES and (not building_sell):
            building_sell = True
            building_sell_start_time = t
            building_sell_capacities = []
            building_sell_keep = 0
        if (a not in SELLING_STATES) and building_sell:
            building_sell_capacities = np.abs(np.array(building_sell_capacities))
            building_sell = False
            building_sell_end_time = t - 1
            bid_ = ('sellbundle', building_sell_start_time, building_sell_end_time,
                    building_sell_capacities, building_sell_keep)
            if building_sell_capacities.sum() - building_sell_keep > EPS:
                bid_list.append(bid_)

        if building_sell:

            building_sell_capacities.append(load[t])
            if a in [PRODUCE_CHARGE_SELL, PRODUCE_CHARGE_NONE]:
                building_sell_keep += bat_usage[t]

    return action, bid_list



def create_bid(uid, load, bat_usage, price_buy, price_sell, ramp_up=None, ramp_down=None, efc=0.95, efd=0.95):
    
    load = load.copy()
    bat_usage = bat_usage.copy()
    new_bid = Bid(uid)
    ac, bids = derive_bid(load, bat_usage, price_buy, price_sell)
    #print('-'*50)
    
    #print(ac)
    #print('-'*50)
    #for b in bids:
        #print(b)
    allin = True
        
    for bd in bids:
        bidtype = bd[0]
        if bidtype == 'buyone':
            t = bd[1]
            q = bd[2]
            cons = new_bid.add_single(item=t,
                               quantity=q,
                               unitcost=price_buy[t],
                               isbuying=True)
            
        elif bidtype == 'buybundle':
            t_start = bd[1]
            t_end = bd[2]
            quant = bd[3]
            remove = np.array(bd[4]).astype(float)
            if ramp_up is None:
                up_bound = np.repeat(quant, t_end - t_start + 1)
            elif isinstance(ramp_up, numbers.Number):
                up_bound = np.repeat(ramp_up, t_end - t_start + 1)
            else:
                assert len(ramp_up) == t_end - t_start + 1
                up_bound = ramp_up.copy()
            up_bound = up_bound.astype('float')
            #print(up_bound, remove)
            up_bound += remove
            cons = new_bid.add_bundle(start=t_start,
                               end=t_end,
                               quantity=quant,
                               isbuying=True,
                               unitcost=price_buy[t_start: t_end + 1].mean(), # TODO,
                               upper_bound=up_bound * 0.95
                               )
                           
        
        elif bidtype == 'sellbundle':
            t_start = bd[1]
            t_end = bd[2]
            quantities = bd[3]
            keep = bd[4]
            
            if ramp_down is None:
                up_bound = quantities.copy()
            elif isinstance(ramp_down, numbers.Number):
                up_bound = np.repeat(ramp_down, t_end - t_start + 1)
            else:
                assert len(ramp_down) == t_end - t_start + 1
                up_bound = ramp_down.copy()
            
            ## TODO: check this
    #        k_ = np.minimum(quantities, up_bound).sum()
    #        keep = min(keep, k_)
            cons = new_bid.add_bundle_selling(start=t_start,
                                       end=t_end,
                                       quantities=quantities,
                                       keep=keep,
                                       unitcost=price_sell[t_start: t_end + 1].mean(), # TODO
                                       keep_quantities=up_bound / efd
                                      )
        if cons is False:
            allin = False
    return new_bid, allin
