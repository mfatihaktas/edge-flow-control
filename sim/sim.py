import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from objs import *
from rvs import *
from plot_utils import *

def plot_client(c):
	fontsize = 14

	# CDF of req response times
	ax = plot.gca()
	# for sid, T_l in sid__T_l_m.items():
	# 	add_cdf(T_l, ax, sid, next(nice_color)) # drawline_x_l=[1000*self.max_delay]
	add_cdf(c.response_time_l, ax, '', next(nice_color))
	# plot.xscale('log')
	plot.xticks(rotation=70)
	plot.ylabel('CDF', fontsize=fontsize)
	plot.xlabel('Response time', fontsize=fontsize)
	plot.legend(fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_cdf_T.png", bbox_inches='tight')
	plot.gcf().clear()

	# CDF of inter result times
	ax = plot.gca()
	add_cdf(c.inter_result_time_l, ax, '', next(nice_color)) # drawline_x_l=[1000*self.inter_job_gen_time_rv.mean()]
	plot.xscale('log')
	plot.xticks(rotation=70)
	plot.ylabel('CDF', fontsize=fontsize)
	plot.xlabel('Inter result arrival time', fontsize=fontsize)
	plot.legend(fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_cdf_interResultTime.png", bbox_inches='tight')

	log(DEBUG, "done.")

def sim_wConstantEndToEndDelay():
	env = simpy.Environment()

	serv_time_rv = DiscreteRV(p_l=[1], v_l=[1])
	sid = 's'
	s = Server(sid, env)
	c = Client('c', env, serv_time_rv, num_req_to_recv=100, sid=sid)
	n = Net_wConstantDelay('n', env, [s, c], delay=2*serv_time_rv.mean())
	env.run(until=c.wait)
	# env.run(until=10)

	plot_client(c)

if __name__ == '__main__':
	sim_wConstantEndToEndDelay()
