#!/usr/bin/python

import sys, socket, socketserver, getopt, threading, subprocess, json, time

from msg import *
from debug_utils import *

# ***************************  Commer utils  *************************** #
def get_eth0_ip():
	# search and bind to eth0 ip address
	intf_list = subprocess.getoutput("ifconfig -a | sed 's/[ \t].*//;/^$/d'").split('\n')
	intf_eth0 = None
	for intf in intf_list:
		if 'eth0' in intf:
			intf_eth0 = intf

	check(intf_eth0 is not None, "Could not find interface with eth0.")
	intf_eth0_ip = subprocess.getoutput("ip address show dev " + intf_eth0).split()
	intf_eth0_ip = intf_eth0_ip[intf_eth0_ip.index('inet') + 1].split('/')[0]
	return intf_eth0_ip

def msg_len_header(msg_size):
	msg_size_str = str(msg_size)
	return ('0' * (MSG_LEN_HEADER_SIZE - len(msg_size_str)) + msg_size_str).encode('utf-8')

def connect(ip, port):
	log(DEBUG, "started;", ip=ip, port=port)
	try:
		if TRANS == 'TCP':
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect((ip, port))
		elif TRANS == 'UDP':
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return sock
	except IOError as e:
		if e.errno == errno.EPIPE: # insuffient buffer at the server side
			assert_("broken pipe err")
			return None

	log(DEBUG, "done.", ip=ip, port=port)

def bind_get_sock(ip, port):
	if TRANS == 'TCP':
		conn_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		conn_sock.bind((ip, port))
		# conn_sock.listen(1)
		log(DEBUG, "Binded on, listening...", ip=ip, port=port)
		conn_sock.listen()
		sock, addr = conn_sock.accept()
		log(DEBUG, "Got connection", addr=addr)
	elif TRANS == 'UDP':
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind((ip, port))
		log(DEBUG, "Binded on", ip=ip, port=port)

	return sock

def recv_size(size, recv):
	data = bytearray()
	size_to_recv = size
	while size_to_recv > 0:
		data_recved = recv(size_to_recv)
		size_to_recv -= len(data_recved)
		data.extend(data_recved)
	return data

def recv_msg(sock):
	total_size_recved = 0
	recv = lambda size: sock.recv(size)
	msg_len_header = recv_size(MSG_LEN_HEADER_SIZE, recv)
	total_size_recved += MSG_LEN_HEADER_SIZE
	log(DEBUG, "recved header", msg_len_header=msg_len_header)
	msg_len = int(msg_len_header)
	log(DEBUG, "will recv msg", msg_len=msg_len)
	if msg_len == 0:
		return None

	msg_str = recv_size(msg_len, recv)
	msg = msg_from_str(msg_str)
	total_size_recved += len(msg_str)
	log(DEBUG, "recved", msg=msg)

	if msg.payload.size_inBs > 0:
		total_size_to_recv = msg.payload.size_inBs
		log(DEBUG, 'will recv payload', total_size_to_recv=total_size_to_recv)
		while total_size_to_recv > 0:
			size_to_recv = min(total_size_to_recv, PACKET_SIZE)
			data = sock.recv(size_to_recv)
			size_recved = len(data)
			log(DEBUG, 'recved', size=size_recved)
			total_size_to_recv -= size_recved
			total_size_recved += size_recved

		log(DEBUG, "finished recving the payload", size=msg.payload.size_inBs)

	log(DEBUG, "done.", total_size_recved=total_size_recved)
	return msg

def send_msg(sock, msg, trans=TRANS, to_addr=None):
	check(trans != 'UDP' or to_addr is not None, "Trans is UDP but to_addr is None.")

	if msg is None:
		header_ba = bytearray(msg_len_header(0))
		if trans == 'TCP':
			sock.sendall(header_ba)
		elif trans == 'UDP':
			sock.sendto(header_ba, to_addr)
		return

	msg.src_ip = IP_ETH0
	msg_str = msg.to_str().encode('utf-8')
	msg_size = len(msg_str)
	header = msg_len_header(msg_size)

	header_ba = bytearray(header)
	msg_ba = bytearray(msg_str)
	if msg.payload.size_inBs > 0:
		payload_ba = bytearray(msg.payload.size_inBs)

	if trans == 'TCP':
		data = header_ba + msg_ba + payload_ba if msg.payload.size_inBs > 0 else header_ba + msg_ba
		# sock.sendall(data)

		total_size = len(data)
		for i in range(0, total_size, PACKET_SIZE):
			sock.send(data[i:min(i + PACKET_SIZE, total_size)])
		log(DEBUG, "sent", total_size=total_size)

	elif trans == 'UDP':
		sock.sendto(header_ba, to_addr)
		sock.sendto(msg_ba, to_addr)

		if msg.payload.size_inBs > 0:
			total_size = len(payload_ba)
			for i in range(0, total_size, PACKET_SIZE):
				sock.sendto(payload_ba[i:min(i + PACKET_SIZE, total_size)], to_addr)

