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

		self.job_q = queue.Queue()
		self.tcp_client = TCPClient(_id)

		self.sid__delay_controller_m = {}
		self.sid_q = queue.Queue()
		self.sid__num_probe_m = {}
		self.num_probes_sent = 0

		self.num_jobs_pushed = 0
		self.probe_info_m = {}

		t = threading.Thread(target=self.run, daemon=True)
		t.start()

	def close(self):
		self.tcp_client.close()

	def reg(self, sid, sip):
		if sid not in self.sid__delay_controller_m:
			self.tcp_client.reg(sid, sip)
			self.sid__delay_controller_m[sid] = AIMDController(sid, self.max_delay, self)
			self.sid__num_probe_m[sid] = 0
			log(DEBUG, "reged", sid=sid)

	def put_sid(self, sid):
		log(DEBUG, "recved", sid=sid)
		self.sid_q.put(sid, block=False)

	def put_job(self, job):
		log(DEBUG, "recved", job=job)
		self.job_q.put(job, block=False)

	def send_probe(self, sid):
		probe = Probe(_id=num_probes_sent, cid=self._id)
		msg = Msg(_id=self.num_probes_sent, payload=probe, dst_id=sid)
		self.tcp_client.send(msg)

		self.probe_info_m[probe] = {'sent_time': time.time()}

		self.num_probes_sent += 1
		log(DEBUG, "sent", probe=probe)

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

		self.sid__delay_controller_m[sid].update_w_probe(t)
		self.probe_on_air = False

	def run(self):
		while True:
			job = self.job_q.get(block=True)
			sid = self.sid_q.get(block=True)

			msg = Msg(_id=self.num_jobs_pushed, payload=job, dst_id=sid)
			self.tcp_client.send(msg)
			self.num_jobs_pushed += 1
			log(DEBUG, "sent", job=job, sid=sid)

	def update_delay_controller(self, sid, t):
		self.sid__delay_controller_m[sid].update_w_result(t)
		log(DEBUG, "done", sid=sid, t=t)
