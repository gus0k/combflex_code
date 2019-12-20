"""

Winner determination problem for the combinatorial flexiblilty auction

"""
import itertools
from collections import defaultdict

import pulp as plp
import numpy as np
import os

class InvalidBid(Exception):
    pass


class WinnerDeterminationProblem:

    """
    Class for creating and solving the WDP
    associated with the combinatorial flexibility auction

    Parameters
    -----------
    M : int
        Quantity of goods that can be traded
    """

    def __init__(self, M, a=0, b=1, seed=420):
        self.M = M
        self.vars_buying = defaultdict(list)
        self.vars_selling = defaultdict(list)
        self.vars_unitcost = dict()
        self.vars_payment = []
        self.constraints = []
        self.bids = []
        self.model = None
        self.is_solved = False
        self.price_buy = None
        self.price_sell = None
        self.a = a
        self.b = b
        self.seed = seed

    def add_bid(self, bid):
        """
        Adds the bid to the problem. There
        are different types of bids.

        Parameters
        ----------

        bid : Bid
            A bid that can be of many types. For now: `simple`

        Returns
        ---------
        bool:
            True if the bid was added, and False if it was not
        """
        try:
            check_bid(bid, self.M)
            self.bids.append(bid)
            return True
        except InvalidBid as e:
            print(e)
            return False

    def build_problem(self, budgetbalanced=False):
        """
        Creates a new model in PulP to solve the WDP
        """

        mdl = plp.LpProblem(name="WDP")
        #mdl.parameters.randomseed.set(seed)

        cost_buying = []
        cost_selling = []

        for bid_ in self.bids:
            uid = bid_.uid
            vars_ = []
            pieces = bid_.bundles + bid_.singles + bid_.sellingbundles
            for i, b_ in enumerate(pieces):
                fun = None
                if b_.type == "simplebundle":
                    fun = generate_bundle_constraints
                elif b_.type == "singleitem":
                    fun = generate_single_constraints
                elif b_.type == "sellingbundle":
                    fun = generate_selling_bundle

                var_d, cons_l, pay_l, cost, isbuying = fun(b_, i, uid)

                for k, v in var_d.items():
                    vars_.append(v)
                    self.vars_unitcost[v._LpElement__name] = b_.unitcost
                    if isbuying:
                        self.vars_buying[k].append(v)
                    else:
                        self.vars_selling[k].append(v)

                self.constraints.extend(cons_l)
                self.vars_payment.extend(pay_l)
                if isbuying:
                    cost_buying.append(cost)
                else:
                    cost_selling.append(cost)

        ## Adding general constraints

        # Selling and buying should be the same for all items
        for m in range(self.M):
            var_b = self.vars_buying[m]
            var_s = self.vars_selling[m]

            cons_time = plp.LpConstraint(
                e=plp.lpSum(var_b) - plp.lpSum(var_s),
                sense=plp.LpConstraintEQ,
                rhs=0,
                name="cons_time_balance_{0}".format(m),
            )
            self.constraints.append(cons_time)

        # Weakly budget balanced payments
        sign = plp.LpConstraintGE if not budgetbalanced else plp.LpConstraintEQ
        cons_budget = plp.LpConstraint(
            e=plp.lpSum(self.vars_payment),
            sense=sign,
            rhs=0,
            name="cons_budget_balance",
        )
        self.constraints.append(cons_budget)

        # Build model

        for cons in self.constraints:
            mdl += cons

        objective = plp.lpSum(cost_buying) - plp.lpSum(cost_selling)
        mdl.sense = plp.LpMaximize
        mdl.setObjective(objective)

        self.model = mdl
        self.is_solved = False
        return mdl

    def solve(self):
        """
        Solves the model if it has one
        #TODO: check different solvers

        Returns
        --------

        status_ : str
            The status after solving the problem.
        objective_: float
            The value of the objective function evaluated in the solution
        vars_ : dict
            A list of pairs with the names of the variables and their value
            in the solution
        """

        CPLEXPATH = os.environ.get('CPLEXPATH', None)
        vars_ = dict()
        status_ = None
        objective_ = None
        if self.model is not None:
            self.model.solve(plp.CPLEX_CMD(CPLEXPATH, options=['set randomseed {0}'.format(self.seed)]))

            status_ = plp.LpStatus[self.model.status]
            objective_ = plp.value(self.model.objective)
            for v in self.model.variables():
                vars_[v.name] = v.varValue
                
        summary_ = compute_results(vars_)
        self.summary = summary_
        self.is_solved = True
        costs = self.get_costs()
        
        return status_, objective_, vars_, summary_, costs
    
    
    
    def get_prices(self):
        """
        For each time-slot determines the maximum selling price
        and minimum buying price that were involved in the trading

        Parameters
        -----------
        wdp: WinnerDeterminationProblem
            pre - It has to be solved

        Returns
        -----------
        list of tuples:
            For each time-slot, the (minimum buying price, maximum selling price)

        """
        a = self.a
        b = self.b
        price_buy = np.ones(48) * -1.0
        price_sell = np.ones(48) * -1.0
        if self.is_solved and (b >= a):
            res = []
            for t in range(48):
                selling, buying = [], []
                for v in self.model.variables():
                    if v.name in [x._LpElement__name for x in self.vars_buying[t]]:
                        if v.varValue > 0:
                            buying.append(self.vars_unitcost[v.name])
                    if v.name in [x._LpElement__name for x in self.vars_selling[t]]:
                        if v.varValue > 0:
                            selling.append(self.vars_unitcost[v.name])
                min_b = min(buying) if len(buying) > 0 else -1
                max_s = max(selling) if len(selling) > 0 else -1
                if min_b != -1 and max_s != -1:
                    ps = max_s * (1 - a) + a * min_b
                    pb = max_s * (1 - b) + b * min_b
                else:
                    pb, ps = -1, -1
                price_buy[t] = pb
                price_sell[t] = ps
                res.append((pb, ps))

        self.price_buy = price_buy
        self.price_sell = price_sell
        return res

    def get_costs(self, price_buy=None, price_sell=None):

        if price_buy is None:
            if self.is_solved is True and self.price_buy is None:
                self.get_prices()
            price_buy = self.price_buy
        if price_sell is None:
            if self.is_solved is True and self.price_sell is None:
                self.get_prices()
            price_sell = self.price_sell

        costs = defaultdict(float)
        vb, vs, _ = self.summary
        for k, v in vb.items():
            for t in range(self.M):
                costs[k] += v[t] * price_buy[t]
        for k, v in vs.items():
            for t in range(self.M):
                costs[k] -= v[t] * price_sell[t]

        return costs
    
