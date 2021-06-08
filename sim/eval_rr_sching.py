import os, sys, collections
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import numpy as np

from objs import *
from rvs import *
from debug_utils import *
from plot_utils import *

class Client_NoFC(): # No Flow Control
	def __init__(self, _id, env, cl_id, inter_gen_time_rv, serv_time_rv, num_req_to_recv, out=None):
		self._id = _id
		self.env = env
		self.cl_id = cl_id
		self.inter_gen_time_rv = inter_gen_time_rv
		self.serv_time_rv = serv_time_rv
		self.num_req_to_recv = num_req_to_recv
		self.out = out

		self.result_s = simpy.Store(env)
		self.wait = env.process(self.run_recv())
		self.action_send = env.process(self.run_send())

		self.num_req_sent = 0
		self.num_req_recved = 0

		# self.result_l = []
		self.avg_resp_time = 0

	def __repr__(self):
		return "Client_NoFC(id= {})".format(self._id)

	def put(self, req):
		slog(DEBUG, self.env, self, "recved result", req=req)
		self.result_s.put(req)

	def run_recv(self):
		while True:
			result = yield self.result_s.get()
			# result.epoch_arrived_client = self.env.now
			# self.result_l.append(result)

			T = self.env.now - result.epoch_departed_client
			# self.avg_resp_time = (self.avg_resp_time * self.num_req_recved + T) / (self.num_req_recved + 1)
			self.avg_resp_time = self.avg_resp_time * self.num_req_recved / (self.num_req_recved + 1) + T / (self.num_req_recved + 1)

			self.num_req_recved += 1
			if self.num_req_recved == self.num_req_to_recv:
				slog(DEBUG, self.env, self, "recved the last result")
				return

	def run_send(self):
		while True:
			inter_gen_time = self.inter_gen_time_rv.sample()
			slog(DEBUG, self.env, self, "waiting", inter_gen_time=inter_gen_time)
			yield self.env.timeout(inter_gen_time)

			req = Request(_id=self.num_req_sent, src_id=self._id, dst_id=self.cl_id, serv_time=self.serv_time_rv.sample())
			slog(DEBUG, self.env, self, "sending", req=req)
			req.epoch_departed_client = self.env.now
			self.out.put(req)
			self.num_req_sent += 1

def plot_client(c_l):
	fontsize = 14

	## CDF of req response times
	response_time_l = [r.epoch_arrived_client - r.epoch_departed_client for r in c.result_l]
	plot.axvline(x=c.avg_resp_time_target, ymin=0, ymax=1, label='Target E[T]', color='red')
	# plot.xscale('log')
	plot.xticks(rotation=70)
	plot.ylabel('Pr{T < x}', fontsize=fontsize)
	plot.xlabel('x', fontsize=fontsize)
	plot.legend(fontsize=fontsize)
	plot.gcf().set_size_inches(6, 4)
	plot.savefig("plot_{}_ns{}_cdf_T.png".format(c._id, NUM_SERVER), bbox_inches='tight')
	plot.gcf().clear()

def sim(num_worker, num_client, inter_gen_time_rv, serv_time_rv):
	slowdown_rv = DiscreteRV(p_l=[1], v_l=[1])

	env = simpy.Environment()
	cl = Cluster('cl', env, slowdown_rv, num_worker)
	c_l = []
	for i in range(num_client):
		c = Client_NoFC('c{}'.format(i), env, 'cl', inter_gen_time_rv, serv_time_rv, num_req_to_recv=100)
		c_l.append(c)

	n = Net_wConstantDelay('n', env, [cl, *c_l], delay=0)
	env.run(until=c_l[0].wait)
	# env.run(until=10)

	avg_resp_time_l = [c.avg_resp_time for c in c_l]
	log(INFO, "", avg_resp_time_l=avg_resp_time_l)

	return np.mean(avg_resp_time_l)

def eval_DGc_approx(num_worker, num_client):
	log(DEBUG, "started", num_worker=num_worker, num_client=num_client)
	ES = 1
	serv_time_rv = Exp(mu=1/ES)
	ES2 = serv_time_rv.moment(2)

	arr_rate = lambda ro: 1/ES * num_worker / num_client * ro

	for ro in [0.1, 0.3, 0.6, 0.8]:
	# for ro in [0.8, 0.9]:
		print(">> ro= {}".format(ro))
		ar = arr_rate(ro)
		inter_gen_time_rv = DiscreteRV(p_l=[1], v_l=[1/ar]) # Exp(mu=ar)
		sim_ET = sim(num_worker, num_client, inter_gen_time_rv, serv_time_rv)
		print("sim_ET= {}".format(sim_ET))

		c = num_worker / num_client
		ET = ET_DGc(ar, ES, ES2, c)
		print("ET= {}".format(ET))

	log(DEBUG, "done")

if __name__ == '__main__':
	num_worker, num_client = 2, 2
	eval_DGc_approx(num_worker, num_client)
