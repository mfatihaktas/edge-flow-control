import threading, time, queue, collections

from debug_utils import *

class InterJobGenTimeController_ExpAvg_AIMD():
	def __init__(self, _id, max_delay, fc_client):
		self._id = _id
		self.max_delay = max_delay
		self.fc_client = fc_client

		self.q_len_limit = 2
		self.q_len = 0
		self.q_len_max = 2
		self.avg_delay = 0
		self.a = 0.5

		self.put() # to put the initial token in sid_q

	def update_common(self, t): # t: turnaround time
		self.q_len = max(0, self.q_len - 1)

		if self.avg_delay == 0:
			self.avg_delay = t
		else:
			self.avg_delay = (1 - self.a)*self.avg_delay + self.a*t

		if self.avg_delay > self.max_delay:
			self.q_len_limit = self.q_len_limit*1/2
			log(WARNING, "reduced q_len_limit; id= {}".format(self._id))
		else:
			if self.q_len_limit < 2*self.q_len_max:
				self.q_len_limit += 1/self.q_len_limit if self.q_len_limit > 1 else 1
				log(WARNING, "inced q_len_limit; id= {}".format(self._id))
		log(DEBUG, "id= {}".format(self._id), avg_delay=self.avg_delay, max_delay=self.max_delay, q_len_limit=self.q_len_limit, q_len=self.q_len)

	def update_w_result(self, t):
		self.update_common(t)

		if self.q_len == 0 or (self.q_len < self.q_len_limit):
			self.put()
		elif self.q_len_limit == 0:
			self.fc_client.send_probe(sid)

	def update_w_probe(self, t):
		self.update_common(t)

	def put(self):
		self.fc_client.put_sid(self._id)
		self.q_len += 1
		self.q_len_max = max(self.q_len_max, self.q_len)

class InterJobGenTimeController_ExpAvg():
	def __init__(self, _id, fc_client_sid_q):
		self._id = _id
		self.fc_client_sid_q = fc_client_sid_q

		self.inter_serv_time = None
		self.a = 0.5
		self.num_jobs_on_fly = 0

		self.on = True

		t = threading.Thread(target=self.run, daemon=True)
		t.start()
		self.put()

	def close(self):
		log(DEBUG, "started")
		self.on = False
		log(DEBUG, "done")

	def run(self):
		while self.on:
			if self.inter_serv_time is None and self.num_jobs_on_fly > 4:
				# time.sleep(1)
				time.sleep(0.1)
			else:
				# time.sleep(2)
				time.sleep(self.inter_serv_time)
				self.put()

	def update_w_result(self, job_serv_time):
		log(DEBUG, "started", job_serv_time=job_serv_time)
		self.num_jobs_on_fly -= 1

		if self.inter_serv_time is None:
			self.inter_serv_time = job_serv_time
		else:
			self.inter_serv_time = self.a*job_serv_time + (1 - self.a)*self.inter_serv_time

		log(DEBUG, "done", inter_serv_time=self.inter_serv_time, num_jobs_on_fly=self.num_jobs_on_fly)

	def put(self):
		self.num_jobs_on_fly += 1
		self.fc_client_sid_q.put(self._id)

class InterJobGenTimeController_GGn():
	def __init__(self, sid, fc_client_sid_q, avg_load_target):
		self.sid = sid
		self.fc_client_sid_q = fc_client_sid_q
		self.avg_load_target = avg_load_target

		self.inter_req_time = None

		self.result_q = collections.deque(maxlen=100)
		self.cum_serv_time = 0

		self.on = True
		self.syncer = queue.Queue()
		t = threading.Thread(target=self.run, daemon=True)
		t.start()

	def __repr__(self):
		return "InterJobGenTimeController_GGn(sid= {}, avg_load_target= {})".format(self.sid, self.avg_load_target)

	def close(self):
		log(DEBUG, "started")
		self.on = False
		log(DEBUG, "done")

	def update(self, result):
		log(DEBUG, "started", inter_req_time=self.inter_req_time, serv_time=result.serv_time)

		self.cum_serv_time += result.serv_time
		if len(self.result_q) == self.result_q.maxlen:
			self.cum_serv_time -= self.result_q[0].serv_time
		self.result_q.append(result)

		should_sync = self.inter_req_time is None
		self.inter_req_time = self.cum_serv_time / len(self.result_q) / result.num_server_fair_share / self.avg_load_target

		if should_sync:
			log(DEBUG, "recved first result")
			self.syncer.put(1)

		log(DEBUG, "done", inter_req_time=self.inter_req_time)

	def run(self):
		log(DEBUG, "started", what=self)
		while self.on:
			if self.inter_req_time is None:
				log(DEBUG, "putting first sid", sid=self.sid)
				self.fc_client_sid_q.put(self.sid)
				log(DEBUG, "waiting for first result", sid=self.sid)
				self.syncer.get(block=True)
				self.fc_client_sid_q.put(self.sid)
			else:
				log(DEBUG, "waiting", inter_req_time=self.inter_req_time, sid=self.sid)
				time.sleep(self.inter_req_time)
				self.fc_client_sid_q.put(self.sid)
