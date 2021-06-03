#!/usr/bin/python

from collections import deque
import queue

from delay_control import *

# cid : client id

class FlowControlServer():
	def __init__(self):
		self.cid_q_m = {}
		self.next_cid_to_pop_q = deque()

	def reg(self, cid):
		if cid not in self.cid_q_m:
			self.cid_q_m[cid] = deque()
			self.next_cid_to_pop_q.append(cid)
			log(DEBUG, "reged", cid=cid)

	def push(self, job):
		check(job.cid in self.cid_q_m, "Job is from an unknown client", job=job)
		self.cid_q_m[job.cid].append(job)
		log(DEBUG, "pushed", job=job)

	def pop(self):
		for _ in range(len(self.cid_q_m)):
			q = self.cid_q_m[self.next_cid_to_pop_q[0]]
			self.next_cid_to_pop_q.rotate(-1)
			if len(q) > 0:
				return q.popleft()
		return None

class FlowControlClient():
	def __init__(self, _id, client_sid_q, avg_load_target=0.8):
		self._id = _id
		self.client_sid_q = client_sid_q
		self.avg_load_target = avg_load_target

		self.sid_controller_m = {}
		self.sid_q = queue.Queue()

		t = threading.Thread(target=self.run, daemon=True)
		t.start()

	def __repr__(self):
		return "FlowControlClient(id= {})".format(self._id)

	def close(self):
		log(DEBUG, "started;")
		self.sid_q.put(-1)
		for _, dc in self.sid_controller_m.items():
			dc.close()
		log(DEBUG, "done.")

	def reg(self, sid, sip):
		if sid not in self.sid_controller_m:
			self.sid_controller_m[sid] = InterJobGenTimeController_GGn(sid, self.sid_q, self.avg_load_target)
			# self.sid_controller_m[sid] = InterJobGenTimeController_ExpAvg(sid, self.sid_q)
			log(DEBUG, "reged", sid=sid)
		else:
			log(WARNING, "Already reged!", sid=sid)

	def run(self):
		log(DEBUG, "started", what=self)
		while True:
			log(DEBUG, "waiting for sid", what=self)
			sid = self.sid_q.get(block=True)

			self.client_sid_q.put(sid)

			if sid == -1:
				log(DEBUG, "recved close signal, terminating the loop thread")
				return

	def update(self, sid, result):
		self.sid_controller_m[sid].update(result)
		log(DEBUG, "done", sid=sid)
