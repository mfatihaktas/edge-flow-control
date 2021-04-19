import inspect, pprint, logging, os

# #################################  Log  ################################# #
DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3
CRITICAL = 4

logger = logging.getLogger('edge_cloud')
logger.setLevel(logging.DEBUG)

# FORMAT = '[%(asctime)s - %(funcName)10s()] %(msg)s'
# FORMAT = '[%(asctime)s - %(func_name)6s()] %(msg)s'
# FORMAT = '[%(filename)s:%(lineno)d] %(func_name):: %(msg)s'
FORMAT = '%(levelname)s] %(func_name)s: %(msg)s'
# logger.basicConfig(format=FORMAT, level=logging.DEBUG) # filename='c.log'
formatter = logging.Formatter(FORMAT)

sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)

level_log_m = {INFO: logger.info, DEBUG: logger.debug, WARNING: logger.warning, ERROR: logger.error, CRITICAL: logger.critical}

def log_to_file(filename):
	logger = logging.getLogger('edge_cloud')
	# for hdlr in logger.handlers[:]: # remove all old handlers
	# 	logger.removeHandler(hdlr)
	
	fh = logging.FileHandler(filename, mode='w')
	fh.setLevel(logging.DEBUG)
	fh.setFormatter(formatter)
	logger.addHandler(fh)

# conf_logger('e{}.log'.format(-1))

def get_extra():
	# caller_list = []
	# frame = inspect.currentframe().f_back
	# while frame.f_back:
	# 	caller_list.append('{0}'.format(frame.f_code.co_name))
	# 	frame = frame.f_back
	# callers =	 '/'.join(reversed(caller_list))
	
  # return {'func_name': '{0}'.format((inspect.currentframe().f_back.f_back).f_code.co_name)}
	frame = inspect.currentframe().f_back.f_back.f_code
	return {'func_name': '{}::{}'.format(os.path.split(frame.co_filename)[1], frame.co_name)}

def log(level: int, _msg_: str, **kwargs):
	level_log_m[level]("{}\n{}".format(_msg_, pstr(**kwargs)), extra=get_extra())

# Always log
def alog(level: int, _msg_: str, **kwargs):
	logger.critical("{}\n{}".format(_msg_, pstr(**kwargs)), extra=get_extra())

def pstr(**kwargs):
	s = ''
	for k, v in kwargs.items():
		s += "  {}: {}\n".format(k, pprint.pformat(v))
	return s

# ###############################  Assert  ############################### #
def check(condition: bool, _msg_: str, **kwargs):
	if not condition:
		logger.error("{}\n{}".format(_msg_, pstr(**kwargs)), extra=get_extra())
		raise AssertionError()

def assert_(_msg_: str, **kwargs):
	logger.error("{}\n{}".format(_msg_, pstr(**kwargs)), extra=get_extra())
	raise AssertionError()
