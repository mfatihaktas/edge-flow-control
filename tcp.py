#!/usr/bin/python

import sys, socket, socketserver, getopt, threading, subprocess, json, time

from msg import *
from debug_utils import *

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def __init__(self, _id, server_addr, call_back):
		socketserver.TCPServer.__init__(self, server_addr, ThreadedTCPRequestHandler)
		self._id = _id
		self.call_back = call_back

	def __repr__(self):
		return "ThreadedTCPServer(id= {})".format(self._id)

MSG_LEN_HEADER_SIZE = 10

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
	def handle(self):
		while True:
			log(DEBUG, "waiting to recv msg_len_header")
			msg_len_header = self.request.recv(MSG_LEN_HEADER_SIZE)
			log(DEBUG, "recved", msg_len_header=msg_len_header)
			msg_len = int(msg_len_header)
			if msg_len == 0:
				log(DEBUG, "Recved end signal...terminating the request handler.")
				return

			msg_str = self.request.recv(msg_len)
			msg = msg_from_str(msg_str)
			# cur_thread = threading.current_thread()
			log(DEBUG, "recved", msg=msg)

			if msg.payload.size_inBs > 0:
				total_size = msg.payload.size_inBs
				log(DEBUG, 'will recv payload', total_size=total_size)
				while total_size > 0:
					to_recv_size = min(total_size, 10*1024)
					self.request.recv(to_recv_size)
					# data = self.request.recv(1)
					# recved_size = sys.getsizeof(data)
					log(DEBUG, 'recved', size=to_recv_size)
					total_size -= to_recv_size
				log(DEBUG, 'finished recving the payload', total_size=msg.payload.size_inBs)

			self.server.call_back(msg)

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

class TCPServer():
	def __init__(self, _id, handle_msg, listen_port=5000):
		self._id = _id
		self.handle_msg = handle_msg

		listen_ip = get_eth0_ip()

		log(DEBUG, "id= {}, listen_ip= {}, listen_port= {}".format(self._id, listen_ip, listen_port))

		self.server = ThreadedTCPServer(self._id, (listen_ip, listen_port), handle_msg)
		self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
		self.server_thread.start()
		log(DEBUG, "Server started running in thread.")

	def close(self):
		self.server.shutdown()
		log(DEBUG, "done.")

class TCPClient():
	def __init__(self, _id, server_listen_port=5000):
		self._id = _id
		self.server_listen_port = server_listen_port

		self.sid_ip_m = {} # sid: server_id
		self.ip = get_eth0_ip()
		self.sid_socket_m = {}

	def reg(self, sid, sip):
		if sid not in self.sid_ip_m:
			self.sid_ip_m[sid] = sip
			self.connect_to_server(sid)

	def connect_to_server(self, sid):
		check(sid in self.sid_ip_m, "not reged", sid=sid)
		sip = self.sid_ip_m[sid]
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect((sip, self.server_listen_port))
		except IOError as e:
			if e.errno == errno.EPIPE: # insuffient buffer at the server side
				assert_("broken pipe err")

		self.sid_socket_m[sid] = sock
		log(DEBUG, "connected", sid=sid, sip=sip)

	def send(self, msg):
		sid = msg.dst_id
		check(sid in self.sid_ip_m, "Unexpected sid= {}".format(sid))

		if sid not in self.sid_socket_m:
			self.connect_to_server(sid)
		sock = self.sid_socket_m[sid]

		msg.src_id = self._id
		msg.src_ip = self.ip

		msg_str = msg.to_str().encode('utf-8')
		msg_size = len(msg_str)
		header = msg_len_header(msg_size)
		sock.sendall(header)
		log(DEBUG, "sent header")

		sock.sendall(msg_str)
		log(DEBUG, "sent msg", msg=msg)

		# TODO: Payload is generated synthetically for now
		payload = bytearray(msg.payload.size_inBs)
		log(DEBUG, "sending payload")
		sock.sendall(payload)
		log(DEBUG, "sent payload", payload_size=msg.payload.size_inBs)

	def close(self):
		for sid, sock in self.sid_socket_m.items():
			sock.sendall(msg_len_header(0))
			log(DEBUG, "sent close signal", sid=sid)

	def broadcast(self, msg):
		for sid in self.sid_socket_m:
			msg.dst_id = sid
			self.send(msg)
