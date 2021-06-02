import random
from collections import deque

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
		self.epoch_arrived_cluster = None
		self.epoch_started_service = None
		self.epoch_departed_cluster = None
		self.epoch_arrived_client = None

		self.num_server_fair_share = None

	def __repr__(self):
		return "Request(id= {}, src_id= {}, dst_id= {}, serv_time= {})".format(self._id, self.src_id, self.dst_id, self.serv_time)

class Client():
	def __init__(self, _id, env, cl_id, serv_time_rv, num_req_to_recv, out=None):
		self._id = _id
		self.env = env
		self.cl_id = cl_id
		self.serv_time_rv = serv_time_rv
		self.num_req_to_recv = num_req_to_recv
		self.out = out

		self.token_s = simpy.Store(env)
		self.fc = FlowControl_GGn(env, self.token_s, avg_load_target=0.8)

		self.result_s = simpy.Store(env)
		self.wait = env.process(self.run_recv())
		self.action_send = env.process(self.run_send())

		self.num_req_sent = 0
		self.num_req_recved = 0

		self.last_time_result_recved = env.now
		self.inter_result_time_l = []
		self.result_l = []

	def __repr__(self):
		return "Client(_id= {})".format(self._id)

	def put(self, req):
		slog(DEBUG, self.env, self, "recved", req=req)
		self.result_s.put(req)

	def run_recv(self):
		while True:
			result = yield self.result_s.get()
			result.epoch_arrived_client = self.env.now

			self.inter_result_time_l.append(self.env.now - self.last_time_result_recved)
			self.last_time_result_recved = self.env.now
			self.result_l.append(result)

			self.num_req_recved += 1
			if self.num_req_recved == self.num_req_to_recv:
				slog(DEBUG, self.env, self, "recved the last result")
				return
			self.fc.update(result)

	def run_send(self):
		while True:
			yield self.token_s.get()
			yield self.env.timeout(random.uniform(0, 1) / 100)

			req = Request(_id=self.num_req_sent, src_id=self._id, dst_id=self.cl_id, serv_time=self.serv_time_rv.sample())
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
		self.is_serving = False

	def __repr__(self):
		return "Server(_id= {})".format(self._id)

	def put(self, req):
		slog(DEBUG, self.env, self, "recved", req=req)
		self.req_s.put(req)

	def num_reqs(self):
		return len(self.req_s.items) + int(self.is_serving)

	def run(self):
		while True:
			req = yield self.req_s.get()
			req.epoch_started_service = self.env.now

			self.is_serving = True
			s = self.slowdown_rv.sample()
			t = s * req.serv_time
			slog(DEBUG, self.env, self, "started serving", slowdown=s, req=req, t=t)
			yield self.env.timeout(t)
			slog(DEBUG, self.env, self, "finished serving", req_id=req._id)

			req.serv_time = t
			self.is_serving = False
			self.out.put_result(self._id, req)

class Cluster():
	def __init__(self, _id, env, slowdown_rv, num_server, out=None):
		self._id = _id
		self.env = env
		self.num_server = num_server
		self.out = out

		self.cid_q_m = {}
		self.next_cid_to_pop_q = deque()
		self.server_l = [Server(i, env, slowdown_rv, out=self) for i in range(num_server)]

		self.sid_s = simpy.Store(env)
		for i in range(num_server):
			self.sid_s.put(i)

		self.waiting_for_req = True
		self.syncer_s = simpy.Store(env)
		self.result_s = simpy.Store(env)

		self.action_handle_reqs = env.process(self.run_handle_reqs())
		self.action_handle_results = env.process(self.run_handle_results())

		self.epoch_nreqs_l = []

	def __repr__(self):
		return "Cluster(_id= {})".format(self._id)

	def reg(self, cid):
		if cid not in self.cid_q_m:
			self.cid_q_m[cid] = deque()
			self.next_cid_to_pop_q.append(cid)
			log(DEBUG, "reged", cid=cid)

	def num_reqs(self):
		return sum(len(q) for _, q in self.cid_q_m.items()) + sum(s.num_reqs() for s in self.server_l)

	def record_num_reqs(self):
		self.epoch_nreqs_l.append((self.env.now, self.num_reqs()))

	def put(self, req):
		slog(DEBUG, self.env, self, "recved", req=req)
		req.epoch_arrived_cluster = self.env.now

		if req.src_id not in self.cid_q_m:
			self.reg(req.src_id)
		self.cid_q_m[req.src_id].append(req)

		if self.waiting_for_req:
			self.syncer_s.put(1)
			# yield self.env.timeout(0.0001)

	def put_result(self, sid, result):
		slog(DEBUG, self.env, self, "recved", result=result)
		self.sid_s.put(sid)
		self.result_s.put(result)

	def next_req(self):
		for _ in range(len(self.cid_q_m)):
			q = self.cid_q_m[self.next_cid_to_pop_q[0]]
			self.next_cid_to_pop_q.rotate(-1)
			if len(q) > 0:
				return q.popleft()
		return None

	def run_handle_reqs(self):
		while True:
			sid = yield self.sid_s.get()

			req = self.next_req()
			if req is None:
				slog(DEBUG, self.env, self, "waiting for a req")
				self.waiting_for_req = True
				yield self.syncer_s.get()
				self.waiting_for_req = False
				slog(DEBUG, self.env, self, "recved a req")
				req = self.next_req()
				check(req is not None, "A req must have been recved")

			self.server_l[sid].put(req)
			self.record_num_reqs()

	def run_handle_results(self):
		while True:
			result = yield self.result_s.get()
			result.src_id, result.dst_id = result.dst_id, result.src_id
			result.epoch_departed_cluster = self.env.now
			result.num_server_fair_share = self.num_server / len(self.cid_q_m)
			self.out.put(result)

			self.record_num_reqs()

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
