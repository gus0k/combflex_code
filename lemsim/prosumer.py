"""
Prosumer class, extendes the battery controler
"""
import numpy as np
from copy import deepcopy
from operator import itemgetter
from lemsim.batterycontroller import BatteryController

class Prosumer(BatteryController):

    def __init__(self, owner_id, b_max, b_min, eff_c, eff_d, d_max, d_min, price_buy, price_sell, load, seed=420):
        super().__init__(owner_id, b_max, b_min, eff_c, eff_d, d_max, d_min, seed)
        self.day = 0
        self.price_buy = price_buy.copy()
        self.price_sell = price_sell.copy()
        self.load = load.copy()
        self.time = 0
        self.T = load.shape[0]
        self.net_demand = np.zeros(self.T)
        self.special_price = {}
        self.commitments = {}
        self.extra_cost = 0

        self.expected_price_sell = np.zeros(self.T)
        self.expected_price_buy = np.zeros(self.T)

        self.update_expected_price(price_buy, True)
        self.update_expected_price(price_sell, False)

        self.register = {0:{
            'load' : self.load.copy(),
            'price_buy': self.price_buy.copy(),
            'price_sell': self.price_sell.copy(),
            'initial_course': {},
        }}

    def get_profile_only_battery(self, day, pb=None, ps=None):
        cons = []
        T_ = self.time
        C_ = self.charge
        load = self.register[day]['load']
        if pb is None:
            pb = self.register[day]['price_buy']
        if ps is None:
            ps = self.register[day]['price_sell']

        self.time = 0
        self.charge = 0
        for t in range(len(load)):
            xs_ = self.find_optimal_step(load[t:], pb[t:], ps[t:], {})
            xs = xs_[2]
            self.update_charge(xs[0])
            cons.append(xs[0] / self.eff_c if xs[0] > 0 else xs[0] * self.eff_d)
        profile_only_battery = np.array(cons) + load
        self.update_charge(C_)
        self.time = T_
        self.register[day]['profile_only_battery'] = profile_only_battery
        return profile_only_battery

    def move_forward(self):
        self.time += 1

