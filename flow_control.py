#!/usr/bin/python

from collections import deque
import queue

from tcp import *
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

		# if len(self.cid_q_m[job.cid]) == 0:
		# 	job.ref_epoch = time.time()
		self.cid_q_m[job.cid].append(job)

		log(DEBUG, "pushed", job=job)
		return True

	def pop(self):
		for _ in range(len(self.cid_q_m)):
			q = self.cid_q_m[self.next_cid_to_pop_q[0]]
			self.next_cid_to_pop_q.rotate(-1)
			if len(q) > 0:
				# return q.popleft()
				job = q.popleft()
				# if len(q) > 0:
				# 	q[0].ref_epoch = time.time()
				return job
		return None

class FlowControlClient():
	def __init__(self, _id, client_sid_q):
		self._id = _id
		self.client_sid_q = client_sid_q

		self.sid__delay_controller_m = {}
		self.sid_q = queue.Queue()

		t = threading.Thread(target=self.run, daemon=True)
		t.start()

	def close(self):
		log(DEBUG, "started;")
		self.sid_q.put(-1)
		for _, dc in self.sid__delay_controller_m.items():
			dc.close()
		log(DEBUG, "done.")

	def reg(self, sid, sip):
		if sid not in self.sid__delay_controller_m:
			self.sid__delay_controller_m[sid] = InterJobGenTimeController(sid, self.sid_q)
			log(DEBUG, "reged", sid=sid)
		else:
			log(WARNING, "Already reged!", sid=sid)

	def run(self):
		while True:
			sid = self.sid_q.get(block=True)

			self.client_sid_q.put(sid)

			if sid == -1:
				log(DEBUG, "recved close signal, terminating the loop thread.")
				return

	def update_delay_controller(self, sid, t):
		self.sid__delay_controller_m[sid].update_w_result(t)
		log(DEBUG, "done", sid=sid, t=t)
