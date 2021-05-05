#!/usr/bin/python

import sys, socket, socketserver, getopt, threading, subprocess, json, time

from msg import *
from debug_utils import *

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
	def __init__(self, _id, server_addr, call_back):
		socketserver.UDPServer.__init__(self, server_addr, ThreadedUDPRequestHandler)
		self._id = _id
		self.call_back = call_back

	def __repr__(self):
		return "ThreadedUDPServer(id= {})".format(self._id)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def __init__(self, _id, server_addr, call_back):
		socketserver.TCPServer.__init__(self, server_addr, ThreadedTCPRequestHandler)
		self._id = _id
		self.call_back = call_back

	def __repr__(self):
		return "ThreadedTCPServer(id= {})".format(self._id)

MSG_LEN_HEADER_SIZE = 10

# Reference:
# - https://gist.github.com/arthurafarias/7258a2b83433dfda013f1954aaecd50a
# - https://note.artchiu.org/2017/10/16/python-multithread-udp-socket-server/
class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
	# handle() is called for every UDP packet received. Thus the logic below
	# will not work.
	def handle(self):
		data = self.request[0].strip()
		log(DEBUG, "recved", data=data)

		check(len(data) == MSG_LEN_HEADER_SIZE, "Header length is wrong.")
		msg_len = int(data)
		if msg_len == 0:
	 		log(DEBUG, "Recved end signal.")
	 		return

		sock = self.request[1]
		msg_str = sock.recvfrom(msg_len)
		msg = msg_from_str(msg_str)
		log(DEBUG, "recved", msg=msg)

		if msg.payload.size_inBs > 0:
			total_size = msg.payload.size_inBs
			log(DEBUG, 'will recv payload', total_size=total_size)
			while total_size > 0:
				to_recv_size = min(total_size, 10*1024)
				self.sock.recvfrom(to_recv_size)
				log(DEBUG, 'recved', size=to_recv_size)
				total_size -= to_recv_size
			log(DEBUG, 'finished recving the payload', total_size=msg.payload.size_inBs)

		self.server.call_back(msg)

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
	def handle(self):
		while True:
			msg_len_header = self.request.recv(MSG_LEN_HEADER_SIZE)
			log(DEBUG, "recved", msg_len_header=msg_len_header)
			try:
				msg_len = int(msg_len_header)
			except ValueError:
				log(WARNING, "Recved NON-header.")
				continue

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

class TransServer():
	def __init__(self, _id, handle_msg, listen_port=5000):
		self._id = _id
		self.handle_msg = handle_msg

		listen_ip = get_eth0_ip()

		log(DEBUG, "id= {}, listen_ip= {}, listen_port= {}".format(self._id, listen_ip, listen_port))

		if TRANS == 'TCP':
			self.server = ThreadedTCPServer(self._id, (listen_ip, listen_port), handle_msg)
		elif TRANS == 'UDP':
			self.server = ThreadedUDPServer(self._id, (listen_ip, listen_port), handle_msg)
		self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
		self.server_thread.start()
		log(DEBUG, "Server started running in thread.")

	def close(self):
		self.server.shutdown()
		log(DEBUG, "done.")

class TransClient():
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
			if TRANS == 'TCP':
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.connect((sip, self.server_listen_port))
			elif TRANS == 'UDP':
				sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		except IOError as e:
			if e.errno == errno.EPIPE: # insuffient buffer at the server side
				assert_("broken pipe err")

		self.sid_socket_m[sid] = sock
		log(DEBUG, "connected", sid=sid, sip=sip)

	def send(self, sid, data):
		sock = self.sid_socket_m[sid]
		if TRANS == 'TCP':
			sock.sendall(data)
		elif TRANS == 'UDP':
			sock.sendto(data, (self.sid_ip_m[sid], self.server_listen_port))

	def send_msg(self, msg):
		sid = msg.dst_id
		if sid not in self.sid_socket_m:
			self.connect_to_server(sid)

		msg.src_id = self._id
		msg.src_ip = self.ip

		msg_str = msg.to_str().encode('utf-8')
		msg_size = len(msg_str)
		header = msg_len_header(msg_size)

		header_ba = bytearray(header)
		msg_ba = bytearray(msg_str)
		payload_ba = bytearray(msg.payload.size_inBs)
		log(DEBUG, "", payload_ba_len=len(payload_ba))

		if TRANS == 'TCP':
			self.send(sid, header_ba + msg_ba + payload_ba)
		elif TRANS == 'UDP':
			self.send(sid, header_ba)
			self.send(sid, msg_ba)

			total_size = len(payload_ba)
			packet_size = 60000 # Bs
			for i in range(0, total_size, packet_size):
				self.send(sid, payload_ba[i:min(i + packet_size, total_size)])

		log(DEBUG, "sent", msg=msg)

	def close(self):
		for sid in self.sid_socket_m:
			self.send(sid, msg_len_header(0))
			log(DEBUG, "sent close signal", sid=sid)

	def broadcast(self, msg):
		for sid in self.sid_socket_m:
			msg.dst_id = sid
			self.send(msg)
