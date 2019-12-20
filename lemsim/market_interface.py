import pymarket as pm
import numpy as np


class MarketInterface(pm.Market):
    """
    Extends a normal market to add
    the ability to recieve a callback.
    It is assumed that only one bid will be recieved
    for each broker

    """

    def __init__(self, r=None):
        super().__init__()
        self.callbacks = {}
        self.used_buying_prices = set()
        self.used_selling_prices = set()

        if r is None:
            self.r = np.random.RandomState(1234)
        else:
            self.r = r

        self.users = -1
        self.users_to_key = {}
        self.key_to_users = {}
        self.users_added = set()

    def accept_bid(self, bid, callback):
        uset = self.used_buying_prices if bid[3] else self.used_selling_prices
        new_p = bid[1]
        owner_id = bid[2]
        eps = 0
        counter = 0
        while ((bid[1] + eps) in uset) and (counter < 1e4):
            eps = self.r.randint(-1e3, 1e3) / 1e4
            counter += 1
        if counter == 1e4:
            raise ValueError('bid could not be added')
        else:
            uset.add(bid[1] + eps)
            if owner_id in self.users_to_key:
                uid = self.users_to_key[owner_id]
            else:
                self.users += 1
                uid = self.users
                self.key_to_users[uid] = owner_id
                self.users_to_key[owner_id] = uid
            new_bid = (bid[0], bid[1] + eps, uid, bid[3], bid[4])
            id_ = super().accept_bid(*new_bid)
            self.callbacks[uid] = callback
            return id_


    def clear(self, method='muda', r=None):
        if len(self.used_buying_prices) == 0 or len(self.used_selling_prices) == 0:
            for k in self.callbacks:
                self.callbacks[k](0, 0, {})
            results = []
        else:
            self.method = method
            if method=='huang':
                tr, ex = self.run(method)
            else:
                tr, ex = self.run(method, r=r)
            results = []
            for k in self.callbacks:
                q, p = self.get_user_result(k)
                self.callbacks[k](q, p, ex)
                results.append((self.key_to_users[k], q, p))

        self.results = results

    def get_user_result(self, user_id):
        """
        Finds the total quantity and price traded
        by a given broker
        """
        tr = self.transactions.get_df()
        bids = self.bm.get_df()
        extra = self.extra

        bid_id = bids.index[bids.user == user_id].tolist()
        buying = bids.iloc[bid_id[0], :].buying
        trans = tr[tr.bid.isin(bid_id)]
        if trans.shape[0] > 0:
            quantity_traded = trans.quantity.sum()
            price = trans.apply(lambda x: x.quantity * x.price, axis=1).sum()
            if self.method == 'muda':
                price += extra['fees'][user_id]
            #price_per_unit = price / quantity_traded if quantity_traded > 0 else 0
            if not buying:
                quantity_traded *= -1.0
                price *= -1.0
            return quantity_traded, price
        else:
            return 0, 0



