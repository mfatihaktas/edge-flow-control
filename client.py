import threading, time, sys, getopt

from plot_utils import *
from rvs import *
from tcp import *
from flow_control import *

class Client():
	def __init__(self, _id, sid_ip_m,
							 num_jobs_to_gen, max_delay,
							 inter_ar_time_rv, serv_time_rv, size_inBs_rv):
		self._id = _id
		self.sid_ip_m = sid_ip_m
		self.num_jobs_to_gen = num_jobs_to_gen
		self.max_delay = max_delay
		self.inter_ar_time_rv = inter_ar_time_rv
		self.serv_time_rv = serv_time_rv
		self.size_inBs_rv = size_inBs_rv

		self.tcp_server = TCPServer(_id, self.handle_msg)

		self.fc_client = FlowControlClient(_id, max_delay)
		for sid, sip in sid_ip_m.items():
			self.fc_client.reg(sid, sip)

		self.num_jobs_gened = 0
		t = threading.Thread(target=self.run, daemon=True)
		t.start()

		self.job_info_m = {}
		t.join()

	def __repr__(self):
		return 'Client(' '\n\t' + \
			'id= {}'.format(self._id) + '\n\t' + \
      'sid_ip_m= {}'.format(self.sid_ip_m) + '\n\t' + \
			'num_jobs_to_gen= {}'.format(self.num_jobs_to_gen) + '\n\t' + \
			'max_delay= {}'.format(self.max_delay) + '\n\t' + \
			'inter_ar_time_rv= {}'.format(self.inter_ar_time_rv) + '\n\t' + \
			'serv_time_rv= {}'.format(self.serv_time_rv) + '\n\t' + \
			'size_inBs_rv= {}'.format(self.size_inBs_rv) + ')'

	def close(self):
		self.fc_client.close()

	def handle_msg(self, msg):
		log(DEBUG, "handling", msg=msg)

		result = msg.payload
		check(result.is_result(), "Msg should contain a result.")

		sid = msg.src_id
		info = self.job_info_m[result]
		t = time.time() - info['enter_time']
		info.update(
			{
				'fate': 'finished',
				'sid': sid,
				'T': 1000*t
			})

		self.fc_client.update_delay_controller(sid, t)

	def run(self):
		while True:
			inter_ar_time = self.inter_ar_time_rv.sample() # random.expovariate(self.rate)
			log(DEBUG, "sleeping ...", inter_ar_time=inter_ar_time)
			time.sleep(inter_ar_time)

			self.num_jobs_gened += 1
			job = Job(_id = self.num_jobs_gened,
								cid = self._id,
								serv_time = self.serv_time_rv.sample(),
								size_inBs = int(self.size_inBs_rv.sample()))
			self.job_info_m[job] = {'enter_time': time.time()}

			if self.fc_client.push(job) == False:
				self.job_info_m[job].update({'fate': 'dropped'})

			if self.num_jobs_gened == self.num_jobs_to_gen:
				self.close()
				return

	def summarize_job_info(self):
		num_dropped = 0

		sid__T_l_m = {sid: [] for sid in self.sid_ip_m}
		for job, info in self.job_info_m.items():
			if 'fate' not in info:
				continue

			fate = info['fate']
			if fate == 'dropped':
				num_dropped += 1
			elif fate == 'finished':
				T = info['T']
				if T < 0:
					log(WARNING, "Negative turnaround time", job=job, T=T)
					continue

				sid__T_l_m[info['sid']].append(T)

		ax = plot.gca()
		for sid, T_l in sid__T_l_m.items():
			add_cdf(T_l, ax, sid, next(nice_color), drawline_x_l=[1000*self.max_delay])
		plot.xscale('log')

		fontsize = 14
		plot.ylabel('CDF', fontsize=fontsize)
		plot.xlabel('Turnaround time (msec)', fontsize=fontsize)

		num_total = len(T_l) + num_dropped
		f_dropped = round(num_dropped / num_total, 2)
		log(DEBUG, "", f_dropped=f_dropped)
		plot.title('f_dropped= {}'.format(f_dropped), fontsize=fontsize)
		plot.legend(fontsize=fontsize)
		plot.gcf().set_size_inches(6, 4)
		plot.savefig("plot_cdf_T_{}.png".format(self._id), bbox_inches='tight')
		plot.gcf().clear()
		log(DEBUG, "done.")

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
	_id = 'c' + parse_argv(argv)
	log_to_file('{}.log'.format(_id))

	# input("Enter to start...\n")

	ES = 0.01
	mu = float(1/ES)
	ar = 0.3*mu
	c = Client(_id, sid_ip_m={'s0': '10.0.1.0'},
						 num_jobs_to_gen=1000, max_delay=0.05,
						 inter_ar_time_rv=Exp(ar), # DiscreteRV(p_l=[1], v_l=[0.5]),
						 serv_time_rv=Exp(mu), # DiscreteRV(p_l=[1], v_l=[ES*1000], norm_factor=1000), # TPareto_forAGivenMean(l=ES/2, a=1, mean=ES)
						 size_inBs_rv=DiscreteRV(p_l=[1], v_l=[1]))

	# input("Enter to summarize job info...\n")
	time.sleep(3)
	log(DEBUG, "", client=c)
	c.summarize_job_info()

	# input("Enter to finish...\n")
	time.sleep(100000)
	c.close()
	sys.exit()

if __name__ == '__main__':
	test(sys.argv[1:])
