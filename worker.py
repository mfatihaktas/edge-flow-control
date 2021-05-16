import threading, time, sys, getopt, queue

from debug_utils import *
from commer import CommerOnWorker

class Worker():
	def __init__(self, _id):
		self._id = _id

		self.sip_job_q = queue.Queue()
		self.commer = CommerOnWorker(_id, self.sip_job_q)

		t = threading.Thread(target=self.run, daemon=True)
		t.start()
		t.join()

	def close(self):
		log(DEBUG, "started;")
		self.commer.close()
		log(DEBUG, "done.")

	def run(self):
		while True:
			sip, job = self.sip_job_q.get(block=True)
			if sip is None:
				log(DEBUG, "recved close signal.")
				self.close()
				return

			# TODO: real processing goes in here
			t = job.serv_time
			log(DEBUG, "serving/sleeping", t=t)
			time.sleep(t)
			log(DEBUG, "finished serving")

			self.commer.send_result_to_server(sip, job)

def parse_argv(argv):
	m = {}
	try:
		opts, args = getopt.getopt(argv, '', ['i='])
	except getopt.GetoptError:
		assert_("Wrong args;", opts=opts, args=args)

	for opt, arg in opts:
		if opt == '--i':
			m['i'] = arg
		else:
			assert_("Unexpected opt= {}, arg= {}".format(opt, arg))

	return m

if __name__ == '__main__':
	m = parse_argv(sys.argv[1:])
	_id = 'w' + m['i']
	log_to_file('w{}.log'.format(_id))

	w = Worker(_id)

	# input("Enter to finish...\n")
	# sys.exit()