# ***************************  CommerOnServer  *************************** #
class ResultHandler(socketserver.BaseRequestHandler):
	def handle(self):
		msg = recv_msg(sock=self.request)
		log(DEBUG, "recved", msg=msg)
		check(msg.dst_id == self.server._id, "Msg recved at the wrong destination.")

		self.server.handle_result(result=msg.payload)

class ResultServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def __init__(self, _id, server_addr, handle_result):
		socketserver.TCPServer.__init__(self, server_addr, ResultHandler)
		self._id = _id
		self.handle_result = handle_result

		log(DEBUG, "constructed", server_addr=server_addr)

class ConnReqHandler(socketserver.BaseRequestHandler):
	def handle(self):
		msg_str = self.request.recv(1024).strip()
		msg = msg_from_str(msg_str)
		log(DEBUG, "recved", msg=msg)
		check(msg.dst_id == self.server._id, "Msg recved at the wrong destination.")

		self.server.handle_conn_req(cid=msg.src_id, cip=self.client_address[0], result=msg.payload, sock=self.request)

class ConnServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def __init__(self, _id, server_addr, handle_conn_req):
		socketserver.TCPServer.__init__(self, server_addr, ConnReqHandler)
		self._id = _id
		self.handle_conn_req = handle_conn_req

		log(DEBUG, "constructed", server_addr=server_addr)

class CommerOnServer():
	def __init__(self, _id, handle_msg):
		self._id = _id
		self.handle_msg = handle_msg

		self.port_to_listen_next_client = 5001

		self.conn_req_server = ConnServer(self._id, (IP_ETH0, PORT_ON_SERVER_TO_LISTEN_FOR_CONN_REQS), self.handle_conn_req)
		self.conn_req_server_thread = threading.Thread(target=self.conn_req_server.serve_forever, daemon=True)
		self.conn_req_server_thread.start()

		self.result_server = ResultServer(self._id, (IP_ETH0, PORT_ON_SERVER_TO_LISTEN_FOR_RESULTS), self.handle_result)
		self.result_server_thread = threading.Thread(target=self.result_server.serve_forever, daemon=True)
		self.result_server_thread.start()

		self.cid_sock_m = {}
		self.cid_addr_m = {}

	def close(self):
		log(DEBUG, "started;")
		self.conn_req_server_thread.shutdown()
		log(DEBUG, "done.")

	def handle_conn_req(self, cid, cip, conn_req, sock):
		log(DEBUG, "started;", cid=cid, cip=cip, conn_req=conn_req)

		## Start listening to client
		t = threading.Thread(target=self.start_listening_client, args=(cid, self.port_to_listen_next_client), daemon=True)
		t.start()

		## Create the sock to client
		self.cid_sock_m[cid] = connect(cip, conn_req.port_client_listening)
		self.cid_addr_m[cid] = (cip, conn_req.port_client_listening)

		## Reply to client
		conn_reply = ConnReply(port_server_listening=self.port_to_listen_next_client)
		self.port_to_listen_next_client += 1
		msg = Msg(_id=-1, payload=conn_reply, dst_id=cid)
		send_msg(sock, msg, trans='TCP')

		log(DEBUG, "done.")

	def handle_result(self, result):
		log(DEBUG, "started;", result=result)
		check(result.cid in self.cid_sock_m, "Result recved for an unsubscribed client.")

		self.send_msg(result.cid, msg=Msg(_id=result._id, payload=result))
		log(DEBUG, "done.")

	def start_listening_client(self, cid, port):
		log(DEBUG, "started;", cid=cid, port=port)

		sock = bind_get_sock(IP_ETH0, port)
		while True:
			msg = recv_msg(sock)
			if msg is None:
				log(DEBUG, "Recved close signal...terminating the request handler.")
				break
			self.handle_msg(msg)

		log(DEBUG, "done.", cid=cid)

	def send_msg(self, cid, msg):
		check(cid in self.cid_sock_m, "Should have been connected to client.")
		msg.src_id = self._id
		msg.dst_id = cid
		send_msg(self.cid_sock_m[cid], msg, to_addr=self.cid_addr_m[cid])

	def send_job_recv_result(self, wip, job):
		# TODO: Eliminate the need to connect to worker each time by using WebSocket's.
		## Send job
		sock = connect(wip, PORT_ON_WORKER_TO_LISTEN_FOR_JOBS)
		msg = Msg(job._id, payload=job)
		send_msg(sock, msg)

		## Recv reply
		msg = recv_msg(sock)

		return msg.payload

