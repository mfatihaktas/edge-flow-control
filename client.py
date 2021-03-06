import threading, time, sys, getopt, json, queue

from config import *
from plot_utils import *
from rvs import *
from msg import *
from commer import PACKET_SIZE, CommerOnClient
from flow_control import FlowControlClient

class Client():
	def __init__(self, _id, sid_ip_m, num_jobs_to_finish, serv_time_rv, size_inBs_rv, avg_load_target):
		self._id = _id
		self.sid_ip_m = sid_ip_m
		self.num_jobs_to_finish = num_jobs_to_finish
		self.serv_time_rv = serv_time_rv
		self.size_inBs_rv = size_inBs_rv

		self.commer = CommerOnClient(_id, self.handle_msg)

		self.sid_q = queue.Queue()
		self.fc_client = FlowControlClient(_id, self.sid_q, avg_load_target)
		for sid, sip in sid_ip_m.items():
			self.commer.reg(sid, sip)
			self.fc_client.reg(sid, sip)

		self.num_jobs_gened = 0
		self.num_jobs_finished = 0

		self.job_finished_l = []
		self.last_time_result_recved = time.time()
		self.inter_result_time_l = []

		self.on = True
		t = threading.Thread(target=self.run, daemon=True)
		t.start()
		t.join()

	def __repr__(self):
		return 'Client(' + '\n\t' + \
			'id= {}'.format(self._id) + '\n\t' + \
      'sid_ip_m= {}'.format(self.sid_ip_m) + '\n\t' + \
			'num_jobs_to_finish= {}'.format(self.num_jobs_to_finish) + '\n\t' + \
			'serv_time_rv= {}'.format(self.serv_time_rv) + '\n\t' + \
			'size_inBs_rv= {}'.format(self.size_inBs_rv) + ')'

	def close(self):
		if not self.on:
			return

		log(DEBUG, "started;")
		self.on = False
		self.sid_q.put(-1)

		self.commer.close()
		self.fc_client.close()
		log(DEBUG, "done.")

	def handle_msg(self, msg):
		log(DEBUG, "started", msg=msg)

		result = msg.payload
		check(result.is_result(), "Msg should contain a result.")

		sid = msg.src_id
		t = time.time()
		result.epoch_arrived_client = t

		self.job_finished_l.append(result)

		log(DEBUG, "",
				response_time = (result.epoch_arrived_client - result.epoch_departed_client),
				time_from_c_to_s = (result.epoch_arrived_server - result.epoch_departed_client),
				time_from_s_to_c = (result.epoch_arrived_client - result.epoch_departed_server),
				time_from_s_to_w_to_s = result.serv_time,
				num_server_fair_share = result.num_server_fair_share,
				result=result)

		self.fc_client.update(sid, result)

		inter_result_time = t - self.last_time_result_recved
		self.inter_result_time_l.append(inter_result_time)
		self.last_time_result_recved = t
		log(DEBUG, "", inter_result_time=inter_result_time, job_serv_time=result.serv_time)

		self.num_jobs_finished += 1
		log(DEBUG, "", num_jobs_gened=self.num_jobs_gened, num_jobs_finished=self.num_jobs_finished)

		log(DEBUG, "done", msg_id=msg._id)
		if self.num_jobs_finished >= self.num_jobs_to_finish:
			self.close()

	def run(self):
		while self.on:
			log(DEBUG, "Waiting for sid")
			sid = self.sid_q.get(block=True)
			if sid == -1:
				log(DEBUG, "Recved close signal")
				return

			self.num_jobs_gened += 1
			job = Job(_id = self.num_jobs_gened,
								cid = self._id,
								size_inBs = int(self.size_inBs_rv.sample()),
								serv_time = self.serv_time_rv.sample())
			job.epoch_departed_client = time.time()

			msg = Msg(_id=self.num_jobs_gened, payload=job)
			self.commer.send_msg(sid, msg)
			log(DEBUG, "sent", job=job, sid=sid)

		log(DEBUG, "done")

	def summarize_job_info(self):
		sid__T_l_m = {sid: [] for sid in self.sid_ip_m}
		for job in self.job_finished_l:
			T = 1000*(job.epoch_arrived_client - job.epoch_departed_client)
			if T < 0:
				log(WARNING, "Negative response time!", job=job, T=T)
				continue

			sid__T_l_m[info['sid']].append(T)

		fontsize = 14
		## CDF of response times
		ax = plot.gca()
		for sid, T_l in sid__T_l_m.items():
			add_cdf(T_l, ax, sid, next(nice_color)) # drawline_x_l=[1000*self.max_delay]
		plot.xscale('log')
		plot.xticks(rotation=70)
		plot.ylabel('Pr{Response time < x}', fontsize=fontsize)
		plot.xlabel('x (msec)', fontsize=fontsize)
		plot.legend(fontsize=fontsize)
		plot.gcf().set_size_inches(6, 4)
		plot.savefig("plot_{}_cdf_T.png".format(self._id), bbox_inches='tight')
		plot.gcf().clear()

		# CDF of inter result times
		ax = plot.gca()
		add_cdf(self.inter_result_time_l, ax, '', next(nice_color)) # drawline_x_l=[1000*self.inter_job_gen_time_rv.mean()]
		plot.xscale('log')
		plot.xticks(rotation=70)
		plot.ylabel('Pr{Inter result arrival time < x}', fontsize=fontsize)
		plot.xlabel('x (msec)', fontsize=fontsize)
		plot.legend(fontsize=fontsize)
		plot.gcf().set_size_inches(6, 4)
		plot.savefig("plot_{}_cdf_interResultTime.png".format(self._id), bbox_inches='tight')

		log(DEBUG, "done.")

