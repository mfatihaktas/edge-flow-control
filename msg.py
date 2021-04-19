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

class Payload():
	def __init__(self, _id, cid, typ, size_inBs):
		self._id = _id
		self.cid = cid
		self.typ = typ
		self.size_inBs = size_inBs

	def __hash__(self):
		return hash((self._id, self.cid))

	def __eq__(self, other):
		return (self._id, self.cid) == (self._id, self.cid)

	def is_job(self):
		return self.typ == 'j'

	def is_probe(self):
		return self.typ == 'p'

	def is_result(self):
		return self.typ == 'r'

class Job(Payload):
	def __init__(self, _id, cid, serv_time, size_inBs):
		super().__init__(_id, cid, typ='j', size_inBs=size_inBs)
		self.serv_time = serv_time

	def __repr__(self):
		return "Job(id= {}, cid= {}, serv_time= {}, size_inBs= {})".format(self._id, self.cid, self.serv_time, self.size_inBs)

class Result(Payload):
	def __init__(self, _id, cid):
		super().__init__(_id, cid, typ='r', size_inBs=0)

	def __repr__(self):
		return "Result(id= {}, cid= {}, size_inBs= {})".format(self._id, self.cid, self.size_inBs)

def result_from_job(job):
	return Result(job._id, job.cid)
