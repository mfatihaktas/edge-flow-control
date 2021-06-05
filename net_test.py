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
		w0 = self.addHost('w0')
		w1 = self.addHost('w1')
		c0 = self.addHost('c0')
		c1 = self.addHost('c1')

		sw0 = self.addSwitch('sw0')

		cluster_link_opts = dict(bw=1000, delay='0.1ms', loss=0, max_queue_size=1000, use_htb=True)
		edge_link_opts = dict(bw=1000, delay='1ms', loss=0, max_queue_size=1000, use_htb=True)
		self.addLink(w0, sw0, **cluster_link_opts)
		self.addLink(w1, sw0, **cluster_link_opts)
		self.addLink(s0, sw0, **cluster_link_opts)
		self.addLink(c0, sw0, **edge_link_opts)
		self.addLink(c1, sw0, **edge_link_opts)

def run_workers(w_l):
	popens = {}
	for i, w in enumerate(w_l):
		w.cmdPrint('pwd')
		popens[w] = w.popen('./run.sh w %s' % i)
		log(DEBUG, "Started w{}".format(i))

if __name__ == '__main__':
	setLogLevel('info')
	net = Mininet(topo=MyTopo(), link=TCLink, controller=OVSController)

	s0 = net.getNodeByName('s0')
	s0.setIP(ip='10.0.1.0', prefixLen=32)
	s0.setMAC(mac='00:00:00:00:01:00')

	w0 = net.getNodeByName('w0')
	w0.setIP(ip='10.0.2.0', prefixLen=32)
	w0.setMAC(mac='00:00:00:00:02:00')
	w1 = net.getNodeByName('w1')
	w1.setIP(ip='10.0.2.1', prefixLen=32)
	w1.setMAC(mac='00:00:00:00:02:01')

	c0, c1 = net.getNodeByName('c0', 'c1')
	c0.setIP(ip='10.0.0.0', prefixLen=32)
	c1.setIP(ip='10.0.0.1', prefixLen=32)
	c0.setMAC(mac='00:00:00:00:00:00')
	c1.setMAC(mac='00:00:00:00:00:01')

	## To fix "network is unreachable"
	s0.setDefaultRoute(intf='s0-eth0')
	w0.setDefaultRoute(intf='w0-eth0')
	c0.setDefaultRoute(intf='c0-eth0')
	c1.setDefaultRoute(intf='c1-eth0')

	net.start()
	run_workers([w0, w1])
	CLI(net)
	net.stop()
