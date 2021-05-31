import simpy

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
		if self.inter_req_time is None:
			slog(DEBUG, self.env, self, "recved first result")
			self.inter_req_time = result.serv_time
			self.syncer.put(1)
		else:
			if result.serv_time > self.inter_req_time:
				self.inter_req_time *= 2
			else:
				self.inter_req_time = (1 - self.coeff) * self.inter_req_time + self.coeff * result.serv_time
		log(DEBUG, "done", inter_req_time=self.inter_req_time, serv_time=result.serv_time)

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
