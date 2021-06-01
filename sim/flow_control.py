import simpy
from collections import deque

from debug_utils import *

class FlowControl():
	def __init__(self, env, token_s):
		self.env = env
		self.token_s = token_s

		self.syncer = simpy.Store(env)
		self.inter_req_time = None
		self.coeff = 0.5

		self.action = env.process(self.run())

	def __repr__(self):
		return "FlowControl(coeff= {})".format(self.coeff)

	def update(self, result):
		cluster_time = result.epoch_departed_cluster - result.epoch_arrived_cluster # result.serv_time
		if self.inter_req_time is None:
			slog(DEBUG, self.env, self, "recved first result")
			self.inter_req_time = cluster_time
			self.syncer.put(1)
		else:
			if cluster_time > self.inter_req_time:
				self.inter_req_time *= 2
			else:
				self.inter_req_time = (1 - self.coeff) * self.inter_req_time + self.coeff * cluster_time
		log(DEBUG, "done", inter_req_time=self.inter_req_time, cluster_time=cluster_time)

	def run(self):
		while True:
			if self.inter_req_time is None:
				slog(DEBUG, self.env, self, "waiting for first result")
				self.token_s.put(1)
				yield self.syncer.get()
				self.token_s.put(1)
			else:
				slog(DEBUG, self.env, self, "waiting", t=self.inter_req_time)
				yield self.env.timeout(self.inter_req_time)
				self.token_s.put(1)

class FlowControl_AvgServTime():
	def __init__(self, env, token_s):
		self.env = env
		self.token_s = token_s

		self.syncer = simpy.Store(env)
		self.inter_req_time = None

		self.result_q = deque(maxlen=100)
		self.cum_serv_time = 0

		self.action = env.process(self.run())

	def __repr__(self):
		return "FlowControl_AvgServTime"

	def update(self, result):
		log(DEBUG, "started", inter_req_time=self.inter_req_time, serv_time=result.serv_time)

		self.cum_serv_time += result.serv_time
		if len(self.result_q) == self.result_q.maxlen:
			self.cum_serv_time -= self.result_q[0].serv_time
		self.result_q.append(result)

		should_sync = self.inter_req_time is None
		self.inter_req_time = self.cum_serv_time / len(self.result_q) / result.num_server_fair_share / 0.8

		if should_sync:
			slog(DEBUG, self.env, self, "recved first result")
			self.syncer.put(1)

		log(DEBUG, "done", inter_req_time=self.inter_req_time)

	def run(self):
		while True:
			if self.inter_req_time is None:
				slog(DEBUG, self.env, self, "waiting for first result")
				self.token_s.put(1)
				yield self.syncer.get()
				self.token_s.put(1)
			else:
				slog(DEBUG, self.env, self, "waiting", inter_req_time=self.inter_req_time)
				yield self.env.timeout(self.inter_req_time)
				self.token_s.put(1)
