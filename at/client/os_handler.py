import logging
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WindowsHandler(object):

    def __init__(self, connection, conn_alias):
        self.connection = connection
        self.conn_alias = conn_alias

    def is_firewall_active(self):
        firewall_states = self.connection.execute(command='netsh advfirewall show allprofiles state',
                                                  timeout=45,
                                                  connection=self.conn_alias)
        states = 0
        for value in firewall_states.split('\n'):
            if len(value) > 0 and 'state' in value.lower():
                if 'on' in value.lower():
                    states += 1
        if states == 3:
            return True
        return False

    def is_port_in_open_ports(self, port):
        command = 'netsh firewall show config | findstr {}'.format(port)
        if str(port) in self.connection.execute(command=command, timeout=40, connection=self.conn_alias):
            logger.debug('port {} in command:{} result'.format(port, command))
            return True
        logger.debug('port {} not in firewall config result'.format(port))
        return False

    def open_firewall_port(self, port):
        command = 'netsh advfirewall firewall add rule name="AT Pyro Application connection" dir=in action=allow' + \
                  ' protocol=TCP localport={}'.format(port)
        verify_firewall_exist_command = 'netsh advfirewall firewall show rule name=all' + \
                                        ' | findstr "AT Pyro Application connection"'
        self.connection.execute(command, timeout=45, connection=self.conn_alias)
        firewall_rule = self.connection.execute(command=verify_firewall_exist_command, timeout=45,
                                                connection=self.conn_alias)
        logger.debug('firewall rule for AT Pyro Application connection : {}'.format(firewall_rule))
        if len(firewall_rule) > 0 and self.is_port_in_open_ports(port):
            return True
        return False

    def close_firewall_port(self, port):
        command = 'netsh advfirewall firewall delete rule name="AT Pyro Application connection"' + \
                  ' protocol=TCP localport={}'.format(port)
        output = self.connection.execute(command, timeout=45, connection=self.conn_alias)
        logger.debug('firewall port closing command result: {}'.format(output))
        if 'ok' in output.lower():
            return True
        return False

    def turn_firewall_off(self):
        self.connection.execute(
            command='netsh advfirewall set allprofiles state off',
            timeout=45,
            connection=self.conn_alias
        )
        logger.info('Firewall turned off')
        if self.is_firewall_active():
            return False
        return True

    def turn_firewall_on(self):
        self.connection.execute(
            'netsh advfirewall set allprofiles state off',
            timeout=45,
            connection=self.conn_alias
        )
        return self.is_firewall_active()

    def save_processes(self, remote_dir):
        command = 'tasklist > {}processes.txt'.format(remote_dir)
        self.connection.execute(command, timeout=45, connection=self.conn_alias)
        if self.connection.file_exists(remote_dir + 'processes.txt', connection=self.conn_alias):
            return '{}processes.txt'.format(remote_dir)

    def save_firewall_rules(self, remote_dir):
        command = 'netsh advfirewall firewall show rule name=all > {}firewall_rules.txt'.format(remote_dir)
        self.connection.execute(command, timeout=45, connection=self.conn_alias)
        if self.connection.file_exists(remote_dir + 'firewall_rules.txt', connection=self.conn_alias):
            return remote_dir + 'firewall_rules.txt'
        return

    @staticmethod
    def kill_process(process):
        return 'wmic PROCESS Where "CommandLine Like \'%{process}%\'" CALL TERMINATE'.format(process=process)

    def is_service_active(self, service):
        command = "cmd /C 'DISM /online /get-features /format:table | findstr {}'".format(service)
        result = self.connection.execute(command, timeout=65, connection=self.conn_alias)
        if 'enabled' in result.lower():
            return True
        return False

    def activate_service(self, service):
        command = "cmd /C 'DISM /online /enable-feature /featurename:{} /NoRestart'".format(service)
        self.connection.execute(command, timeout=65, connection=self.conn_alias)
        return self.is_service_active(service)

    def deactivate_service(self, service):
        command = "cmd /C 'DISM /online /disable-feature /featurename:{} /NoRestart'".format(service)
        time.sleep(5)
        self.connection.execute(command, timeout=65, connection=self.conn_alias)
        return self.is_service_active(service)

    @staticmethod
    def is_port_listening(port):
        return 'netstat -a -b | findstr :{}'.format(port)

    @staticmethod
    def set_pyro_log_path(path):
        return "SET PYRO_LOGFILE='{}pyro.log' & SET PYRO_LOGLEVEL=DEBUG".format(path)

    @staticmethod
    def get_pyro_log_path():
        return "echo %PYRO_LOGFILE%"


