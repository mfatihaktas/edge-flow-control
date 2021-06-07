import simpy
from collections import deque
# from simple_pid import PID

from debug_utils import *
from model import *

class FlowControl():
	def __init__(self, env, token_s):
		self.env = env
		self.token_s = token_s

class FlowControl_ExpAvg_MD(FlowControl): # Exponential Averaging, Multiplicative Decrease
	def __init__(self, env, token_s):
		super().__init__(env, token_s)

		self.syncer = simpy.Store(env)
		self.inter_req_time = None
		self.coeff = 0.5

		self.action = env.process(self.run())

	def __repr__(self):
		return "FlowControl_ExpAvg_MD(coeff= {})".format(self.coeff)

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

class FlowControl_GGn(FlowControl):
	def __init__(self, env, token_s, avg_load_target):
		super().__init__(env, token_s)
		self.avg_load_target = avg_load_target

		self.syncer = simpy.Store(env)
		self.inter_req_time = None

		self.result_q = deque(maxlen=100)
		self.cum_serv_time = 0

		self.action = env.process(self.run())

	def __repr__(self):
		return "FlowControl_GGn(avg_load_target= {})".format(self.avg_load_target)

	def update(self, result):
		log(DEBUG, "started", inter_req_time=self.inter_req_time, serv_time=result.serv_time)

		self.cum_serv_time += result.serv_time
		if len(self.result_q) == self.result_q.maxlen:
			self.cum_serv_time -= self.result_q[0].serv_time
		self.result_q.append(result)

		should_sync = self.inter_req_time is None
		self.inter_req_time = self.cum_serv_time / len(self.result_q) / result.num_server_share / self.avg_load_target

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

class FlowControl_GGn_AvgRespTimeTarget(FlowControl):
	def __init__(self, env, token_s, avg_resp_time_target):
		super().__init__(env, token_s)
		self.avg_resp_time_target = avg_resp_time_target

		self.syncer = simpy.Store(env)
		self.inter_req_time = None

		self.inter_req_time_q = deque(maxlen=10)
		self.result_q = deque(maxlen=100)
		self.cum_serv_time = 0
		self.cum_serv_time_sqr = 0
		self.avg_resp_time = 0

		# self.pid = PID(1, 0.1, 0.05, setpoint=avg_resp_time_target)
		# self.pid.output_limits = (0.1, 10)

		self.action = env.process(self.run())

	def __repr__(self):
		return "FlowControl_GGn_AvgRespTimeTarget(avg_resp_time_target= {})".format(self.avg_resp_time_target)

	def update(self, result):
		log(DEBUG, "started", inter_req_time=self.inter_req_time, serv_time=result.serv_time)

		self.cum_serv_time += result.serv_time
		self.cum_serv_time_sqr += result.serv_time**2
		if len(self.result_q) == self.result_q.maxlen:
			self.cum_serv_time -= self.result_q[0].serv_time
			self.cum_serv_time_sqr -= self.result_q[0].serv_time**2
		self.result_q.append(result)

		should_sync = self.inter_req_time is None
		ES = self.cum_serv_time / len(self.result_q)
		if len(self.result_q) < 20 or self.avg_resp_time_target <= ES:
			self.inter_req_time = None
		else:
			ES2 = self.cum_serv_time_sqr / len(self.result_q)
			if ES == ES2:
				self.inter_req_time = None
			else:
				self.inter_req_time = 1 / ar_DGc_forGivenET(ES, ES2, result.num_server_share, self.avg_resp_time_target)
				# EX = sum(self.inter_req_time_q) / len(self.inter_req_time_q)
				# EX2 = sum(t**2 for t in self.inter_req_time_q) / len(self.inter_req_time_q)
				# self.inter_req_time = 1 / ar_GGc_forGivenET(EX, EX2, ES, ES2, result.num_server_share, self.avg_resp_time_target)

				self.avg_resp_time = self.avg_resp_time * 0.8 + (result.epoch_departed_cluster - result.epoch_arrived_cluster) * 0.2

				corrector = 0.3 * (self.avg_resp_time - self.avg_resp_time_target)
				max_ = 10
				if abs(corrector) > max_:
					corrector = max_ if corrector > 0 else -max_
				if self.inter_req_time + corrector < 0.1:
					corrector = 0
				self.inter_req_time += corrector
				log(DEBUG, "", corrector=corrector, inter_req_time=self.inter_req_time, avg_resp_time=self.avg_resp_time)

				# control_input = self.pid(self.avg_resp_time)
				# log(DEBUG, "", control_input=control_input, inter_req_time=self.inter_req_time, avg_resp_time=self.avg_resp_time)
				# # self.inter_req_time = control_input
				# self.inter_req_time += control_input

		if should_sync:
			slog(DEBUG, self.env, self, "recved first result")
			self.syncer.put(1)

		log(DEBUG, "done", inter_req_time=self.inter_req_time)

	def run(self):
		## First req
		self.token_s.put(1)
		last_time_req_sent = self.env.now
		while True:
			if self.inter_req_time is None:
				slog(DEBUG, self.env, self, "waiting for result")
				yield self.syncer.get()
				self.token_s.put(1)
			else:
				slog(DEBUG, self.env, self, "sleeping", inter_req_time=self.inter_req_time)
				yield self.env.timeout(self.inter_req_time)
				self.token_s.put(1)

			self.inter_req_time_q.append(self.env.now - last_time_req_sent)
			last_time_req_sent = self.env.now
