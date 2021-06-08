import os, sys
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from math_utils import *
from debug_utils import *

# def EW_MGc(ar, ES, ES2, c):
#		CV = math.sqrt(ES2 - ES**2)/ES
#		return (1 + CV**2)/2 * EW_MMc(ar, ES, c)

def EW_MMc_wGamma(ar, ES, c):
	ro = ar*ES/c
	ro_ = c*ro
	c_times_ro__power_c = (c*ro)**c
	x = (1-ro) * c*math.exp(ro_)*G(c, ro_, 'upper')/c_times_ro__power_c
	Prqing = 1/(1 + (1-ro) * x)

	return Prqing/(c/ES - ar) #, Prqing

def EW_MMc(ar, ES, c):
	return EW_MMc_wGamma(ar, ES, c)
	# if c * 10 != int(c) * 10:
	# 	return EW_MMc_wGamma(ar, ES, c)
	# else:
	# 	ro = ar*ES/c
	# 	C = 1/(1 + (1-ro)*G(c+1)/(c*ro)**c * sum([(c*ro)**k/G(k+1) for k in range(c) ] ) )
	# 	# EN = ro/(1-ro)*C + c*ro
	# 	return C/(c/ES - ar)

## Derived from Allen-Cunneen approximation
## [Arnold Allen, Queueing models of computer systems]
## [Whitt, Approximations for the G/G/m queue]
def EW_MGc(ar, ES, ES2, c):
	log(DEBUG, "", ar=ar, ES=ES, ES2=ES2, c=c)

	ro = ar*ES/c
	if ro >= 1:
		log(DEBUG, "Avg system load should be < 1", ro=ro)
		return None
	# CoeffVar = math.sqrt(ES2 - ES**2)/ES
	# return (1 + CoeffVar**2)/2 * MMc_EW_Prqing(ar, ES, c)
	EW_MMc_ = EW_MMc(ar, ES, c)
	return (1 + (ES2 - ES**2)/ES**2)/2 * EW_MMc_

def ET_MGc(ar, ES, ES2, c):
	EW_MGc_ = EW_MGc(ar, ES, ES2, c)
	if EW_MGc_ is None or EW_MGc_ < 0:
		return None
	return ES + EW_MGc_

def EW_DGc(ar, ES, ES2, c):
	log(DEBUG, "", ar=ar, ES=ES, ES2=ES2, c=c)

	ro = ar*ES/c
	if ro >= 1:
		log(DEBUG, "Avg system load should be < 1", ro=ro)
		return None

	EW_MMc_ = EW_MMc(ar, ES, c)
	return (ES2 - ES**2)/ES**2/2 * EW_MMc_

def ET_DGc(ar, ES, ES2, c):
	EW_DGc_ = EW_DGc(ar, ES, ES2, c)
	if EW_DGc_ is None or EW_DGc_ < 0:
		return None
	return ES + EW_DGc_

def EW_GGc(EX, EX2, ES, ES2, c):
	log(DEBUG, "", EX=EX, EX2=EX2, ES=ES, ES2=ES2, c=c)

	ar = 1/EX
	ro = ar*ES/c
	if ro >= 1:
		log(DEBUG, "Avg system load should be < 1", ro=ro)
		return None

	EW_MMc_ = EW_MMc(ar, ES, c)
	log(DEBUG, "", EW_MMc_=EW_MMc_)
	return ((EX2 - EX**2)/EX**2 + (ES2 - ES**2)/ES**2)/2 * EW_MMc_

def ET_GGc(EX, EX2, ES, ES2, c):
	EW_GGc_ = EW_GGc(EX, EX2, ES, ES2, c)
	if EW_GGc_ is None or EW_GGc_ < 0:
		return None
	log(DEBUG, "", EW_GGc_=EW_GGc_)
	return ES + EW_GGc_

def binary_search(l, target, get_value):
	r = l + 0.01
	while True:
		# if r < 0.00001 or r > 1000:
		#		break

		val = get_value(r)
		log(DEBUG, "", val=val, r=r)
		if val is None:
			r /= 1.5
		elif val < target:
			r *= 2
		else:
			break
	log(DEBUG, "Starting", l=l, r=r)

	while (r - l > 0.01):
		m = (l + r)/2
		# log(DEBUG, "", m=m)
		if get_value(m) < target:
			l = m
		else:
			r = m

	return (l + r)/2

def ar_MGc_forGivenET(ES, ES2, c, ET):
	return binary_search(0, ET, lambda ar: ET_MGc(ar, ES, ES2, c))

def ar_DGc_forGivenET(ES, ES2, c, ET):
	return binary_search(0, ET, lambda ar: ET_DGc(ar, ES, ES2, c))

def ar_GGc_forGivenET(EX, EX2, ES, ES2, c, ET):
	return 1 / binary_search(0, ET, lambda EX: ET_GGc(EX, EX2, ES, ES2, c))

if __name__ == '__main__':
	ES, ES2 = 3, 9
	c = 2
	ar = 0.1
	ET = ET_DGc(ar, ES, ES2, c)
	while ET is not None:
		log(DEBUG, "", ar=ar, ET=ET)
		ar += 0.1
		ET = ET_DGc(ar, ES, ES2, c)
