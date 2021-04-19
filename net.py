#!/usr/bin/python

from mininet.log import setLogLevel, info #, error
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.cli import CLI

from debug_utils import *

class MyTopo(Topo):
	def __init__(self):
		Topo.__init__(self)

		c0 = self.addHost('c0')
		c1 = self.addHost('c1')
		s0 = self.addHost('s0')
		sw0 = self.addSwitch('sw0')

		link_opts = dict(bw=1000, delay='1ms', loss=0, max_queue_size=1000, use_htb=True)
		self.addLink(c0, sw0, **link_opts)
		self.addLink(c1, sw0, **link_opts)
		self.addLink(s0, sw0, **link_opts)

def run_tnodes(hosts):
	"""
	for host in hosts:
		host.cmdPrint('pwd')
		host.sendCmd('./run.sh %s &' % host.name)
	"""
	popens = {}
	for host in hosts:
		host.cmdPrint('pwd')
		popens[host] = host.popen('./run.sh %s' % host.name)
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

if __name__ == '__main__':
	setLogLevel('info')
	net = Mininet(topo=MyTopo(), link=TCLink, controller=OVSController)

	c0, c1 = net.getNodeByName('c0', 'c1')
	c0.setIP(ip='10.0.0.0', prefixLen=32)
	c1.setIP(ip='10.0.0.1', prefixLen=32)
	c0.setMAC(mac='00:00:00:00:00:00')
	c1.setMAC(mac='00:00:00:00:00:01')

	s0 = net.getNodeByName('s0')
	s0.setIP(ip='10.0.1.0', prefixLen=32)
	s0.setMAC(mac='00:00:00:00:01:00')

	## To fix "network is unreachable"
	c0.setDefaultRoute(intf='c0-eth0')
	c1.setDefaultRoute(intf='c1-eth0')
	s0.setDefaultRoute(intf='s0-eth0')

	net.start()
  # run_tnodes([t11, t21, t31])
	CLI(net)
	net.stop()