#
    def restart(self):
        self.reset()
        self.time = 0
        self.net_demand = np.zeros(self.T)

    def finish_day(self):
        day = self.day
        #print(self.owner_id, self.day, self.commitments)
        self.register[day]['net_demand'] =  self.net_demand.copy()
        self.register[day]['special_price'] =  deepcopy(self.special_price)
        self.register[day]['extra_cost'] = self.extra_cost
        self.register[day]['commitments'] = deepcopy(self.commitments)
        self.register[day]['expected_sell'] = self.expected_price_sell.copy()
        self.register[day]['expected_buy'] = self.expected_price_buy.copy()

    def new_day(self, new_price_buy=None, new_price_sell=None, new_load=None):
        
        self.register[self.day]['final_cost'] = self.get_final_cost(self.day)
        self.reset()
        self.day += 1
        self.time = 0
        self.net_demand = np.zeros(self.T)
        self.commitments = {}
        self.special_price = {}

        if new_price_buy is not None:
            self.price_buy = new_price_buy.copy()
            self.update_expected_price(new_price_buy, True)
        if new_price_sell is not None:
            self.price_sell = new_price_sell.copy()
            self.update_expected_price(new_price_sell, False)
        if new_load is not None:
            self.load = new_load.copy()


        self.register[self.day] = {
            'load' : self.load.copy(),
            'price_buy': self.price_buy.copy(),
            'price_sell': self.price_sell.copy(),
            'initial_course': {}
        }



    def update_expected_price(self, price, buying=True):
        EPS = 1e-4
        if buying:
            self.expected_price_buy = price.copy()
        else:
            self.expected_price_sell = price.copy()
        ## Fix problems
        for t in range(self.T):
            epb_ = self.expected_price_buy[t]
            eps_ = self.expected_price_sell[t]
            if epb_ < eps_:
                new_val = (epb_ + eps_) * 0.5
                self.expected_price_sell[t] = new_val - EPS
                self.expected_price_buy[t] = new_val + EPS

    def add_special_price(self, timeslot, quantity, price):
        self.special_price[timeslot] = (quantity, price)
        
    def add_cost(self, cost):
        self.extra_cost += cost
        #print('entre', self.extra_cost)

    def get_final_cost(self, day):
        price = self.extra_cost
        #print(self.owner_id, price)
        if 'net_demand' not in self.register[day]:
            self.finish_day()
        D = self.register[day]['net_demand']
        pb = self.register[day]['price_buy']
        ps = self.register[day]['price_sell']
        comm = self.register[day]['commitments']
        #print(self.owner_id, comm)
        #sp = self.register[day]['special_price']

        for t in range(self.T):
            p_ = pb[t] if D[t] > 0 else ps[t]
            if t in comm and comm[t] is not None:
                if np.abs(D[t]) > np.abs(comm[t]):
                    price += (D[t] - comm[t]) * p_
            #if t in sp:
            #    q1, p1 = sp[t]
            #    if np.abs(D[t]) > np.abs(q1):
            #        #price += q1 * p1 + (D[t] - q1) * p_
            #        price += p1 + (D[t] - q1) * p_
            #    else:
            #        # price += D[t] * p1
            #        price += p1
            else:
                price += D[t] * p_
            

            
        return price

    def get_bid(self, bid_type='short', EPS=1e-4):
        """
        Estimate the consumption of the next timeslot
        Returns:
            q: quantity wanted to be traded in the market
            p: price at which it would normall be traded
        """
        t = self.time
        load = self.load[t:].copy().astype(float)
        pb = self.expected_price_buy[t:].copy().astype(float)
        ps = self.expected_price_sell[t:].copy().astype(float)


        # Gets a list of all the commitments applicable
        N = self.load.shape[0]
        commitments = {}
        for ii in range(t, N + 1):
            commitments[ii - t] = self.commitments.get(ii, None)

        accumulated_bids = []
        ## Solves the first battery usage
        r = self.find_optimal_step(load, pb, ps, commitments) # battery usage
        x = r[2][0]
        q = x / self.eff_c if x > 0 else x * self.eff_d # Energy seen from outside the battery
        q += load[0] #* self.resolution
        q_0 = q
        buying = (q > 0) or (q == 0 and load[0] > 0)
        p = pb[0] if q > 0 else ps[0]
        if not np.allclose(q, 0):
            accumulated_bids.append([np.abs(q), p, buying])

        if bid_type == 'long':

            if buying: # Case in which user is buying by default
                future_prices = set(p_ for p_ in pb if p_ < pb[0])
                future_prices = sorted([x for x in future_prices], reverse=True)
            else:
                pbs = np.hstack([ps, pb])
                future_prices = set(p_ for p_ in pbs if p_ > ps[0])
                future_prices = sorted([x for x in future_prices], reverse=False)

            for fp in future_prices[:5]:
                pb_1 = pb.copy()
                ps_1 = ps.copy()
                if buying:
                    pb_1[0] = fp - EPS # Force solution to be in different range
                    if pb_1[0] < ps_1[0]:
                        ps_1[0] = pb_1[0]
                    r = self.find_optimal_step(load, pb_1, ps_1, commitments) #
                else:
                    ps_1[0] = fp + EPS
                    if ps_1[0] > pb_1[0]:
                        pb_1[0] = ps_1[0]
                    r = self.find_optimal_step(load, pb_1, ps_1, commitments) #
                x = r[2][0] # first battery usage
                q = x / self.eff_c if x > 0 else x * self.eff_d
                q += load[0] #* self.resolution
                if not np.allclose(q, 0) and ((buying and q > 0) or (not buying and q < 0)):
                    accumulated_bids.append([np.abs(q), fp, buying])

        bids_sorted = sorted(accumulated_bids, key=itemgetter(1, 0, 2), reverse=True)
        return accumulated_bids

    
    def add_commitment(self, timeslot, quantity):

        commit = None if np.allclose(quantity, 0, atol=1e-5) else quantity
        #print(self.owner_id, timeslot, commit)
        self.commitments[timeslot] = commit
        if (self.owner_id == 4):
            pass

    def take_action(self):
        """
        Process the market result and takes the appropiate
        action to move forward
        Params:
            traded_quantity, amount of energy that was finally traded
            in the market
            traded_price: price at which it was traded.
        """
        #print('entre', self.owner_id)     
        t = self.time
        load = self.load[t:].copy()
        pb = self.expected_price_buy[t:].copy()
        ps = self.expected_price_sell[t:].copy()

        pb[0] = self.price_buy[t]
        ps[0] = self.price_sell[t]

        N = self.load.shape[0]
        commitments_ = {}
        for ii in range(t, N + 1):
            commitments_[ii - t] = self.commitments.get(ii, None)
      
        xs_ = self.find_optimal_step(load, pb, ps, commitments_) # battery usage
        self.register[self.day]['initial_course'][t] = xs_
        xs = xs_[2]
        xf = xs[0]

        #self.post_market.append([pb.copy(), ps.copy(), commitment, self.charge, xf])
        # Update the battery with the new action
        self.update_charge(xf)

        q = xf / self.eff_c if xf > 0 else xf * self.eff_d
        q += load[0] #* self.resolution
        self.net_demand[t] = q
       