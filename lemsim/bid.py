import numpy as np


class simpleBundle:
    """
    A class that represents a single Bundle
    """

    def __init__(self, start, end, quantity, isbuying, unitcost, upper_bound=None):
        """
        Build a standard bid, in which quantity is desired at any point
        between start and end, at on average, the user wishes to pay
        no more than unit_cost per unit
        Items are ordered so it makes sense to speak of start and end.

        Parameters
        ----------

        uid : str
            Identifier of the agent

        start : int
            First item desired
        end : int
            Last item desired
        quantity : float
            Desired quantity to be adquired in total
        isbuying : bool
            `True` if the bid is for buying. `False` if the bid
            is for selling.
        unitcost : float
            Maximum price willing to pay for a given unit of
            any item.
        upper_bound : np.ndarray(float) of length (`end` - `start` + 1)
            Maximum quantity that can be bought or sold at each time-slot.

        Returns
        -------

        simpleBundle

        """

        self.start = start
        self.end = end
        self.quantity = quantity
        self.isbuying = isbuying
        self.unitcost = unitcost
        self.type = "simplebundle"

        if upper_bound is None:
            upper_bound = np.repeat(quantity, end - start + 1)
        self.upper_bound = upper_bound


class singleItem:
    """
    A bid for a single item
    """

    def __init__(self, item, quantity, unitcost, isbuying):
        self.item = item
        self.quantity = quantity
        self.unitcost = unitcost
        self.isbuying = isbuying
        self.type = "singleitem"


class bundleSelling:
    """
    Defines a bid for selling bunds when you
    want to keep some
    """

    def __init__(self, start, end, quantities, keep, unitcost, keep_quantities=None):
        """
        Initializes a bundle for selling with a keep quantity

        Parameters
        -----------
        start : int
            First time-slot of the bundle
        end : int
            Last (included) time-slot of the bundle
        quantities : np.ndarray of floats
            Maximum quantity available for selling in each of the time-slots
        keep : float
            Quantity that cannot be sold
        unitcost: float
            Mininum price at which the seller is willing to sell a unit.
        keep_quantities: np.ndarray of floats
            Maximum energy that can be kept in each time-slot. If it is None, then
            `quantities` is used as the deafult value.

        """
        self.start = start
        self.end = end
        assert quantities.shape[0] == (end - start + 1)
        assert (quantities > 0).all()
        self.quantities = quantities
        self.unitcost = unitcost
        assert keep <= quantities.sum()
        self.keep = keep
        if keep_quantities is None:
            keep_quantities = quantities.copy()
        assert keep_quantities.shape[0] == end - start + 1
        self.keep_quantities = keep_quantities

        self.type = "sellingbundle"

        tmp = keep_quantities.copy()
        tmp.sort()
        threshold = (
            next(
                (i for i, x in enumerate(np.cumsum(tmp)) if x >= keep), end - start + 1
            )
            + 1
        )
        self.threshold = threshold


def intervals_intercept(s1, e1, s2, e2):

    interval1 = list(range(s1, e1 + 1))
    interval2 = list(range(s2, e2 + 1))
    intersection = [x for x in interval1 if x in interval2]
    return len(intersection) > 0


class Bid:
    """
    Represents a bid, which is composed of bundles
    """

    def __init__(self, uid):
        self.uid = uid
        self.bundles = []
        self.sellingbundles = []
        self.singles = []

    def add_bundle(self, start, end, quantity, unitcost, isbuying, upper_bound=None):
        """
        Adds a new bundle to the bid. It checks to see if the new bundle would overlap
        with the old one in which case, an Exception is raised.

        Parameters
        -----------
        Same as to create a bundle

        Returns
        ---------
        bool
            True if the new bundle was added
        """
        consistent = True
        for bund in self.bundles + self.sellingbundles:
            if intervals_intercept(bund.start, bund.end, start, end):
                consistent = False

        vals = list(range(start, end + 1))
        for sing in self.singles:
            if (sing.item in vals) and (sing.isbuying != isbuying):
                consistent = False
        if consistent:
            new_bundle = simpleBundle(
                start, end, quantity, isbuying, unitcost, upper_bound
            )
            self.bundles.append(new_bundle)

        return consistent

    def add_single(self, item, quantity, unitcost, isbuying):
        """
        Adds a singleItem piece to the bid, only if there is not
        another singleItem piece at the same timeslot. If there
        was a bundle, it should be also for the same type of isbuying
        """

        consistent = True
        for s in self.singles:
            if s.item == item:
                consistent = False
        for b in self.bundles:
            vals = list(range(b.start, b.end + 1))
            if (item in vals) and (isbuying != b.isbuying):
                consistent = False
        for b in self.sellingbundles:
            vals = list(range(b.start, b.end + 1))
            if (item in vals) and isbuying:
                consistent = False

        if consistent:
            new_single = singleItem(item, quantity, unitcost, isbuying)
            self.singles.append(new_single)
        return consistent

    def add_bundle_selling(
        self, start, end, quantities, keep, unitcost, keep_quantities=None
    ):
        """
        Adds the selling bundle to the bid. It cannot overlap with other
        selling bounds and it cannot be at the same timeslot than a buying
        offer
        """
        timeslots = list(range(start, end + 1))
        consistent = True
        for s in self.singles:
            if (s.item in timeslots) and (s.isbuying is True):
                consistent = False
        for bund in self.bundles + self.sellingbundles:
            if intervals_intercept(start, end, bund.start, bund.end):
                consistent = False

        if consistent:
            new_bundle = bundleSelling(
                start, end, quantities, keep, unitcost, keep_quantities
            )
            self.sellingbundles.append(new_bundle)
        return consistent
