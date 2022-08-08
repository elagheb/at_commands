from __future__ import print_function
import Pyro4
import logging
import sys
from .serial_connector import Connector
from .commands.common.at_mobile_controller import *
from .commands.common.at_network_handler import *
import os
import functools

current_dir = os.getcwd()
logging.basicConfig(filename=current_dir + '/server.log',
                    format='%(asctime)s - %(name)s::%(levelname)s::%(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

AT_VERSION = '0.1'


class ATServer(object):
    PYRO_SEREVR_NAME = 'ATServer'

    def __init__(self, hostname, com_id):
        self._hostname = hostname
        self.connector = Connector(com_id=com_id)
        self._prepared = False
        self.enabled = False
        self.supported_commands = self.get_supported_commands()
        self.exceptions = []

    def checker(command, require_cfun_activation=True):
        def decorator_checker(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                value = ''
                if command in args[0].supported_commands():
                    if require_cfun_activation:
                        if args[0].enabled:
                            try:
                                value = func(*args, **kwargs)
                            except Exception as e:
                                args[0].exceptions.append({command: e})
                                logger.debug('exception encountered {} while running command {}'.format(
                                    e, command
                                ))
                                pass
                        else:
                            logger.debug('{} require cfun activation'.format(command))

                else:
                    logger.debug('{} not supported'.format(command))
                return value

            return wrapper

        return decorator_checker

    def get_supported_commands(self):
        try:
            self.supported_commands = CLAC(self.connector).read()
        except Exception as e:
            self.exceptions.append({CLAC.COMMAND: e})
            pass
        return self.supported_commands

    @Pyro4.expose
    @checker(CPIN.COMMAND)
    def read_pin_status(self):
        return CPIN(self.connector, timeout=180).read()

    @Pyro4.expose
    @checker(CPAS.COMMAND)
    def report_phone_activity_status(self):
        return CPAS(self.connector, timeout=180).get()

    @Pyro4.expose
    @checker(CSQ.COMMAND)
    def get_signal_quality(self):
        return CSQ(self.connector, timeout=50).get()

    @Pyro4.expose
    @checker(ATI.COMMAND)
    def get_product_informations(self):
        return ATI(self.connector, timeout=60).get()

    @Pyro4.expose
    @checker(CREG.COMMAND)
    def get_network_registration_params(self):
        return CREG(self.connector, timeout=180).read()

    @checker(COPS.COMMAND)
    @Pyro4.expose
    def set_rat_mode(self, rat='AUTO', mcc=0, mnc=0):
        if rat.upper() not in {'AUTO', 'LTE', 'NR_LTE', 'NR'}:
            raise ValueError(' rat value should be one of AUTO, LTE, NR_LTE or NR')
        return COPS(self.connector).set(rat=COPS.rat, mcc=mcc, mnc=mnc)

    @Pyro4.expose
    @checker(CGATT.COMMAND)
    def attach(self):
        return CGATT(self.connector).set(CGATT.ATTACH)

    @Pyro4.expose
    def detach(self):
        return CGATT(self.connector).set(CGATT.DETACH)

    @Pyro4.expose
    def get_ue(self):
        self.enabled = True
        return CFUN(self.connector, timeout=20).set(level=CFUN.ACTIVATE)

    @Pyro4.expose
    def release_ue(self):
        return CFUN(self.connector, timeout=20).set(level=CFUN.DEACTIVATE)

    @staticmethod
    @Pyro4.expose
    def at_version():
        return AT_VERSION

    def _isrunning(self):
        return self.running

    @Pyro4.expose
    def shutdown(self):
        self.daemon.shutdown()
        logger.info("server shutdown complete")

    def start(self):
        Pyro4.config.SOCK_REUSE = True
        Pyro4.config.REQUIRE_EXPOSE = True
        with Pyro4.Daemon(
                host=self._hostname,
                port=9093
        ) as self.daemon:
            self.daemon.register(self, objectId=self.PYRO_SEREVR_NAME)
            self.running = True
            self.daemon.requestLoop(loopCondition=self._isrunning)
            logger.info('server up and running')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ATServer(hostname=sys.argv[1], com_id=sys.argv[2]).start()
    logger.info('server is running')