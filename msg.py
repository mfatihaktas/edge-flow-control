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
	def __init__(self, _id, cid, typ, size_inBs, serv_time=None):
		self._id = _id
		self.cid = cid
		self.size_inBs = size_inBs
		self.typ = typ
		self.serv_time = serv_time

		self.epoch_departed_client = None
		self.epoch_arrived_server = None
		self.epoch_departed_server = None
		self.epoch_arrived_client = None

		self.num_server_fair_share = None

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
	def __init__(self, _id, cid, size_inBs, serv_time):
		super().__init__(_id, cid, 'j', size_inBs, serv_time)

	def __repr__(self):
		return "Job(id= {}, cid= {}, size_inBs= {}, serv_time= {})".format(self._id, self.cid, self.size_inBs, self.serv_time)

class Result(Payload):
	def __init__(self, _id, cid, size_inBs=0):
		super().__init__(_id, cid, 'r', size_inBs)

	def __repr__(self):
		return "Result(id= {}, cid= {}, size_inBs= {})".format(self._id, self.cid, self.size_inBs)

def result_from_job(j):
	r = Result(j._id, j.cid)

	r.serv_time = j.serv_time
	r.epoch_departed_client = j.epoch_departed_client
	r.epoch_arrived_server = j.epoch_arrived_server
	r.epoch_departed_server = j.epoch_departed_server
	r.epoch_arrived_client = j.epoch_arrived_client
	return r
