#!/usr/bin/python

from collections import deque
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

		self.cid_q_m[job.cid].append(job)
		log(DEBUG, "pushed", job=job)
		return True

	def pop(self):
		for _ in range(len(self.cid_q_m)):
			q = self.cid_q_m[self.next_cid_to_pop_q[0]]
			self.next_cid_to_pop_q.rotate(-1)
			if len(q) > 0:
				return q.popleft()

		return None

class FlowControlClient():
	def __init__(self, _id, max_delay):
		self._id = _id
		self.max_delay = max_delay

		self.tcp_client = TCPClient(_id)

		self.sid__delay_controller_m = {}
		self.next_sid_to_push_q = deque()

		self.num_jobs_pushed = 0
		self.probe_info_m = {}
		self.probe_on_air = False

	def close(self):
		self.tcp_client.close()

	def reg(self, sid, sip):
		if sid not in self.sid__delay_controller_m:
			self.tcp_client.reg(sid, sip)

			self.sid__delay_controller_m[sid] = AIMDController(sid, self.max_delay)
			self.next_sid_to_push_q.append(sid)
			log(DEBUG, "reged", sid=sid)

	def push(self, job):
		log(DEBUG, "recved", job=job)

		for _ in range(len(self.sid__delay_controller_m)):
			sid = self.next_sid_to_push_q[0]
			self.next_sid_to_push_q.rotate(-1)
			delay_controller = self.sid__delay_controller_m[sid]
			if delay_controller.put():
				msg = Msg(_id=self.num_jobs_pushed, payload=job, dst_id=sid)
				self.tcp_client.send(msg)
				self.num_jobs_pushed += 1
				log(DEBUG, "sent", job=job, sid=sid)
				return True
			elif delay_controller.q_len_limit == 0 and self.probe_on_air == False:
				probe = Probe(_id=job._id, cid=job.cid)
				msg = Msg(_id=self.num_jobs_pushed, payload=probe, dst_id=sid)
				self.tcp_client.send(msg)

				self.probe_info_m[probe] = {'sent_time': time.time()}
				self.probe_on_air = True
				log(DEBUG, "sent", probe=probe)

		log(DEBUG, "dropping", job=job)
		return False

	def update_delay_controller(self, sid, t):
		self.sid__delay_controller_m[sid].update(t)
		log(DEBUG, "done", sid=sid, t=t)

	def handle_probe(self, sid, probe):
		check(probe in self.probe_info_m, "Probe has not been entered probe_info_m.")
		log(DEBUG, "handling", sid=sid, probe=probe)
		info = self.probe_info_m[probe]
		t = time.time() - info['sent_time']
		info.update(
			{
				'fate': 'returned',
				'sid': sid,
				'T': 1000*t
			})

		self.update_delay_controller(sid, t)
		self.probe_on_air = False
