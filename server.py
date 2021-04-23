import threading, time, sys, getopt

from tcp import *
from flow_control import *

class Server():
	def __init__(self, _id):
		self._id = _id

		self.tcp_server = TCPServer(_id, self.handle_msg)
		self.tcp_client = TCPClient(_id)

		self.fc_server = FlowControlServer()

		self.wait_for_ajob = threading.Condition()
		self.is_waiting_for_ajob = False
		t = threading.Thread(target=self.run, daemon=True)
		t.start()
		t.join()

	def handle_msg(self, msg):
		log(DEBUG, "handling", msg=msg)
		cid = msg.src_id
		self.tcp_client.reg(cid, msg.src_ip)
		self.fc_server.reg(cid)

		payload = msg.payload
		check(payload.is_job() or payload.is_probe(), "Msg should contain a job or probe.")
		self.put(payload)

	def put(self, job):
		log(DEBUG, "recved", job=job)

		if self.fc_server.push(job):
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
				continue

			if job.is_job():
				log(DEBUG, "will serv", job=job)
				time.sleep(job.serv_time)
				log(DEBUG, "finished serving", job=job)

				msg = Msg(job._id, payload=result_from_job(job), dst_id=job.cid)
			elif job.is_probe():
				msg = Msg(job._id, payload=job, dst_id=job.cid) # return the probe back to the client

			self.tcp_client.send(msg)

def parse_argv(argv):
	i = None
	try:
		opts, args = getopt.getopt(argv, '', ['i='])
	except getopt.GetoptError:
		assert_("Wrong args;", opts=opts, args=args)

	for opt, arg in opts:
		if opt == '--i':
			i = arg
		else:
			assert_("Unexpected opt= {}, arg= {}".format(opt, arg))

	check(i is not None, "i is not set.")
	return i

def test(argv):
	_id = 's' + parse_argv(argv)
	log_to_file('{}.log'.format(_id))

	s = Server(_id)
	# input("Enter to finish...\n")
	# sys.exit()

if __name__ == '__main__':
	test(sys.argv[1:])
