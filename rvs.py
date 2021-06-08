import random, scipy, math
import scipy.integrate
import scipy.stats
import numpy as np

from math_utils import *
from debug_utils import *
from plot_utils import *

class RV(): # Random Variable
	def __init__(self, l, u):
		check(l <= u, "l= {} should be < u= {}.".format(l, u))
		self.l = l
		self.u = u

class Exp(RV):
	def __init__(self, mu, D=0):
		super().__init__(l=D, u=np.inf)
		self.D = D
		self.mu = mu

	def __repr__(self):
		if self.D == 0:
			return r'Exp(\mu={})'.format(self.mu)
		return r'{} + Exp(\mu={})'.format(self.D, self.mu)

	def tail(self, x):
		if x <= self.l:
			return 1
		return math.exp(-self.mu*(x - self.D) )

	def cdf(self, x):
		if x <= self.l:
			return 0
		return 1 - math.exp(-self.mu*(x - self.D) )

	def pdf(self, x):
		if x <= self.l:
			return 0
		return self.mu*math.exp(-self.mu*(x - self.D) )

	def mean(self):
		return self.D + 1/self.mu

	def var(self):
		return 1/self.mu**2

	def moment(self, i):
		return G(i + 1) / self.mu**i

	def laplace(self, s):
		check(self.D == 0, "Defined only for D = 0.")
		return self.mu/(s + self.mu)

	def sample(self):
		return self.D + random.expovariate(self.mu)

class TPareto(RV): # Truncated
	def __init__(self, l, u, a):
		super().__init__(l=l, u=u)
		self.a = a

	def __repr__(self):
		return "TPareto(l= {}, u= {}, a= {})".format(self.l, self.u, self.a)

	def to_latex(self):
		return r'TPareto($\min= {}$, $\max= {}$, $\alpha= {}$)'.format(self.l, self.u, self.a)

	def pdf(self, x):
		if x < self.l: return 0
		elif x >= self.u: return 0
		else:
			return self.a*self.l**self.a * 1/x**(self.a+1) / (1 - (self.l/self.u)**self.a)

	def	inverse_pdf(self, p):
		check(0 <= p <= 1, "Prob p= {}, has to be lie in [0, 1].".format(p))

		y = p * (1 - math.pow(self.l/self.u, self.a)) / self.a / math.pow(self.l, self.a)
		return math.pow(y, -1/(self.a + 1))

	def cdf(self, x):
		if x < self.l: return 0
		elif x >= self.u: return 1
		else:
			return (1 - (self.l/x)**self.a)/(1 - (self.l/self.u)**self.a)

	def tail(self, x):
		return 1 - self.cdf(x)

	def mean(self):
		return self.moment(1)

	def std(self):
		return math.sqrt(self.moment(2) - self.mean()**2)

	def moment(self, k):
		if k == self.a:
			return math.log(self.u/self.l)
		else:
			try:
				r = self.l/self.u
				return self.a*self.l**k/(self.a-k) * \
							 (1 - r**(self.a-k))/(1 - r**self.a)
			except:
				# x = math.log(self.l) - math.log(self.u)
				# return self.a*self.l**k/(self.a-k) * \
				#				(1 - math.exp((self.a-k)*x) )/(1 - math.exp(self.a*x) )
				r = self.l/self.u
				log(INFO, "", r=r, a=self.a, k=k)
				return self.a*self.l**k/(self.a-k) * \
							 (r**k - r**self.a)/(r**k - r**(self.a + k) )

	def sample(self):
		r = random.uniform(0, 1)
		s = self.l*(1 - r*(1-(self.l/self.u)**self.a) )**(-1/self.a)
		if s < self.l or s > self.u:
			log(ERROR, "illegal sample! s= {}".format(s) )
			return None
		return s

def binary_search(l, target, get_value):
	r = (l + 1) * 10**3
	while get_value(r) < target:
		r *= 10
	log(DEBUG, "Starting", l=l, r=r)

	while (r - l > 0.01):
		m = (l + r)/2
		# log(DEBUG, "", m=m)
		if get_value(m) < target:
			l = m
		else:
			r = m

	return (l + r)/2

class TPareto_forAGivenMean(TPareto):
	def __init__(self, l, a, mean):
		u = binary_search(float(l), mean, lambda u: TPareto(l, u, a).mean())
		super().__init__(l, u, a)

class DiscreteRV():
	def __init__(self, p_l, v_l, norm_factor=1):
		self.p_l = p_l
		self.v_l = v_l
		self.norm_factor = norm_factor

		self.dist = scipy.stats.rv_discrete(name='discrete', values=(v_l, p_l))

	def __repr__(self):
		return 'DiscreteRV(' + '\n\t' + \
			'p_l= {}'.format(self.p_l) + '\n\t' + \
			'v_l= {}'.format(self.v_l) + '\n\t' + \
			'norm_factor= {}'.format(self.norm_factor) + ')'

	def mean(self):
		return self.dist.mean() / self.norm_factor

	def sample(self):
		return self.dist.rvs() / self.norm_factor

