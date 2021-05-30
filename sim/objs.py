from flow_control import *
from debug_utils import *

class Request():
	def __init__(self, _id, src_id, dst_id, serv_time):
		self._id = _id
		self.src_id = src_id
		self.dst_id = dst_id
		self.serv_time = serv_time

		self.epoch_departed_client = None
		self.epoch_arrived_net = None
		self.epoch_arrived_server = None
		self.epoch_departed_server = None

	def __repr__(self):
		return "Request(id= {}, src_id= {}, dst_id= {}, serv_time= {})".format(self._id, self.src_id, self.dst_id, self.serv_time)

class Client():
	def __init__(self, _id, env, serv_time_rv, num_req_to_recv, sid, out=None):
		self._id = _id
		self.env = env
		self.serv_time_rv = serv_time_rv
		self.num_req_to_recv = num_req_to_recv
		self.sid = sid
		self.out = out

		self.token_s = simpy.Store(env)
		self.fc = FlowControl(env, self.token_s)

		self.result_s = simpy.Store(env)
		self.wait = env.process(self.run_recv())
		self.action_send = env.process(self.run_send())

		self.num_req_sent = 0
		self.num_req_recved = 0

		self.last_time_result_recved = env.now
		self.inter_result_time_l = []
		self.response_time_l = []

	def __repr__(self):
		return "Client(_id= {})".format(self._id)

	def put(self, req):
		slog(DEBUG, self.env, self, "recved", req=req)
		self.result_s.put(req)

	def run_recv(self):
		while True:
			result = yield self.result_s.get()

			self.inter_result_time_l.append(self.env.now - self.last_time_result_recved)
			self.last_time_result_recved = self.env.now

			self.response_time_l.append(self.env.now - result.epoch_departed_client)

			self.num_req_recved += 1
			if self.num_req_recved == self.num_req_to_recv:
				slog(DEBUG, self.env, self, "recved the last result")
				return
			self.fc.update(result)

	def run_send(self):
		while True:
			yield self.token_s.get()

			req = Request(_id=self.num_req_sent, src_id=self._id, dst_id=self.sid, serv_time=self.serv_time_rv.sample())
			slog(DEBUG, self.env, self, "sending", req=req)
			req.epoch_departed_client = self.env.now
			self.out.put(req)
			self.num_req_sent += 1

class Server():
	def __init__(self, _id, env, slowdown_rv, out=None):
		self._id = _id
		self.env = env
		self.slowdown_rv = slowdown_rv
		self.out = out

		self.req_s = simpy.Store(env)
		self.action = env.process(self.run())
		self.req_in_service = None

		self.epoch_qlen_l = []

	def __repr__(self):
		return "Server(_id= {})".format(self._id)

	def put(self, req):
		slog(DEBUG, self.env, self, "recved", req=req)
		self.req_s.put(req)

		self.epoch_qlen_l.append((self.env.now, len(self.req_s.items) + int(self.req_in_service == None)))

	def run(self):
		while True:
			req = yield self.req_s.get()
			self.req_in_service = req

			s = self.slowdown_rv.sample()
			slog(DEBUG, self.env, self, "started serving", slowdown=s, serv_time=req.serv_time)
			yield self.env.timeout(s * req.serv_time)
			slog(DEBUG, self.env, self, "finished serving", req=req)

			req.src_id, req.dst_id = req.dst_id, req.src_id
			self.out.put(req)
			self.req_in_service = None

			self.epoch_qlen_l.append((self.env.now, len(self.req_s.items)))

class Net():
	def __init__(self, _id, env, cs_l):
		self._id = _id
		self.env = env

		self.id_out_m = {}
		for cs in cs_l:
			cs.out = self
			self.id_out_m[cs._id] = cs

		self.req_s = simpy.Store(env)

	def __repr__(self):
		return "Net(id= {})".format(self._id)

	def put(self, req):
		slog(DEBUG, self.env, self, "recved", req=req)
		req.epoch_arrived_net = self.env.now
		self.req_s.put(req)

class Net_wConstantDelay(Net):
	def __init__(self, _id, env, cs_l, delay):
		super().__init__(_id, env, cs_l)
		self.delay = delay

		self.action = env.process(self.run())

	def run(self):
		while True:
			req = yield self.req_s.get()

			t = self.delay - (self.env.now - req.epoch_arrived_net)
			if t > 0:
				slog(DEBUG, self.env, self, "delaying", req=req, t=t)
				yield self.env.timeout(t)

			self.id_out_m[req.dst_id].put(req)
