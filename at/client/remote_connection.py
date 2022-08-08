

from .ssh import ssh
import pysftp
import os
import logging
import platform
from .exceptions import *
from .os_handler import *

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_connector = ssh()


class RemoteConnection(object):
    """

    """

    def __init__(self, hostname, username, password, processes_to_kill=None):
        self._hostname = hostname
        self._username = username
        self._password = password
        self.processes_to_kill = ['QXDM', 'PUTTY', 'ttermpro', 'ATCom', 'python']
        if processes_to_kill is not None:
            for process in processes_to_kill:
                self.processes_to_kill.append(process)
        self._ue_connection = None
        self._os_version = None
        self._firewall_on = True
        self._remote_files_dir = '/home/' + str(self._username) + '/pyro_test/'

    def open_port_connection(self):
        port_opened = self._os_version.open_firewall_port(port=9093)
        if port_opened:
            logger.info(
                'port {} opened on ue pc for taf.ue.plugin.at Pyro application connection'.
                    format(9093))
            return port_opened
        logger.debug('Firewall port opening exception, something wrong happened on the ue pc end')
        raise FirewallRuleException('Firewall {} port not opened'.format(9093))

    def close_port_connection(self):
        port_opened = self._os_version.close_firewall_port(9093)
        if port_opened:
            logger.info(
                'port 9093 closed on ue pc for taf.ue.plugin.at Pyro application connection')
            return port_opened
        logger.debug('Firewall port closing exception, something wrong happened on the ue pc end')
        raise FirewallRuleException('Firewall 9093 port closing error')

    def turn_on_firewall(self):
        if not self._firewall_on:
            self._firewall_on = self._os_version.turn_firewall_on()
            if self._firewall_on:
                logger.info('firewall is on on ue pc')
                return self._firewall_on
            raise FirewallRuleException('firewall turning on didn\'t turn as expected')

    def turn_off_firewall(self):
        self._firewall_on = self._os_version.is_firewall_active()
        if self._firewall_on:
            self._firewall_on = not self._os_version.turn_firewall_off()
            if not self._firewall_on:
                logger.info('firewall is off on ue pc')
                return self._firewall_on
            raise FirewallRuleException('firewall states are not off')

    def kill_processes(self):
        _not_killed = []
        logger.info('processes to kill are {}'.format(self.processes_to_kill))
        for process in self.processes_to_kill:
            try:
                result = _connector.execute \
                    (command=self._os_version.kill_process(process),
                     timeout=45,
                     connection='PYRO')
                logger.info('Killing process {} result: {}'.format(process, result))
                self.processes_to_kill.remove(process)
            except Exception as e:
                logger.debug('a problem was encountered while killing {} process'.format(process))
                self.processes_to_kill.remove(process)
                _not_killed.append(
                    {e: process}
                )
                pass
        if len(_not_killed) > 0:
            logger.info("this processes weren't killed or found {}".format(
                _not_killed
            ))
            return _not_killed
        return True

    def get_os_handler(self):
        self._os_version = _connector.execute(command='python -c "import platform;print(platform.system())"',
                                              timeout=45,
                                              connection='PYRO')
        logger.info('result of command is  :{}'.format(self._os_version))
        self._os_version = self._os_version.strip('\r\n').lower()
        logger.info('OS version on {} machine is : {}'.format(
            self._hostname, self._os_version
        ))
        if 'indows' in self._os_version:
            self._os_version = WindowsHandler(connection=_connector, conn_alias='PYRO')
            return self._os_version
        if 'linux' in self._os_version:
            self._os_version = LinuxHandler(connection=_connector, conn_alias='PYRO')
            return self._os_version

    def connect(self):
        try:
            self._ue_connection = _connector.connect_to(
                hostname=self._hostname,
                username=self._username,
                password=self._password,
                alias='PYRO'
            )
            self._ue_connection = True
        except Exception as e:
            raise e
        logger.info('connection established to {}'.format(self._hostname))
        return self._ue_connection

    def send_files(self, localpaths, remotepaths):
        """
        use ssh to send files ( ssh.upload_file()) method
        :param localpaths:
        :param remotepaths:
        :return:
        """
        for path in localpaths:
            if not os.path.exists(path):
                raise IOError(" {} doesn't exist on local machine".format(path))
        for localpath in localpaths:
            _connector.upload_file(
                local_path=localpath,
                remote_path=remotepaths,
                connection='PYRO')
            logger.debug('file {} send successfully to ue pc'.format(localpath))
        return True

    def send_files_to_server(self, localpaths):
        """
        send files to remote
        # bug encountered when sending from windows machine OSError Failure (related to confirm=True)
        :param localpaths: a list of all files to send to remote
        :param remotepath: list of remote paths
        :return:
        """
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        for path_to_file in localpaths:
            if not os.path.exists(path_to_file):
                raise IOError('File Not found on Local machine {}'.format(path_to_file))

        with pysftp.Connection(self._hostname, username=self._username, password=self._password, cnopts=cnopts) as sftp:
            for path_to_file in localpaths:
                logger.info('sending file : {} to {}'.format(path_to_file,
                                                             self._remote_files_dir))
                if not sftp.exists(self._remote_files_dir):
                    sftp.chdir('/home/' + str(self._username) + '/')
                    logger.info('creating directory : {}'.format('/home/' + str(self._username) + 'pyrotest'))
                    sftp.mkdir(remotepath='pyro_test', mode=744)
                try:
                    sftp.chdir('/home/' + str(self._username))
                    logger.info('current remote directory :{}'.format(sftp.getcwd()))
                    sftp.chdir(self._remote_files_dir)
                    sftp.put(path_to_file, confirm=False)
                    logger.info('file {} sent to ue pc'.format(path_to_file))
                except (IOError, OSError) as e:
                    raise FileTransmissionException('File {} not transmitted to {}, encountered an {} exception'.format(
                        self._hostname, path_to_file, e
                    ))
            logger.info('all files sent')
        return

    def download(self):
        pass

    def remove_remote_files(self, files):
        try:
            _connector.execute(
                command='rm *.py *.pyc',
                timeout=30,
                connection='PYRO'
            )
            remote_files = _connector.execute(
                command='ls -lrt {}'.format(self._remote_files_dir),
                timeout=30,
                connection='PYRO'
            )
            for file in files:
                if file in remote_files:
                    raise RemoteFileCleaningException('file {} is present in {}'.format(
                        file, self._remote_files_dir
                    ))
        except (IOError, OSError) as e:
            raise RemoteFileCleaningException('something went wrong when removing python files on ue pc')
        logger.info('all files where removed')
        return True

    def get_server_dir_path(self):
        current_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        for entry in os.listdir(current_directory):
            if os.path.isdir(os.path.join(current_directory, entry)):
                if entry == 'destination':
                    _directory = os.path.join(current_directory, entry)
                    return _directory

    def get_server_files_paths(self):
        paths = []
        _directory = self.get_server_dir_path()
        logger.info('server dir path is {}'.format(_directory))
        for entry in os.listdir(_directory):
            # print('entry is {}'.format(entry))
            if entry.split('.')[-1] == 'py':
                if os.path.isfile(os.path.join(str(_directory), str(entry))):
                    paths.append(
                        os.path.join(_directory, entry)
                    )
        logger.info('paths of server files are {}'.format(paths))
        return paths

    def return_remote_files_paths(self):
        files = self.get_server_files_paths()
        files = [str(self._remote_files_dir) + str(file.split('/')[-1]) for file in files]
        return files

    def start_remote_server(self, com_id):
        try:

            result = _connector.execute(
                command="cygpath.exe -w /home/{}/pyro_test/".format(self._username),
                connection='PYRO'
            )

            result = result.strip()
            logger.info('path of cygwin is :{}'.format(result))

            logger.info("launching command cmd /C 'python {}server.py {}'".format(
                result, self._hostname
            ))
            _connector.send_command(
                command="cmd /C 'python {}server.py {} {}'".format(
                    result, self._hostname, com_id
                ), connection='PYRO')
        except Exception as e:
            raise (e)
        logger.info('remote sever started')
        return True

    def set_pyro_log_path_on_server(self):
        _connector.send_command(
            command=self._os_version.set_pyro_log_path(self._remote_files_dir),
            connection='PYRO'
        )
        logger.info('pyro log path on ue pc set to {}'.format(self._remote_files_dir))
        return True

    def save_firewall_rules(self):
        path = self._os_version.save_firewall_rules(self._remote_files_dir)
        logger.info('firewall rules saved to {}'.format(path))
        return path

    def save_processes(self):
        processes_path = self._os_version.save_processes(self._remote_files_dir)
        logger.info('processes saved to {}'.format(processes_path))
        return processes_path

    def activate_telnet_service(self):
        try:
            self.telnet_state = self._os_version.is_service_active('TelnetClient')
            if self.telnet_state is False:
                logger.info('tlenetclient is not active on uepc')
                self.telnet_state = self._os_version.activate_service('TelnetClient')
                if not self.telnet_state:
                    raise ServiceOperationException('TelnetClient activation error')
                logger.info('telnetclient activated on ue pc ')
                return self.telnet_state
            return self.telnet_state
        except NotImplementedError:
            pass
        except Exception as e:
            raise e

    def deactivate_telnet_service(self):
        try:
            if self.telnet_state:
                self.telnet_state = self._os_version.deactivate_service('TelnetClient')
                if self.telnet_state:
                    raise ServiceOperationException('TelnetClient deactivation error')
                logger.info('telnet client deactivated on ue pc')
                return self.telnet_state
            return self.telnet_state
        except NotImplementedError:
            pass
        except Exception as e:
            raise e

    def is_port_listening(self, port):
        ports = _connector.execute(
            command=self._os_version.is_port_listening(port=port),
            timeout=55,
            connection='PYRO')
        if str(port) in ports:
            logger.info('port is 9093 is open and listenning for connection on ue pc')
            return True
        return False

    @staticmethod
    def set_pyro_log_path_for_client():
        log_path = os.getcwd()
        if 'windows' in platform.system().lower():
            os.system(WindowsHandler.set_pyro_log_path(log_path))
        else:
            os.system(LinuxHandler.set_pyro_log_path(log_path))
        logger.info('pyro log path on client set to {}'.format(log_path))
        return log_path

    def disconnect(self):
        if self._ue_connection is not None:
            _connector.disconnect(connection='PYRO')
            self._ue_connection = None
            logger.info('{} connection terminated '.format(self._hostname))
        return self._ue_connection