class LinuxHandler(object):

    def __init__(self, connection, conn_alias):
        self.connection = connection
        self.conn_alias = conn_alias

    def is_port_in_open_ports(self, port):
        result = self.connection.execute(
            command='sudo iptables -L |grep {}'.format(port),
            timeout=30,
            connection=self.conn_alias
        )
        logger.debug('iptables containing port {} on unix machine: {}'.format(port, result))
        if len(result) > 0 and 'ACCEPT' in result:
            return True
        return False

    def is_firewall_active(self):
        status = self.connection.execute(
            command="sudo systemctl status firewalld| grep 'Active: '",
            timeout=50,
            connection=self.conn_alias
        )
        if 'active (running)' in status:
            logger.info('firewalld service active and running')
            return True
        logger.info('firewalld service inactive')
        return False

    def open_firewall_port(self, port):
        self.connection.execute(
            command='sudo iptables -A INPUT -p tcp --dport {} -j ACCEPT'.format(port),
            timeout=30,
            connection=self.conn_alias
        )
        logger.debug('open port command executed on unix machine')
        return self.is_port_in_open_ports(port)

    def close_firewall_port(self, port):
        self.connection.execute(
            command='sudo iptables -D INPUT -p tcp --dport {} -j ACCEPT'.format(port),
            timeout=30,
            connection=self.conn_alias
        )
        logger.debug('close port command executed on unix machine')
        return not self.is_port_in_open_ports(port)

    def turn_firewall_off(self):
        self.connection.execute(
            command='sudo service firewalld stop',
            timeout=30,
            connection=self.conn_alias
        )
        if self.is_firewall_active():
            return False
        return True

    def turn_firewall_on(self):
        self.connection.execute(
            command='sudo service firewalld start',
            timeout=30,
            connection=self.conn_alias
        )
        # run command : sudo systemctl start firewalld
        # run command : sudo systemctl enable firewalld
        return self.is_firewall_active()

    def save_processes(self, remote_dir):
        self.connection.execute(
            command='ps aux > {}processes.txt'.format(remote_dir),
            timeout=45,
            connection=self.conn_alias
        )
        if self.connection.file_exists(remote_dir + 'processes.txt', connection=self.conn_alias):
            return remote_dir + 'processes.txt'

    def save_firewall_rules(self, remote_dir):
        self.connection.execute(
            command='sudo iptables-save > {}firewall_rules.txt'.format(remote_dir),
            timeout=40,
            connection=self.conn_alias
        )
        if self.connection.file_exists(remote_dir + 'firewall_rules.txt', connection=self.conn_alias):
            return remote_dir + 'firewall_rules.txt'

    @staticmethod
    def kill_process(process):
        return 'kill -9 $(ps aux |grep -i {process}| grep -v grep | awk \'{{print $2}}\' | xargs)'.format(
            process=process)

    def is_service_active(self):
        raise NotImplementedError

    def activate_service(self, service):
        raise NotImplementedError

    def deactivate_service(self, service):
        raise NotImplementedError

    @staticmethod
    def is_port_listening(port):
        return 'sudo netstat -tulpn | grep -i :{}'.format(port)

    @staticmethod
    def set_pyro_log_path(path):
        return "export PYRO_LOGFILE='{}/pyro.log' ; export PYRO_LOGLEVEL=DEBUG".format(path)

    @staticmethod
    def get_pyro_log_path():
        return "echo $PYRO_LOGFILE"