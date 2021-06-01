import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from objs import *
from rvs import *
from plot_utils import *

NUM_SERVER = 2

def plot_client(c):
	fontsize = 14

	## CDF of req response times
	response_time_l = [r.epoch_arrived_client - r.epoch_departed_client for r in c.result_l]
	ax = plot.gca()
	# for sid, T_l in sid__T_l_m.items():
	# 	add_cdf(T_l, ax, sid, next(nice_color)) # drawline_x_l=[1000*self.max_delay]
	add_cdf(response_time_l, ax, '', next(nice_color))
	# plot.xscale('log')
	plot.xticks(rotation=70)
	plot.ylabel('CDF', fontsize=fontsize)
	plot.xlabel('Response time', fontsize=fontsize)
	# plot.legend(fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_cdf_T_ns_{}.png".format(NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	## CDF of queueing times
	qing_time_l = [r.epoch_started_service - r.epoch_arrived_cluster for r in c.result_l]
	ax = plot.gca()
	add_cdf(qing_time_l, ax, '', next(nice_color))
	plot.xticks(rotation=70)
	plot.ylabel('CDF', fontsize=fontsize)
	plot.xlabel('Queueing time', fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_cdf_Q_ns_{}.png".format(NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	## CDF of inter result times
	ax = plot.gca()
	add_cdf(c.inter_result_time_l, ax, '', next(nice_color)) # drawline_x_l=[1000*self.inter_job_gen_time_rv.mean()]
	plot.xscale('log')
	plot.xticks(rotation=70)
	plot.ylabel('CDF', fontsize=fontsize)
	plot.xlabel('Inter result arrival time', fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_cdf_interResultTime_ns_{}.png".format(NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	log(DEBUG, "done.")

def plot_cluster(cl):
	x_l, y_l = [], []
	epoch_prev, nreqs_prev = None, None
	cum_busy_servers = 0
	for (epoch, nreqs) in cl.epoch_nreqs_l:
		if epoch_prev is not None:
			cum_busy_servers += (epoch - epoch_prev) * min(NUM_SERVER, nreqs_prev)
		epoch_prev = epoch
		nreqs_prev = nreqs
		x_l.append(epoch)
		y_l.append(nreqs)
	avg_load = cum_busy_servers / epoch_prev / NUM_SERVER

	plot.plot(x_l, y_l, color=next(nice_color), marker='_', linestyle='solid', lw=2, mew=2, ms=2)
	# plot.plot(x_l, y_l, color=next(nice_color), marker='*', linestyle='None', lw=2, mew=2, ms=2)

	fontsize = 14
	plot.ylabel('Number of requests in the cluster', fontsize=fontsize)
	plot.xlabel('Time', fontsize=fontsize)
	plot.title('Number of servers= {}, Avg load= {}'.format(cl.num_server, round(avg_load, 2)))
	plot.gcf().set_size_inches(10*2, 4*2)
	plot.savefig("plot_cluster_nreqs_ns_{}.png".format(NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	log(DEBUG, "done.")

def sim_wConstantEndToEndDelay():
	env = simpy.Environment()

	serv_time_rv = DiscreteRV(p_l=[1], v_l=[1])
	slowdown_rv = Dolly() # DiscreteRV(p_l=[0.9, 0.1], v_l=[1, 5]) # DiscreteRV(p_l=[1], v_l=[1])
	cl_id = 'cl'
	cl = Cluster(cl_id, env, slowdown_rv, NUM_SERVER)
	cid = 'c'
	c = Client(cid, env, cl_id, serv_time_rv, num_req_to_recv=1000*NUM_SERVER)
	cl.reg(cid)
	n = Net_wConstantDelay('n', env, [cl, c], delay=0.1) # 0.1 # 2*serv_time_rv.mean()
	env.run(until=c.wait)
	# env.run(until=10)

	plot_client(c)
	plot_cluster(cl)

if __name__ == '__main__':
	sim_wConstantEndToEndDelay()
