import abc
import logging
from .common.exceptions import ATCommandException

logger = logging.getLogger()
logger.addHandler(logging.NullHandler())


class AtCommand(metaclass=abc.ABCMeta):
    COMMAND = 'command'

    def __init__(self, serial_target, timeout):
        self.serial_target = serial_target
        self.timeout = timeout

    def read(self, read_char='?', message='Error while running command'):
        state = self.serial_target.run(command=self.COMMAND + read_char,
                                       timeout=self.timeout,
                                       exception=ATCommandException,
                                       message=message)
        return self.parse_output(state)

    @abc.abstractmethod
    def parse_error(self):
        raise NotImplementedError

    @abc.abstractmethod
    def parse_output(self, result):
        match = self.COMMAND[2:] + ':'
        for value in result:
            if match in value:
                return value.split(':')[-1]