#!/usr/bin/python

from mininet.log import setLogLevel, info #, error
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.cli import CLI
import time

from debug_utils import *

class MyTopo(Topo):
	def __init__(self):
		Topo.__init__(self)

		s0 = self.addHost('s0')
		c0 = self.addHost('c0')
		c1 = self.addHost('c1')
		c2 = self.addHost('c2')
		c3 = self.addHost('c3')
		c4 = self.addHost('c4')
		c5 = self.addHost('c5')
		sw0 = self.addSwitch('sw0')

		link_opts = dict(bw=1000, delay='1ms', loss=0, max_queue_size=1000, use_htb=True)
		self.addLink(s0, sw0, **link_opts)
		self.addLink(c0, sw0, **link_opts)
		self.addLink(c1, sw0, **link_opts)
		self.addLink(c2, sw0, **link_opts)
		self.addLink(c3, sw0, **link_opts)
		self.addLink(c4, sw0, **link_opts)
		self.addLink(c5, sw0, **link_opts)

def run_servers(server_l):
	popens = {}
	for i, s in enumerate(server_l):
		s.cmdPrint('pwd')
		popens[s] = s.popen('./run.sh s %s' % i)
		log(DEBUG, "Started s{}".format(i))

	"""
	# Monitor them and print output
	for host,popen in popens.items():
		out, err = popen.communicate()
		print '%s; out=%s, err=%s' % (host.name,out,err)
	"""
	"""
	for host, line in pmonitor( popens ):
	  if host:
      print "<%s>: %s" % ( host.name, line.strip() )
	"""
	log(INFO, "done.")

def run_clients(client_l):
	popens = {}
	for i, s in enumerate(client_l):
		s.cmdPrint('pwd')
		popens[s] = s.popen('./run.sh c %s' % i)
		log(DEBUG, "Started c{}".format(i))

if __name__ == '__main__':
	setLogLevel('info')
	net = Mininet(topo=MyTopo(), link=TCLink, controller=OVSController)

	s0 = net.getNodeByName('s0')
	s0.setIP(ip='10.0.1.0', prefixLen=32)
	s0.setMAC(mac='00:00:00:00:01:00')

	c0, c1 = net.getNodeByName('c0', 'c1')
	c2, c3 = net.getNodeByName('c2', 'c3')
	c4, c5 = net.getNodeByName('c4', 'c5')
	c0.setIP(ip='10.0.0.0', prefixLen=32)
	c1.setIP(ip='10.0.0.1', prefixLen=32)
	c2.setIP(ip='10.0.0.2', prefixLen=32)
	c3.setIP(ip='10.0.0.3', prefixLen=32)
	c4.setIP(ip='10.0.0.4', prefixLen=32)
	c5.setIP(ip='10.0.0.5', prefixLen=32)
	c0.setMAC(mac='00:00:00:00:00:00')
	c1.setMAC(mac='00:00:00:00:00:01')
	c2.setMAC(mac='00:00:00:00:00:02')
	c3.setMAC(mac='00:00:00:00:00:03')
	c4.setMAC(mac='00:00:00:00:00:04')
	c5.setMAC(mac='00:00:00:00:00:05')

	## To fix "network is unreachable"
	s0.setDefaultRoute(intf='s0-eth0')
	c0.setDefaultRoute(intf='c0-eth0')
	c1.setDefaultRoute(intf='c1-eth0')
	c2.setDefaultRoute(intf='c2-eth0')
	c3.setDefaultRoute(intf='c3-eth0')
	c4.setDefaultRoute(intf='c4-eth0')
	c5.setDefaultRoute(intf='c5-eth0')

	net.start()

  # run_tnodes([t11, t21, t31])
	run_servers([s0])
	time.sleep(1)
	run_clients([c0])
	# run_clients([c0, c1])
	run_clients([c0, c1, c2, c3, c4, c5])

	CLI(net)
	net.stop()
