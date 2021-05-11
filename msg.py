import jsonpickle

class Msg():
	def __init__(self, _id, payload, src_id=None, dst_id=None):
		self._id = _id
		self.payload = payload
		self.src_id = src_id
		self.dst_id = dst_id

		self.src_ip = None

	def __repr__(self):
		return "Msg(id= {} \n\t payload= {} \n\t src_id= {} \n\t dst_id= {} \n\t src_ip= {})".format(self._id, self.payload, self.src_id, self.dst_id, self.src_ip)

	def to_str(self):
		return jsonpickle.encode(self)

def msg_from_str(s):
	return jsonpickle.decode(s)

class ConnReq():
	def __init__(self, port_client_listening):
		self.port_client_listening = port_client_listening

		self.size_inBs = 0

	def __repr__(self):
		return "ConnReq(port_client_listening= {})".format(self.port_client_listening)

class ConnReply():
	def __init__(self, port_server_listening):
		self.port_server_listening = port_server_listening

		self.size_inBs = 0

	def __repr__(self):
		return "ConnReply(port_server_listening= {})".format(self.port_server_listening)

class Payload():
	def __init__(self, _id, cid, size_inBs, typ):
		self._id = _id
		self.cid = cid
		self.size_inBs = size_inBs
		self.typ = typ

	def __hash__(self):
		return hash((self._id, self.cid))

	def __eq__(self, other):
		return (self._id, self.cid) == (other._id, other.cid)

	def is_job(self):
		return self.typ == 'j'

	def is_result(self):
		return self.typ == 'r'

	def is_probe(self):
		return self.typ == 'p'

class Job(Payload):
	def __init__(self, _id, cid, serv_time, size_inBs):
		super().__init__(_id, cid, size_inBs, typ='j')
		self.serv_time = serv_time

		self.gen_epoch = None
		self.reached_server_epoch = None

	def __repr__(self):
		return "Job(id= {}, cid= {}, serv_time= {}, size_inBs= {})".format(self._id, self.cid, self.serv_time, self.size_inBs)

class Result(Payload):
	def __init__(self, _id, cid, size_inBs=0):
		super().__init__(_id, cid, size_inBs, typ='r')

		self.gen_epoch = None
		self.reached_server_epoch = None

		self.departed_server_epoch = None
		self.serv_time = None

	def __repr__(self):
		return "Result(id= {}, cid= {}, size_inBs= {})".format(self._id, self.cid, self.size_inBs)

class Probe(Payload):
	def __init__(self, _id, cid):
		super().__init__(_id, cid, typ='p', size_inBs=0)

	def __repr__(self):
		return "Probe(id= {}, cid= {}, size_inBs= {})".format(self._id, self.cid, self.size_inBs)

def result_from_job(job):
	r = Result(job._id, job.cid)
	r.gen_epoch = job.gen_epoch
	r.reached_server_epoch = job.reached_server_epoch
	return r
