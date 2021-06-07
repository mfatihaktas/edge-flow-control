import os, sys, collections
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from objs import *
from rvs import *
from debug_utils import *
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
	plot.axvline(x=c.avg_resp_time_target, ymin=0, ymax=1, label='Target E[T]', color='red')
	# plot.xscale('log')
	plot.xticks(rotation=70)
	plot.ylabel('Pr{T < x}', fontsize=fontsize)
	plot.xlabel('x', fontsize=fontsize)
	plot.legend(fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_{}_ns{}_cdf_T.png".format(c._id, NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	## CDF of queueing times
	qing_time_l = [r.epoch_started_service - r.epoch_arrived_cluster for r in c.result_l]
	ax = plot.gca()
	add_cdf(qing_time_l, ax, '', next(nice_color))
	plot.xticks(rotation=70)
	plot.ylabel('Pr{Queueing time < x}', fontsize=fontsize)
	plot.xlabel('x', fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_{}_ns{}_cdf_Q.png".format(c._id, NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	## CDF of inter result times
	ax = plot.gca()
	add_cdf(c.inter_result_time_l, ax, '', next(nice_color)) # drawline_x_l=[1000*self.inter_job_gen_time_rv.mean()]
	plot.xticks(rotation=70)
	plot.xscale('log')
	plot.ylabel('Pr{Inter result arrival time < x}', fontsize=fontsize)
	plot.xlabel('x', fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_{}_ns{}_cdf_interResultTime.png".format(c._id, NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	log(DEBUG, "done", cid=c._id)

def plot_cluster(cl):
	epoch_l, nreq_l = [], []
	epoch_prev, nreqs_prev = None, None
	cum_weighted_num_busy_servers = 0
	for (epoch, nreqs) in cl.epoch_nreqs_l:
		if epoch_prev is not None:
			cum_weighted_num_busy_servers += (epoch - epoch_prev) * min(NUM_SERVER, nreqs_prev)
		epoch_prev = epoch
		nreqs_prev = nreqs

		epoch_l.append(epoch)
		nreq_l.append(nreqs)
	max_time = epoch_prev
	avg_load = cum_weighted_num_busy_servers / max_time / NUM_SERVER

	fontsize = 14
	## Number of requests over time
	plot.plot(epoch_l, nreq_l, color=next(nice_color), marker='_', linestyle='solid', lw=2, mew=2, ms=2)
	# plot.plot(epoch_l, nreq_l, color=next(nice_color), marker='*', linestyle='None', lw=2, mew=2, ms=2)
	plot.ylabel('Number of requests in the cluster', fontsize=fontsize)
	plot.xlabel('Time', fontsize=fontsize)
	plot.title('Number of servers= {}, Avg load= {}'.format(cl.num_server, round(avg_load, 2)))
	plot.gcf().set_size_inches(10*2, 4*2)
	plot.savefig("plot_ns{}_cluster_nreqs.png".format(NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	## Fraction of time there are x requests in the cluster
	nreq__cum_time_l = list(range(max(nreq_l) + 1)) # collections.defaultdict(0)
	for i in range(len(nreq_l) - 1):
		nreq__cum_time_l[nreq_l[i]] += epoch_l[i + 1] - epoch_l[i]
	nreq__frac_time_l = [t / max_time for t in nreq__cum_time_l]
	ax = plot.gca()
	# add_cdf(nreq_l, ax, '', next(nice_color))
	plot.plot(list(range(len(nreq__frac_time_l))), nreq__frac_time_l, color=next(nice_color), marker='_', linestyle='None', mew=5, ms=10)
	plot.ylabel('Fraction of time number of requests is x', fontsize=fontsize)
	plot.xlabel('x', fontsize=fontsize)
	plot.title('Number of servers= {}, Avg load= {}'.format(cl.num_server, round(avg_load, 2)))
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_ns{}_cdf_cluster_nreqs.png".format(NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

	log(DEBUG, "done", cl_id=cl._id)

def sim_wSingleClient():
	serv_time_rv = DiscreteRV(p_l=[1], v_l=[1])
	slowdown_rv = DiscreteRV(p_l=[0.7, 0.2, 0.1], v_l=[1, 3, 6]) # DiscreteRV(p_l=[0.9, 0.1], v_l=[1, 5]) # Dolly() # DiscreteRV(p_l=[1], v_l=[1])

	env = simpy.Environment()
	cl = Cluster('cl', env, slowdown_rv, NUM_SERVER)
	avg_resp_time_target = 1.6 * serv_time_rv.mean() * slowdown_rv.mean()
	c = Client('c', env, 'cl', serv_time_rv, avg_resp_time_target, num_req_to_recv=2000*NUM_SERVER)
	n = Net_wConstantDelay('n', env, [cl, c], delay=0.1) # 0.1 # 2*serv_time_rv.mean()
	env.run(until=c.wait)
	# env.run(until=10)

	plot_client(c)
	plot_cluster(cl)

	log(DEBUG, "done")

def sim_wMultiClient(num_client):
	serv_time_rv = DiscreteRV(p_l=[1], v_l=[1])
	slowdown_rv = DiscreteRV(p_l=[0.7, 0.2, 0.1], v_l=[1, 3, 6]) # Dolly() # DiscreteRV(p_l=[1], v_l=[1]) # DiscreteRV(p_l=[0.9, 0.1], v_l=[1, 5])

	env = simpy.Environment()
	cl = Cluster('cl', env, slowdown_rv, NUM_SERVER)
	c_l = []
	for i in range(num_client):
		cid= 'c{}'.format(i)
		avg_resp_time_target = 1.6 * serv_time_rv.mean() * slowdown_rv.mean()
		c = Client(cid, env, 'cl', serv_time_rv, avg_resp_time_target, num_req_to_recv=1000*NUM_SERVER)
		c_l.append(c)

	n = Net_wConstantDelay('n', env, [cl, *c_l], delay=0.1)
	env.run(until=c_l[0].wait)
	# env.run(until=10)

	for i in range(num_client):
		plot_client(c_l[i])
	plot_cluster(cl)

	log(DEBUG, "done")

if __name__ == '__main__':
	log_to_file('sim.log')

	# sim_wSingleClient()
	sim_wMultiClient(num_client=2)
