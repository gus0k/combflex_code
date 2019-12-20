"""
Solves the battery control problem using the LP
formulation
"""

import numpy as np
from lemsim.lp_with_reg import solve_bat

class BatteryController:
    """
    A manager class for a consumer that owns a battery
    and controls it using an LP
    """
    
    def __init__(self, owner_id, b_max, b_min, eff_c, eff_d, d_max, d_min, seed=420):
        """
        Instanciates the consumer with a battery
        Params:
            owner_id, str: unique identifier of the battery owner
            h, float: duration of each timeslot in hours
            b_max, float: maximum capacity of the battery in kWh
            b_min, float: minimum capacity of the battery in kWh
            eff_c, float: efficiency of charging the battery (0, 1]
            eff_d, float: efficiency of discharging the battery (0, 1]
            d_max, float: maximum amount of power that the battery can charge in kW
            d_min, float: maximum amount of power that the battery can discharge in kW
        """
        self.owner_id = owner_id
        self.b_max = b_max
        self.b_min = b_min
        self.eff_c = eff_c
        self.eff_d = eff_d
        self.d_max = d_max
        self.d_min = d_min
        self.charge = b_min
        self.seed = seed
    
    def reset(self, init_charge=None):
        """
        Resets the battey to `init_charge`. Defaults to
        reseting to the minimum.
        Params:
            init_charge, float: initial charge of the battery
        Returns:
            -
        """
        if init_charge:
            self.charge = init_charge
        else:
            self.charge = self.b_min
    
    def find_optimal_step(self, fload, fprice_b, fprice_s, commitment={}, reg=False):
        """
        Solves the optimal control of the battery using a forecast
        of the load and the prices for the remaining timeslots
        Params:
            fload, np.array: forecast of the future net load in kW
            fprice_b, np.array: forecast of the futre buying price
            fprice_s, np.array: forecast of the futre selling price
        Returns:
            xs, np.array: the optimal action for each of the timeslots consdiered
        """
        #if self.owner_id == 32:
        #    print(len(fload), commitment)
        res = solve_bat(fload,
                       fprice_b,
                       fprice_s,
                       self.charge,
                       self.b_max,
                       self.b_min,
                       self.eff_c,
                       self.eff_d,
                       self.d_max,
                       self.d_min,
                       commitment,
                       reg,
                       seed=self.seed
                      )
        a, b,c, d = res
        #if self.owner_id == 32:
        #    print(d.export_as_lp_string())
        return (a,b,c)

    def update_charge(self, x):
        """
        Updated the charge of the battery by an amount x
        """
        self.charge += x
