import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from objs import *
from rvs import *

def sim_wConstantEndToEndDelay():
	env = simpy.Environment()

	serv_time_rv = DiscreteRV(p_l=[1], v_l=[1])
	c = Client('c', env, serv_time_rv, num_reqs=5)
	s = Server('s', env)
	n = Net_wConstantEndToEndDelay('n', env, [c, s], delay=2*serv_time_rv.mean())
	env.run(until=c.wait)

if __name__ == '__main__':
	sim_wConstantEndToEndDelay()
