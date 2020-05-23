import numpy as np
import dill
import pandas as pd
import os,sys,inspect
import copyreg
import types
import multiprocessing
import datetime
from os.path import expanduser


def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)

copyreg.pickle(types.MethodType, _pickle_method)

from concurrent.futures import ProcessPoolExecutor

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)
home = expanduser("~")

from lemsim.sim_manager import run_one_day

#####################################

#os.environ["CPLEXPATH"] = '/home/infres/dkiedanski/Cplex/cplex/bin/x86-64_linux/cplex'
os.environ["CPLEXPATH"] = "/home/guso/.local/bin/ibm/cplex/bin/x86-64_linux/cplex"
#os.environ["CPLEXPATH"] = '/opt/ibm/ILOG/CPLEX_Studio129/cplex/bin/x86-64_linux/cplex'
#print(parentdir)

NICK = 'sim_dec_1-'

T = 48
p_1 = np.ones(T) * 16.0
p_1[: T // 2] = 12.0
p_2 = np.ones(T) * 14
ps = np.ones(T) * 10.0

PARAMS = {
    'N': 50,
    'b_min': 0,
    'b_max': 13,
    'eff_c': 0.95,
    'eff_d': 0.95,
    'd_max': 1.25,
    'd_min': -1.25,
    'seed': 420,
    'PRICES_BUY': [p_1, p_2],
    'PRICES_SELL': [ps],
    'T': T,
    'PATHTODATA': '{0}/simulations/data/customers_data.csv'.format(parentdir),
    'DAYS': 1,
    'savepath': '{0}/Outputs/'.format(home),
}

###################################################




#def fun(args):
#    return run_one_day(args[0], args[1], onoff=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], nick=args[2])

if __name__ == '__main__':

    day = sys.argv[1]
    
    name = PARAMS['savepath']
    name += NICK
    name += day + '_' + '-'.join(map(str,[PARAMS[x] for x in ['N', 'seed', 'b_max', 'DAYS']]))
    name += '.csv'
    print(name)
    if os.path.isfile(name):
        print('File exists')
    else:
        #onof = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        onof = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        run_one_day(day, PARAMS, onoff=onof, nick=NICK)




#arguments = ((day, PARAMS, NICK) for day in DATES)
#with ProcessPoolExecutor() as executor:
#    for result in executor.map(fun, arguments):   # (*p) does the unpacking part
#        pass
