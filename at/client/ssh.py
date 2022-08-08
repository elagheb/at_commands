import paramiko
import logging

logging.basicConfig(format='%(asctime)s - %(name)s::%(levelname)s::%(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler)


class AuthenticationFailure(Exception):
    pass


class CommandExecutionFailure(Exception):
    pass


class ConnectionFailure(Exception):
    pass


class Ssh(object):

    def __init__(self):
        self._connected = False
        self.client = paramiko.SSHClient()

    def connect_to(self, hostname, username, password, alias, port=22, timeout=50):
        """
        used to connect host machine to remote server using ssh

        :param string hostname:
        :param string username:
        :param string password:
        :param string alias:
        :param int port: port on which connection to server will be established (22 by default)
        :param int timeout: connection timeout (50 s by default)

        :return: bool indicating if connection is established or not
        """
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.hostname = hostname
        logger.info('client configured')
        logger.debug('connecting to remote machine : {}  with username : {} on port : {}'.format(
            hostname, username, port
        ))
        try:
            self.client.connect(hostname=self.hostname, username=username, password=password, port=port,
                                timeout=timeout)
        except paramiko.ssh_exception.AuthenticationException as e:
            logger.debug('Paramiko Exception :{}'.format(e))
            raise AuthenticationFailure('authentication Failed on remote {}'.format(self.hostname), e)
        except paramiko.ssh_exception.SSHException as e:
            logger.debug('Paramiko exception: {}'.format(e))
            raise ConnectionFailure('connection Failed to remote {}'.format(self.hostname), e)
        self._connected = True
        return self._connected

    def send_command(self, command):
        raise NotImplementedError

    def file_exists(self, file):
        raise NotImplementedError

    def execute(self, command, timeout=50):
        """
        run command on remote server and return the output

        :param str command: command to execute on remote
        :param int timeout: time to wait for command output (default 50s)

        :return: remote command output
        """
        if self._connected:
            try:
                logger.info('executing command : {}'.format(command))
                stdin, stdout, stderr = self.client.exec_command(command=command, timeout=timeout)
                logger.debug('output form {} : {}'.format(command, stdout.readlines))
                return stdout.readlines()
            except Exception as e:
                logger.debug("command execution Failure : {}".format(e))
                raise CommandExecutionFailure('command {} failure'.format(command), e)
        raise CommandExecutionFailure('command can not be executed need to connect before')

    def disconnect(self):
        """
        close ssh connection on remote

        :return:
        """
        if self._connected:
            logger.debug('disconnecting from {}'.format(self.hostname))
            try:
                self.client.close()
            except Exception as e:
                logger.info('disconnection Failure, raised exception : {}'.format(e))
                raise ('disconnection Failure, raised exception : {}'.format(e))
            finally:
                self._connected = False
                self.client = None
