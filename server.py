import threading, time, sys, getopt, json, queue, nslookup

from config import *
from debug_utils import *
from commer import CommerOnServer
from flow_control import FlowControlServer

def get_wip_l(dns_sip="1.1.1.1"):
	query = nslookup.Nslookup(dns_servers=[dns_sip])
	record = query.dns_lookup(domain)
	log(DEBUG, "", dns_response=record.response_full, dns_answer=record.answer)

	record = query.soa_lookup(domain)
	log(DEBUG, "", soa_response=record.response_full, soa_answer=record.answer)

class Server():
	def __init__(self, _id, wip_l=None, max_num_jobs_per_worker=1):
		self._id = _id
		self.wip_l = wip_l if wip_l is None else get_wip_l()

		self.commer = CommerOnServer(_id, self.handle_msg)

		self.fc_server = FlowControlServer()

		self.wid_q = queue.Queue()
		for i in range(len(wip_l)):
			for _ in range(max_num_jobs_per_worker):
				self.wid_q.put(i)

		self.wait_for_ajob = threading.Condition()
		self.is_waiting_for_ajob = False
		t = threading.Thread(target=self.run, daemon=True)
		t.start()
		t.join()

	def handle_msg(self, msg):
		log(DEBUG, "handling", msg=msg)
		cid = msg.src_id
		self.fc_server.reg(cid)

		payload = msg.payload
		check(payload.is_job() or payload.is_probe(), "Msg should contain a job or probe.")
		self.put(payload)

	# TODO: Move from condition to blocking queue
	def put(self, job):
		log(DEBUG, "recved", job=job)

		job.reached_server_epoch = time.time()
		self.fc_server.push(job)
		if self.is_waiting_for_ajob:
			with self.wait_for_ajob:
				self.wait_for_ajob.notifyAll()
				log(DEBUG, "notified.")

	def run(self):
		while True:
			job = self.fc_server.pop()
			if job is None:
				self.is_waiting_for_ajob = True
				with self.wait_for_ajob:
					log(DEBUG, "waiting for a job")
					self.wait_for_ajob.wait()
					log(DEBUG, "a job has arrived!")
					self.is_waiting_for_ajob = False
				continue

			if job.is_job():
				wid = self.wid_q.get(block=True)
				t = threading.Thread(target=self.send_job_recv_result_return_to_client, args=(wid, job), daemon=True)
				t.start()
			elif job.is_probe():
				msg = Msg(job._id, payload=job) # return the probe back to the client
				self.commer.send_msg(job.cid, msg)

	def send_job_recv_result_return_to_client(self, wid, job):
		log(DEBUG, "started;", wid=wid, job_id=job._id)
		result = self.commer.send_job_recv_result(self.wip_l[wid], job)

		result.serv_time = time.time() - job.reached_server_epoch
		result.departed_server_epoch = time.time()
		msg = Msg(job._id, payload=result, dst_id=job.cid)
		self.commer.send_msg(job.cid, msg)

		self.wid_q.put(wid)
		log(DEBUG, "done.", wid=wid, job_id=job._id)

def parse_argv(argv):
	m = {}
	try:
		opts, args = getopt.getopt(argv, '', ['i=', 'wip_l='])
	except getopt.GetoptError:
		assert_("Wrong args;", opts=opts, args=args)

	for opt, arg in opts:
		if opt == '--i':
			m['i'] = arg
		elif opt == '--wip_l':
			m['wip_l'] = json.loads(arg)
		else:
			assert_("Unexpected opt= {}, arg= {}".format(opt, arg))

	return m

def run(argv):
	m = parse_argv(argv)
	_id = 's' + m['i']
	log_to_file('{}.log'.format(_id))

	s = Server(_id, m['wip_l'])
	# input("Enter to finish...\n")
	# sys.exit()

def test(argv):
	m = parse_argv(argv)
	_id = 's' + m['i']
	log_to_file('{}.log'.format(_id))

	s = Server(_id, m['wip_l'])
	input("Enter to finish...\n")
	sys.exit()

if __name__ == '__main__':
	if TEST:
		test(sys.argv[1:])
	else:
		run(sys.argv[1:])
