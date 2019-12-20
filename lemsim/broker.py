import numpy as np
"""
Intermediary between a consumer and the market
"""


class ProsumerBroker:
    def __init__(self, prosumer, r=None):
        """
        Interface between the Prosumer and the market. In decomposes the bids
        into a set of single bids, submitts them to the market and process the results.
        """
        self.prosumer = prosumer
        self.r = r

    def market_bid(self, bid_type = 'long'):
        """
        Calculates the market bid to submit in the market
        """
        # The prosumer solves the control problem and returns
        # how much he expects to consume and at what price
        t = self.prosumer.time
        id_ = self.prosumer.owner_id
        bids_ac= self.prosumer.get_bid(bid_type)
        current_quantity = 0
        new_bids = []
        for q_, p_, b_ in bids_ac:
            if q_ > current_quantity:
                bid = (round(q_ - current_quantity, 4), p_, id_, b_, t)
                new_bids.append(bid)
                current_quantity = q_
            else:
                pass

        return new_bids

    def process_market_result(self, q, p, extra):
        """
        Process the market result, adding commitments and special prices
        to the prosumer
        """

        t = self.prosumer.time
        if not np.allclose(q, 0):
            self.prosumer.add_commitment(t, q)
            #self.prosumer.add_special_price(t, q, p)
            self.prosumer.add_cost(p)
        ## Maybe there should be something here to update the strategy if needed.
        self.prosumer.take_action()
        self.prosumer.move_forward()
