import scipy, math

def G(z, x=None, type_=None):
	if x is None:
		return scipy.special.gamma(z)
	else:
		if type_ == 'lower':
			return float(scipy.special.gammainc(z, x)*G(z) )
		elif type_ == 'upper':
			# return (1 - scipy.special.gammainc(z, x) )*G(z)
			return float(scipy.special.gammaincc(z, x)*G(z) )