# ***************************  CommerOnClient  *************************** #
class CommerOnClient():
	def __init__(self, _id, handle_msg):
		self._id = _id
		self.handle_msg = handle_msg
		self.port_to_listen_next_server = 5000

		self.sid_addr_m = {} # sid: server_id
		self.ip = get_eth0_ip()
		self.sid_sock_m = {}

	def reg(self, sid, sip):
		if sid not in self.sid_addr_m:
			self.connect_to_server(sid, sip)

	def connect_to_server(self, sid, sip):
		log(DEBUG, "started;", sid=sid, sip=sip)

		## Start listening to server
		t = threading.Thread(target=self.start_listening_server, args=(sid, self.port_to_listen_next_server), daemon=True)
		t.start()

		## Send connection request
		sock = connect(sip, PORT_ON_SERVER_TO_LISTEN_FOR_CONN_REQS)
		conn_req = ConnReq(port_client_listening=self.port_to_listen_next_server)
		self.port_to_listen_next_server += 1
		msg = Msg(_id=-1, payload=conn_req, src_id=self._id, dst_id=sid)
		sock.sendall(msg.to_str().encode('utf-8'))

		## Recv connection reply
		msg = recv_msg(sock)
		check(msg is not None, "Conn req cannot contain None as msg.")

		## Create transport socket to server
		conn_reply = msg.payload
		self.sid_sock_m[sid] = connect(sip, conn_reply.port_server_listening)

		self.sid_addr_m[sid] = (sip, conn_reply.port_server_listening)
		log(DEBUG, "done.", sid=sid)

	def start_listening_server(self, cid, port):
		log(DEBUG, "started;", cid=cid, port=port)

		sock = bind_get_sock(IP_ETH0, port)
		while True:
			msg = recv_msg(sock)
			if msg is None:
				log(DEBUG, "Recved close signal...terminating the request handler.")
				break
			self.handle_msg(msg)

		log(DEBUG, "done.", cid=cid)

	def send_msg(self, sid, msg):
		check(sid in self.sid_sock_m, "Should have been connected to server.")
		if msg is not None:
			msg.src_id = self._id
			msg.src_ip = self.ip
			msg.dst_id = sid
		send_msg(self.sid_sock_m[sid], msg, to_addr=self.sid_addr_m[sid])

	def close(self):
		log(DEBUG, "started;")
		for sid in self.sid_sock_m:
			self.send_msg(sid, msg=None)
			log(DEBUG, "sent close signal", sid=sid)
		log(DEBUG, "done.")

# ***************************	 CommerOnWorker	 *************************** #
class JobReqHandler(socketserver.BaseRequestHandler):
	def handle(self):
		msg = recv_msg(sock=self.request)
		sip = self.client_address[0]
		log(DEBUG, "recved", msg=msg)
		self.server.handle_job_req(sip=self.client_address[0], job=msg.payload)

class JobReqServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def __init__(self, _id, server_addr, handle_job_req):
		socketserver.TCPServer.__init__(self, server_addr, JobReqHandler)
		self._id = _id
		self.handle_job_req = handle_job_req

class CommerOnWorker():
	def __init__(self, _id, req_job_q):
		self._id = _id
		# self.handle_job = handle_job
		self.req_job_q = req_job_q

		self.job_req_server = JobReqServer(self._id, (IP_ETH0, PORT_ON_WORKER_TO_LISTEN_FOR_JOBS), self.handle_job_req)
		self.job_req_server_thread = threading.Thread(target=self.job_req_server.serve_forever, daemon=True)
		self.job_req_server_thread.start()
		log(DEBUG, "Started JobReqServer;", ip=IP_ETH0, port=PORT_ON_WORKER_TO_LISTEN_FOR_JOBS)

		log(DEBUG, "constructed;", self=self)

	def __repr__(self):
		return 'CommerOnWorker(id= {})'.format(self._id)

	def close(self):
		log(DEBUG, "started;")
		self.job_req_server_thread.shutdown()
		log(DEBUG, "done.")

	def handle_job_req(self, sip, job):
		log(DEBUG, "started;", job=job
		self.sip_job_q.put((sip, job))
		log(DEBUG, "done.")

	def send_result_to_server(self, sip, job):
		result = result_from_job(job)
		# result.size_inBs = ?
		sock = connect(sip, PORT_ON_SERVER_TO_LISTEN_FOR_RESULTS)
		send_msg(sock, msg=Msg(_id=result._id, payload=result, to_addr=(sip, PORT_ON_SERVER_TO_LISTEN_FOR_RESULTS)))
		log(DEBUG, "sent", result=result)
