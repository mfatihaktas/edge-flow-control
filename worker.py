import threading, time, sys, getopt, queue

from debug_utils import *
from commer import CommerOnWorker
from msg import result_from_job

class Worker():
	def __init__(self, _id):
		self._id = _id

		self.job_q = queue.Queue()
		self.commer = CommerOnWorker(_id, self.job_q)

		t = threading.Thread(target=self.run, daemon=True)
		t.start()
		t.join()

	def close(self):
		log(DEBUG, "started;")
		self.commer.close()
		log(DEBUG, "done.")

	def run(self):
		while True:
			job = self.job_q.get(block=True)
			if job is None:
				log(DEBUG, "recved close signal.")
				self.close()
				return

			# TODO: real processing goes in here
			t = job.serv_time
			log(DEBUG, "serving/sleeping", t=t)
			time.sleep(t)
			log(DEBUG, "finished serving")

			result = result_from_job(job)
			# result.size_inBs = ?
			self.commer.send_result_to_server(result)

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
	log_to_file('{}.log'.format(_id))

	w = Worker(_id)

	input("Enter to finish...\n")
	sys.exit()