class Dolly(RV):
	## Kristen et al. A Better Model for Job Redundancy: Decoupling Server Slowdown and Job Size
	def __init__(self):
		RV.__init__(self, l=1, u=12)

		self.v = np.arange(1, 13)
		self.p = [0.23, 0.14, 0.09, 0.03, 0.08, 0.1, 0.04, 0.14, 0.12, 0.021, 0.007, 0.002]
		self.dist = scipy.stats.rv_discrete(name='dolly', values=(self.v, self.p) )

	def __str__(self):
		return "Dolly(l={}, u={})".format(self.l, self.u)

	def mean(self):
		return self.dist.mean()

	def pdf(self, x):
		return self.dist.pmf(x) if (x >= self.l and x <= self.u) else 0

	def cdf(self, x):
		if x < self.l:
			return 0
		elif x > self.u:
			return 1
		return float(self.dist.cdf(x) )

	def sample(self):
		# u = random.uniform(0, 1)
		return self.dist.rvs() # + u/100

class SumOfRVs(RV):
	def __init__(self, rv_l):
		super().__init__(l=sum(rv.l for rv in rv_l), u=sum(rv.u for rv in rv_l))
		self.rv_l = rv_l

	def __repr__(self):
		return r'SumOfRVs(rv_l= {})'.format(self.rv_l)

	def sample(self):
		return sum(rv.sample() for rv in self.rv_l)

class CycleOverRVs(RV):
	def __init__(self, rv_l):
		super().__init__(l=min(rv.l for rv in rv_l), u=max(rv.u for rv in rv_l))
		self.rv_l = rv_l

		self.cur_i = 0

	def __repr__(self):
		return r'CycleOverRVs(rv_l= {})'.format(self.rv_l)

	def sample(self):
		s = self.rv_l[self.cur_i].sample()
		self.cur_i = self.cur_i % len(self.rv_l)
		return s

class TruncatedX(RV):
	def __init__(self, X, a=None, b=None):
		check(a is not None or b is not None, "Either lower or upper boundary should be given.")

		l = X.l if a is None else max(X.l, a)
		u = X.u if b is None else min(X.u, b)
		super().__init__(l, u)
		self.X = X

		self.Pr_X_leq_a = X.cdf(a) if a is not None else 0
		self.Pr_X_leq_b = X.cdf(b) if b is not None else 1
		self.Pr_diff = self.Pr_X_leq_b - self.Pr_X_leq_a
		# log(INFO, "", Pr_X_leq_a=self.Pr_X_leq_a, Pr_X_leq_b=self.Pr_X_leq_b, Pr_diff=self.Pr_diff)

	def __repr__(self):
		return r'TruncatedX(X= {})'.format(self.X)

	def pdf(self, x):
		return self.X.pdf(x) / self.Pr_diff

	def cdf(self, x):
		return (self.X.cdf(x) - self.Pr_X_leq_a) / self.Pr_diff

	def inverse_pdf(self, p):
		check(0 <= p <= 1, "Prob p= {}, has to lie in [0, 1].".format(p))

		return self.X.inverse_pdf(p * self.Pr_diff + self.Pr_X_leq_a)

	def moment(self, i):
		r, abserr = scipy.integrate.quad(lambda y: y**i*self.X.pdf(y), self.l, self.u)
		return r / self.Pr_diff

	def sample(self):
		u = random.uniform(0, 1)
		return self.inverse_pdf(u)

## Pr{a < X < b}
def Prob(X, a=None, b=None):
	if a is not None and b is not None:
		check(a < b, "a= {} < b= {} should have hold!".format(a, b))

	Pr_X_leq_a = X.cdf(a) if a is not None else 0
	Pr_X_leq_b = X.cdf(b) if b is not None else 1

	return Pr_X_leq_b - Pr_X_leq_a

## E[X^i | a < X < b]
def Moment(X, i, a=None, b=None):
	if a is None and b is None:
		return X.moment(i)

	TX = TruncatedX(X, a, b)
	return TX.moment(i)

def Mean(X, a=None, b=None):
	return Moment(X, 1, a, b)

def test_moment():
	X = Exp(1)
	EX = Mean(X)

	low, mid = 0.2, 0.5
	EX_low = Moment(X, 1, b=low)
	Pr_low = Prob(X, b=low)
	log(INFO, "", EX_low=EX_low, Pr_low=Pr_low)

	EX_mid = Moment(X, 1, a=low, b=mid)
	Pr_mid = Prob(X, a=low, b=mid)
	log(INFO, "", EX_mid=EX_mid, Pr_mid=Pr_mid)

	EX_high = Moment(X, 1, a=mid)
	Pr_high = Prob(X, a=mid)
	log(INFO, "", EX_high=EX_high, Pr_high=Pr_high)

	EX_total = Pr_low*EX_low + Pr_mid*EX_mid + Pr_high*EX_high
	log(INFO, "", EX=EX, EX_total=EX_total)

def CoeffVar(X, a=None, b=None):
	EX = Mean(X, a, b)
	EX2 = Moment(X, 2, a, b)
	log(INFO, "", EX=EX, EX2=EX2)
	StdX = math.sqrt(EX2 - EX**2)
	return StdX / EX

def plot_cdf_dolly():
	dolly = Dolly()
	fontsize = 14
	log(DEBUG, "", dolly_mean=dolly.mean())
	plot_cdf(dolly, plot.gca(), label=None, color='blue')
	plot.ylabel('Pr{S < s}', fontsize=fontsize)
	plot.xlabel('s', fontsize=fontsize)
	plot.title(r'$S \sim$ Dolly')
	plot.gcf().set_size_inches(4, 4)
	plot.savefig("plot_cdf_dolly.pdf", bbox_inches='tight')
	plot.gcf().clear()

if __name__ == '__main__':
	# test_moment()

	# rv = DiscreteRV(p_l=[1], v_l=[0.023])
	# s = rv.sample()
	# log(DEBUG, "", s=s, rv=rv)

	plot_cdf_dolly()