def parse_argv(argv):
	m = {}
	try:
		opts, args = getopt.getopt(argv, '', ['i=', 'sid_ip_m='])
	except getopt.GetoptError:
		assert_("Wrong args;", opts=opts, args=args)

	for opt, arg in opts:
		if opt == '--i':
			m['i'] = arg
		elif opt == '--sid_ip_m':
			m['sid_ip_m'] = json.loads(arg)
		else:
			assert_("Unexpected opt= {}, arg= {}".format(opt, arg))

	return m

def run(argv):
	m = parse_argv(argv)
	_id = 'c' + m['i']
	log_to_file('{}.log'.format(_id))

	ES = 0.1 # 0.01
	mu = float(1/ES)
	c = Client(_id, sid_ip_m=m['sid_ip_m'],
						 num_jobs_to_finish=100,
						 serv_time_rv=DiscreteRV(p_l=[1], v_l=[ES*1000], norm_factor=1000), # Exp(mu), # TPareto_forAGivenMean(l=ES/2, a=1, mean=ES)
						 size_inBs_rv=DiscreteRV(p_l=[1], v_l=[1]),
						 avg_load_target=0.8)

	time.sleep(3)
	log(DEBUG, "", client=c)
	c.summarize_job_info()

	time.sleep(100000)
	c.close()
	sys.exit()

def test(argv):
	m = parse_argv(argv)
	_id = 'c' + m['i']
	log_to_file('{}.log'.format(_id))

	# input("Enter to start...\n")
	ES = 0.1 # 0.01
	mu = float(1/ES)
	c = Client(_id, sid_ip_m=m['sid_ip_m'], # {'s0': '10.0.1.0'},
						 num_jobs_to_finish=100, # 200
						 serv_time_rv=DiscreteRV(p_l=[1], v_l=[ES*1000], norm_factor=1000), # Exp(mu), # TPareto_forAGivenMean(l=ES/2, a=1, mean=ES)
						 size_inBs_rv=DiscreteRV(p_l=[1], v_l=[PACKET_SIZE*1]),
						 avg_load_target=0.8)

	# input("Enter to summarize job info...\n")
	# time.sleep(3)
	log(DEBUG, "", client=c)
	c.summarize_job_info()

	# input("Enter to finish...\n")
	# c.close()
	# sys.exit()

if __name__ == '__main__':
	if TEST:
		test(sys.argv[1:])
	else:
		run(sys.argv[1:])
