import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import scipy, math
from scipy import special

from debug_utils import *

def G(z, x=None, type_=None):
	if x is None:
		return scipy.special.gamma(z)
	else:
		if type_ == 'lower':
			return float(scipy.special.gammainc(z, x)*G(z) )
		elif type_ == 'upper':
			# return (1 - scipy.special.gammainc(z, x) )*G(z)
			return float(scipy.special.gammaincc(z, x)*G(z) )

def EW_MMc(ar, EX, c):
	ro = ar*EX/c
	C = 1/(1 + (1-ro)*G(c+1)/(c*ro)**c * sum([(c*ro)**k/G(k+1) for k in range(c) ] ) )
	# EN = ro/(1-ro)*C + c*ro
	return C/(c/EX - ar)

# def EW_MGc(ar, EX, EX2, c):
#		CV = math.sqrt(EX2 - EX**2)/EX
#		return (1 + CV**2)/2 * EW_MMc(ar, EX, c)

def EW_MMc_wGamma(ar, EX, c):
	ro = ar*EX/c
	ro_ = c*ro
	c_times_ro__power_c = (c*ro)**c
	x = (1-ro) * c*math.exp(ro_)*G(c, ro_, 'upper')/c_times_ro__power_c
	Prqing = 1/(1 + (1-ro) * x)

	return Prqing/(c/EX - ar) #, Prqing

## Derived from Allen-Cunneen approximation
## [Arnold Allen, Queueing models of computer systems]
## [Whitt, Approximations for the G/G/m queue]
def EW_MGc(ar, EX, EX2, c):
	log(DEBUG, "", ar=ar, EX=EX, EX2=EX2, c=c)

	ro = ar*EX/c
	if ro >= 1:
		log(DEBUG, "Avg system load should be < 1", ro=ro)
		return None
	# CoeffVar = math.sqrt(EX2 - EX**2)/EX
	# return (1 + CoeffVar**2)/2 * MMc_EW_Prqing(ar, EX, c)
	EW_MMc_ = EW_MMc_wGamma(ar, EX, c)
	return (1 + (EX2 - EX**2)/EX**2)/2 * EW_MMc_

def ET_MGc(ar, EX, EX2, c):
	EW_MGc_ = EW_MGc(ar, EX, EX2, c)
	if EW_MGc_ is None:
		return None
	return EX + EW_MGc_

def EW_DGc(ar, EX, EX2, c):
	log(DEBUG, "", ar=ar, EX=EX, EX2=EX2, c=c)

	ro = ar*EX/c
	if ro >= 1:
		log(DEBUG, "Avg system load should be < 1", ro=ro)
		return None

	EW_MMc_ = EW_MMc_wGamma(ar, EX, c)
	return (EX2 - EX**2)/EX**2/2 * EW_MMc_

def ET_DGc(ar, EX, EX2, c):
	EW_DGc_ = EW_DGc(ar, EX, EX2, c)
	if EW_DGc_ is None:
		return None
	return EX + EW_DGc_

def binary_search(l, target, get_value):
	r = l + 0.01
	while True:
		val = get_value(r)
		if val is None:
			r /= 1.5
		elif val < target:
			r *= 2
		else:
			break

	# while get_value(r) < target:
	# 	log(DEBUG, "r= {}, get_value(r)= {}".format(r, get_value(r)))
	# 	r *= 1.1
	log(DEBUG, "Starting", l=l, r=r)

	while (r - l > 0.01):
		m = (l + r)/2
		# log(DEBUG, "", m=m)
		if get_value(m) < target:
			l = m
		else:
			r = m

	return (l + r)/2

def ar_MGc_forGivenET(EX, EX2, c, ET):
	return binary_search(0, ET, lambda ar: ET_MGc(ar, EX, EX2, c))

def ar_DGc_forGivenET(EX, EX2, c, ET):
	return binary_search(0, ET, lambda ar: ET_DGc(ar, EX, EX2, c))

if __name__ == '__main__':
	EX, EX2 = 3, 9
	c = 2
	ar = 0.1
	ET = ET_DGc(ar, EX, EX2, c)
	while ET is not None:
		log(DEBUG, "", ar=ar, ET=ET)
		ar += 0.1
		ET = ET_DGc(ar, EX, EX2, c)
