import lemsim.market_interface as lmar
import numpy as np
import dill
import pickle
from copy import deepcopy
from lemsim.utils import create_bid
from lemsim.wdp import WinnerDeterminationProblem
from lemsim.mechanism_variants import simple_split_mechanism, vcg_mechanism

class MainSim:
    """
    Main interface for running simulations
    """

    def __init__(self,
                 brokers,
                 randomstate=None,
                 bid_type='short',
                 pre_trade='none',
                 signaling='ismarket',
                 market_type='muda',
                 nickname=None,
                 sun_times=(15, 30),
                 seed=420
                ):


        #assert bid_type == 'short' or bid_type == 'long' or bid_type == 'flexible'
        #assert pre_trade == 'none' or pre_trade == 'yes'
        #assert signaling == 'ismarket' or signaling == 'clearing_price' or signaling == 'none'
        assert bid_type in ['short', 'long', 'flexible']
        assert pre_trade in ['none', 'yes']
        assert signaling in ['ismarket', 'clearing_price', 'none']
        assert market_type in ['muda', 'huang', 'p2p', 'combflex', 'combflex_split', 'combflex_vcg']
        self.brokers = deepcopy(brokers)
        self.r = np.random.RandomState(420) if randomstate is None else randomstate
        self.bid_type = bid_type
        self.pre_trade = pre_trade
        self.signaling = signaling
        self.market_type = market_type
        self.sun_times = sun_times
        self.nickname=nickname
        self.seed = seed


        self.days = 0
        self.results = []

    def one_market_round(self, param):
        """
        Implements one round of trading among all brokers
        """

        r = self.r
        bt = self.bid_type

        # Creates a new instance of the market
        mi = lmar.MarketInterface(r=r)
        for b in self.brokers:
            bid = b.market_bid(bt)
            call= b.process_market_result
            if len(bid) > 0:
                for block in bid:
                    mi.accept_bid(block, call)
            else:
                call(0, 0, {})

        #print('this is the param', param)
        #print(mi.bm.get_df())
        mi.clear(param, r=r)
        return mi

    def update_with_market_existance(self, per=0.1):
        """
        Updates the expected price of the prosumers using a signal
        that indicates availability of solar
        """
        sun_start, sun_end = self.sun_times
        for b in self.brokers:
            p = b.prosumer
            ps_ = p.price_sell.copy() * 1.0
            pb_ = p.price_buy.copy() * 1.0
            ps_[sun_start:sun_end] *= 1 + per
            pb_[sun_start:sun_end] *= 1 - per

            p.update_expected_price(pb_, buying=True)
            p.update_expected_price(ps_, buying=False)

    def update_with_last_market_price(self, results):
        """
        Updates the expected price of all prosumers
        using the last clearing price of the market

        #TODO this assumes the market is muda
        """
        EPS = 1e-4
        market_price = []
        for r in results:
            e = r.extra
            p1 = e.get('price_left', np.inf)
            p2 = e.get('price_right', np.inf)
            p1 = p1 if np.isfinite(p1) else None
            p2 = p2 if np.isfinite(p2) else None
            if p1 is None and p2 is None:
                pf = None
            elif p1 is None:
                pf = p2
            elif p2 is None:
                pf = p1
            else:
                pf = (p1 + p2) * 0.5
            market_price.append(pf)

        assert len(market_price) == self.brokers[0].prosumer.T

        for b in self.brokers:
            p = b.prosumer
            ps_ = p.price_sell.copy() * 1.0
            pb_ = p.price_buy.copy() * 1.0
            for t, mp in enumerate(market_price):
                if mp is not None:
                    ps_[t] = mp - EPS
                    pb_[t] = mp + EPS

            p.update_expected_price(pb_, buying=True)
            p.update_expected_price(ps_, buying=False)


    def sim_pre_trade(self, param):
        """
        Pre trades among prosumers so that they can properly optimize
        with knowledge of the future
        """
        r = self.r
        bt = self.bid_type
        T = self.brokers[0].prosumer.T

        results = []
        for t in range(T):
            #print(t)
            res = self.one_market_round(param)
            results.append(res)

        for b in self.brokers:
            b.prosumer.restart()

        return results

    def sim_comb_trade(self, alpha=0, beta=1):
        r = self.r
        bt = self.bid_type
        T = self.brokers[0].prosumer.T
        markup = True if self.signaling == 'ismarket' else False
        pro_dict = dict()
        bid_list = []
        for b_ in self.brokers:
            p = b_.prosumer
            load = p.register[0]['load']
            price_buy = p.register[0]['price_buy'].copy()
            price_sell = p.register[0]['price_sell'].copy()
            if markup:
                price_buy[15: 30] *= 0.9
                price_sell[15: 30] *= 1.1
                for t in range(48):
                    if price_buy[t] < price_sell[t]:
                        m = price_buy[t] + price_sell[t]
                        price_buy[t] = m * 0.5
                        price_sell[t] = m * 0.5
            pbat = p.get_profile_only_battery(0, pb=price_buy, ps=price_sell)

            bat = pbat - load
            bd, status  = create_bid(p.owner_id,
                                     load,
                                     bat,
                                     price_buy,
                                     price_sell,
                                     p.d_max,
                                     -p.d_min)
            if status is True:
                bid_list.append(bd)
                pro_dict[p.owner_id] = p

        if self.market_type == 'combflex':
            #print('entre normal')
            prob = WinnerDeterminationProblem(T, alpha, beta, seed=self.seed)
            [prob.add_bid(b_) for b_ in bid_list]
            prob.build_problem()
            _, _, _, (vb, vs, _), costs = prob.solve()         
        elif self.market_type == 'combflex_split':
            #print('entre split')
            #print(alpha, beta)
            prob, vb, vs, costs = simple_split_mechanism(bid_list, r, alpha, beta, seed=self.seed)     
        elif self.market_type == 'combflex_vcg':
            #print('Entré vcg')
            prob, vb, vs, costs = vcg_mechanism(bid_list, r, alpha, beta, seed=self.seed)
        
        for k, v in costs.items():
            pro_dict[int(k)].add_cost(v)
        
        #for k, v in vb.items():
        #    for i in range(T):
        #        pro_dict[int(k)].add_commitment(i, v[i])
        for k in vb:
            if k in vs:
                vb[k] -= vs[k]
        for k in vs:
            if k not in vb:
                vb[k] = -vs[k]
        
        for k, v in vb.items():
            for i in range(T):
                pro_dict[int(k)].add_commitment(i, v[i])
        
        
        return (bid_list, prob, costs, vb, vs)
        
    
    def simulate_day(self, alpha=0, beta=1):
        """
        Runs the simulation of one day forward
        """

        T = self.brokers[0].prosumer.T
        r = self.r
        bt = self.bid_type

        if self.pre_trade == 'yes' and 'combflex' not in self.market_type:
            results = self.sim_pre_trade(self.market_type)
        elif self.pre_trade == 'yes' and 'combflex' in self.market_type:
            results = self.sim_comb_trade(alpha, beta)
        else:
            results = []

        for t in range(T):
            #print(t)
            if self.pre_trade == 'none':
                res = self.one_market_round(self.market_type)
                results.append(res)
            else:
                for i, b in enumerate(self.brokers):
                    p = b.prosumer
                    p.take_action()
                    p.move_forward()

        for b in self.brokers:
            b.prosumer.finish_day()
            b.prosumer.get_profile_only_battery(self.days)
            b.prosumer.get_final_cost(self.days)


        self.results.append(results)

    def change_day(self, new_data):
        """
        New data is a dictionary containting for each prosumer
        possibly  the keys "load", "price_buy", "price_sell".

        Precondition: simulate_day has already been called.
        """

        for b in self.brokers:
            p = b.prosumer
            data_ = new_data.get(p.owner_id, {})
            load = data_.get('load', None)
            pb = data_.get('price_buy', None)
            ps = data_.get('price_sell', None)
            p.new_day(pb, ps, load)

        if self.signaling == 'ismarket':
            self.update_with_market_existance()
        elif self.signaling == 'clearing_price':
            self.update_with_last_market_price(self.results[-1])

        self.days += 1

    def save(self, name='sim', description=''):

        with open(f'{name}.pkl', 'wb') as fh: dill.dump(self, fh)