def compute_results(sol):
    varbuy = defaultdict(lambda :np.zeros(48))
    varsell = defaultdict(lambda :np.zeros(48))
    payment = defaultdict(float)
    for k, v in sol.items():
        sp = k.split('_')
        if sp[0] == 'payment':
            uid = sp[2]
            payment[uid] += v
        elif sp[0] == 'x':
            t = int(sp[2])
            uid = sp[-1]
            if sp[1] == 'sellingbundle':
                varsell[uid][t] += v
            elif sp[1] == 'bundle':
                varbuy[uid][t] += v
            elif sp[1] == 'single':
                varbuy[uid][t] += v
        
    return varbuy, varsell, payment    
    

def generate_single_constraints(bid, i, uid):
    """
    Generates all the constraints for a singleitem
    bid
    """
    vars_list = []
    vars_dict = dict()
    constraints_list = []
    payment_list = []
    item = bid.item
    quantity = bid.quantity
    isbuying = bid.isbuying
    unitcost = bid.unitcost

    var_ = plp.LpVariable(
        cat=plp.LpContinuous,
        lowBound=0,
        upBound=quantity,
        name="x_single_{0}_{1}".format(item, uid),
    )
    vars_dict[item] = var_
    vars_list.append(var_)

    bnd = (0, None) if isbuying else (None, 0)
    payment_ = plp.LpVariable(
        cat=plp.LpContinuous,
        lowBound=bnd[0],
        upBound=bnd[1],
        name="payment_single_{0}_{1}".format(uid, i),
    )
    payment_list.append(payment_)

    # Add a constraint for the payment (IR)
    sign = 1 if isbuying else -1
    cons_ir = plp.LpConstraint(
        e=sign * plp.lpSum(vars_list) * unitcost - payment_,
        sense=plp.LpConstraintGE,
        rhs=0,
        name="cons_single_ir_{0}_{1}".format(uid, i),
    )
    constraints_list.append(cons_ir)

    cost = [unitcost * v for v in vars_list]

    return vars_dict, constraints_list, payment_list, cost, isbuying


