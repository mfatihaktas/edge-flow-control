import threading, time, sys, getopt, json, queue, nslookup

from config import *
from debug_utils import *
from commer import CommerOnServer
from msg import Msg
from flow_control import FlowControlServer

def get_wip_l(domain):
	query = nslookup.Nslookup()
	record = query.dns_lookup(domain)
	log(DEBUG, "", dns_response=record.response_full, dns_answer=record.answer)

	# record = query.soa_lookup(domain)
	# log(DEBUG, "", soa_response=record.response_full, soa_answer=record.answer)

	return record.answer

class Server():
	def __init__(self, _id, wip_l=None, worker_service_domain='edge-server', max_num_jobs_per_worker=1):
		self._id = _id
		self.wip_l = wip_l if wip_l is not None else get_wip_l(worker_service_domain)

		self.commer = CommerOnServer(_id, self.handle_msg, self.handle_result)

		self.fc_server = FlowControlServer()

		self.wip_q = queue.Queue()
		for wip in wip_l:
			for _ in range(max_num_jobs_per_worker):
				self.wip_q.put(wip)

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
		check(payload.is_job(), "Msg should contain a job")
		self.put(payload)

	# TODO: Move from condition to blocking queue
	def put(self, job):
		log(DEBUG, "recved", job=job)

		job.epoch_arrived_server = time.time()
		self.fc_server.push(job)
		if self.is_waiting_for_ajob:
			with self.wait_for_ajob:
				self.wait_for_ajob.notifyAll()
				log(DEBUG, "notified")

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

				job = self.fc_server.pop()
				check(job is not None, "A job must have arrived")

			wip = self.wip_q.get(block=True)
			self.commer.send_job_to_worker(wip, job)

	def handle_result(self, wip, result):
		log(DEBUG, "started", wip=wip, result_id=result._id)
		self.wip_q.put(wip)

		result.num_server_fair_share = len(self.fc_server.cid_q_m)
		result.serv_time = time.time() - result.epoch_arrived_server
		result.epoch_departed_server = time.time()
		self.commer.send_msg(result.cid, msg=Msg(_id=result._id, payload=result))

		log(DEBUG, "done", wip=wip, result_id=result._id, serv_time=result.serv_time)

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
	log(DEBUG, "", m=m)
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
