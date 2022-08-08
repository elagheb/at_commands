import serial
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Connector(object):

    def __init__(self, com_id):
        self._history = []
        self._ser = None
        self._com_id = com_id

    def connect(self, b=115200):
        if self._ser:
            self.disconnect()
        self._ser = serial.Serial(
            port='COM' + str(self._com_id), baudrate=b, stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE,
            timeout=2, xonxoff=1)
        logger.info('CONNECTION ESTABLISHED TO COM PORT {}'.format(com_id))
        return self._ser

    def disconnect(self):
        if self._ser is None:
            return
        self._ser.close()
        self._ser = None
        logger.info('SERIAL DISCONNECTION COMPLETE')
        return self._ser

    def isERROR(self, output):
        for line in output:
            if "ERROR" in line:
                return True
        return False

    def read(self):
        lines = self._ser.readlines()
        output = [x.rstrip('\r\n') for x in lines]
        self._history += ["Read: " + value for value in output]
        return output

    def send_command(self, command):
        """
        send a command to com
        :param command:
        :return:
        """
        self._history.append("Send: " + command)
        self._ser.write(command + '\r\n')
        self._ser.flush()

    def read_command(self, timeout):
        """
        Read Serial Communication output
        :param timeout:
        :return:
        """
        output = []
        wait_until = datetime.now() + timedelta(seconds=int(timeout))
        while wait_until > datetime.now():
            output += self.read()
            if len(output) > 0:
                ok = ['OK' in value for value in output]
                if True in ok:
                    return output
                if self.isERROR(output):
                    return {'error': output}
            time.sleep(0.3)
        return output

    def execute(self, command, timeout=0.2):
        """
        execute command on COM port
        :param command:
        :param timeout:
        :return: a list of command lines output
        """
        self.send_command(command)
        logger.debug('executing command {} on COM Port{} with a timeout of {} sec'.format(
            command, self._com_id, timeout))
        output = self.read_command(timeout=timeout + 3)
        logger.debug('{} output:: {}'.format(command, output))
        return output

    def error_occurred(self, result):
        if 'error' in result or len(result) == 0:
            return True
        return False

    def run(self, command, timeout, exception, message):
        self.connect(self._com_id)
        output = self.execute(command=command, timeout=timeout)
        if self.error_occurred(output):
            logger.debug(
                message + ' {} output : {}'.format(command, output) + "exception encountered : {}".format(exception))
            raise exception(message + ' {} output : {}'.format(command, output))
        self.disconnect()
        return output
