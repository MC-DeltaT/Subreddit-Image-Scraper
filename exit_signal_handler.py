import logging
import platform
import signal
import sys



_logger = logging.getLogger()


_exit_signos = {signal.SIGTERM, signal.SIGINT}
_signalled = False


def _signal_handler(signo, frame):
	global _signalled

	_logger.debug("Exit signal caught")
	if _signalled:
		_logger.debug("Application already terminating")
	else:
		_signalled = True
		_logger.debug("Initiating termination with sys.exit()")
		sys.exit(0)


def block_signals():
	if platform.system() == "Linux":
		_logger.debug("Blocking signals")
		# Only available on Unix-like environments.
		signal.pthread_sigmask(signal.SIG_BLOCK, _exit_signos)
	pass


def unblock_signals():
	if platform.system() == "Linux":
		_logger.debug("Unblocking signals")
		# Only available on Unix-like environments.
		signal.pthread_sigmask(signal.SIG_UNBLOCK, _exit_signos)
	pass
	

for _signo in _exit_signos:
	signal.signal(_signo, _signal_handler)
