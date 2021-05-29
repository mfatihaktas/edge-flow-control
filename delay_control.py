import threading, time

from debug_utils import *

class AIMDController():
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

class InterJobGenTimeController():
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
		log(DEBUG, "started;")
		self.on = False
		log(DEBUG, "done.")

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
		log(DEBUG, "started;", job_serv_time=job_serv_time)
		self.num_jobs_on_fly -= 1

		if self.inter_serv_time is None:
			self.inter_serv_time = job_serv_time
		else:
			self.inter_serv_time = self.a*job_serv_time + (1 - self.a)*self.inter_serv_time

		log(DEBUG, "done.", inter_serv_time=self.inter_serv_time, num_jobs_on_fly=self.num_jobs_on_fly)

	def put(self):
		self.num_jobs_on_fly += 1
		self.fc_client_sid_q.put(self._id)