def generate_bundle_constraints(bundle, i, uid):
    """
    Generates all the bundle_associated
    variables and constraints

    Parameters
    -----------
    bundle: bundle
        Bundle to add to the problem
    i: int
        Identifier of the bundle inside the bid
    uid: str
        Identifier of the agent
    """

    vars_list = []
    vars_dict = dict()
    constraints_list = []
    payment_list = []
    start = bundle.start
    end = bundle.end
    quantity = bundle.quantity
    isbuying = bundle.isbuying
    unitcost = bundle.unitcost

    # Create a variable for each item desired
    for t in range(start, end + 1):
        var_ = plp.LpVariable(
            cat=plp.LpContinuous,
            lowBound=0,
            upBound=bundle.upper_bound[t - start],
            name="x_bundle_{0}_{1}_{2}".format(t, i, uid),
        )
        vars_dict[t] = var_
        vars_list.append(var_)
        # if isbuying:
        #    self.vars_buying[t].append(var_)
        # else:
        #    self.vars_selling[t].append(var_)

    # Add a constraint on the total quantity desired
    cons_sum = plp.LpConstraint(
        e=plp.lpSum(vars_list),
        sense=plp.LpConstraintLE,
        rhs=quantity,
        name="cons_bundle_quantity_{0}_{1}".format(i, uid),
    )
    # self.constraints.append(cons_sum)
    constraints_list.append(cons_sum)

    # Add a variable for the payment
    if isbuying:
        payment_ = plp.LpVariable(
            cat=plp.LpContinuous,
            lowBound=0,
            name="payment_bundle_{0}_{1}".format(uid, i),
        )
    else:
        payment_ = plp.LpVariable(
            cat=plp.LpContinuous,
            upBound=0,
            name="payment_bundle_{0}_{1}".format(uid, i),
        )
    # self.vars_payment.append(payment_)
    payment_list.append(payment_)

    # Add a constraint for the payment (IR)
    if isbuying:
        cons_ir = plp.LpConstraint(
            e=plp.lpSum(vars_list) * unitcost - payment_,
            sense=plp.LpConstraintGE,
            rhs=0,
            name="cons_bundle_ir_{0}_{1}".format(uid, i),
        )
    else:
        cons_ir = plp.LpConstraint(
            e=-plp.lpSum(vars_list) * unitcost - payment_,
            sense=plp.LpConstraintGE,
            rhs=0,
            name="cons_bundle_ir_{0}_{1}".format(uid, i),
        )

    constraints_list.append(cons_ir)

    cost = [unitcost * v for v in vars_list]

    return vars_dict, constraints_list, payment_list, cost, isbuying


def generate_selling_bundle(bundle, i, uid):
    """
    Generates all the selling bundle_associated
    variables and constraints

    Parameters
    -----------
    bundle: selling bundle
        Bundle to add to the problem
    i: int
        Identifier of the bundle inside the bid
    uid: str
        Identifier of the agent
    """

    vars_list = []
    vars_dict = dict()
    constraints_list = []
    payment_list = []
    start = bundle.start
    end = bundle.end
    keep = bundle.keep
    quantities = bundle.quantities
    unitcost = bundle.unitcost
    keep_quantities = bundle.keep_quantities
    threshold = bundle.threshold
    L = end - start + 1

    # Create a variable for each item desired
    for t in range(start, end + 1):
        var_ = plp.LpVariable(
            cat=plp.LpContinuous,
            lowBound=0,
            upBound=quantities[t - start],
            name="x_sellingbundle_{0}_{1}_{2}".format(t, i, uid),
        )
        vars_dict[t] = var_
        vars_list.append(var_)

    count = 0
    for k in range(0, threshold):
        for ele in itertools.combinations(range(L), k):

            sum_qs = sum(quantities[t] for t in range(L) if t not in ele)
            sum_comp = sum(keep_quantities[t] for t in ele)

            cons_ = plp.LpConstraint(
                e=plp.lpSum(vars_dict[t] for t in range(start, end + 1) if t not in ele),
                sense=plp.LpConstraintLE,
                rhs=sum_qs + sum_comp - keep,
                name="cons_sellingbundle_keepable_{0}_{1}_{2}".format(count, i, uid),
            )
            constraints_list.append(cons_)
            count += 1

    # Add a constraint on the total quantity desired
    # cons_sum = plp.LpConstraint(
    #     e=plp.lpSum(vars_list),
    #     sense=plp.LpConstraintLE,
    #     rhs=quantity,
    #     name="cons_bundle_quantity_{0}".format(uid),
    # )
    # # self.constraints.append(cons_sum)
    # constraints_list.append(cons_sum)

    # Add a variable for the payment
    payment_ = plp.LpVariable(
        cat=plp.LpContinuous,
        upBound=0,
        name="payment_sellingbundle_{0}_{1}".format(uid, i),
    )
    # self.vars_payment.append(payment_)
    payment_list.append(payment_)

    # Add a constraint for the payment (IR)
    cons_ir = plp.LpConstraint(
        e=-plp.lpSum(vars_list) * unitcost - payment_,
        sense=plp.LpConstraintGE,
        rhs=0,
        name="cons_sellingbundle_ir_{0}_{1}".format(uid, i),
    )

    constraints_list.append(cons_ir)

    cost = [unitcost * v for v in vars_list]

    return vars_dict, constraints_list, payment_list, cost, False


def check_bid(bid, M):
    """
    Checks whether the bid fits the problem

    Parameters
    ----------
    bid : Bid
        A bid object
    M: int
        Number of objects to trade
    """

    for bundle in bid.bundles:
        try:
            assert bundle.end <= M
        except AssertionError:
            raise InvalidBid("Too many objects to trade")
        try:
            assert bundle.start <= bundle.end
        except AssertionError:
            raise InvalidBid("End is smaller than beginning")
        try:
            assert bundle.upper_bound.shape[0] == bundle.end - bundle.start + 1
        except AssertionError:
            raise InvalidBid("Malformed upper bound")

    return True


