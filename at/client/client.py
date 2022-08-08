from .remote_connection import RemoteConnection

RemoteConnection.set_pyro_log_path_for_client()

from Pyro4 import Proxy
import time
from .exceptions import *
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Client(object):
    PYRO_SERVER_NAME = 'PYRO:ATServer@{}:9093'
    AT_VERSION = '0.5'

    def __init__(self, config):
        self.config = config
        self._hostname = config['ue_pc_ip']
        self.processes_to_kill = []
        if 'processes_to_kill' in config:
            for process in config['processes_to_kill']:
                self.processes_to_kill.append(process)
        self.connection = RemoteConnection(
            hostname=config['ue_pc_ip'],
            username=config['login'],
            password=config['password'],
            processes_to_kill=self.processes_to_kill)
        self._com_id = config['com_id']
        self._remote_files_dir = '/home/' + str(config['login']) + '/pyro_test/'
        self._remote_prepared = False

    def set_remote_paths(self, paths):
        self._remote_paths = []
        for path in paths:
            full_path = str(self._remote_files_dir) + str(path.split('/')[-1])
            logger.info('adding {} to remote paths'.format(full_path))
            self._remote_paths.append(full_path)
        logger.info('files paths on remote are {}'.format(self._remote_paths))
        return self._remote_paths

    def prepare(self):
        self._connected = self.connection.connect()
        if self._connected is True:
            os_handler = self.connection.get_os_handler()
            logger.info('os version on ue pc :{}'.format(os_handler))
            self._firewall_on = self.connection.turn_off_firewall()
            self._port_on = self.connection.open_port_connection()
            self.connection.save_firewall_rules()
            state = self.connection.kill_processes()
            if state is not True:
                logger.info('trying to kill remaining processes')
                self.connection.kill_processes()
            self.connection.save_processes()
            paths = self.connection.get_server_files_paths()
            self.connection.send_files_to_server(localpaths=paths)
            self.set_remote_paths(paths)
            self.connection.start_remote_server(self._com_id)
            time.sleep(3)
            if self.connection.is_port_listening(9093):
                self._remote_prepared = True
                logger.info('remote prepared')
        return self._remote_prepared

    def terminate(self):
        if self._remote_prepared:
            self.ue_ready = self.p.release_ue()
            if not isinstance(self.ue_ready, bool):
                raise RemoteException(' exception while releasing ue : {}'.format(
                    self.ue_ready
                ))
            self.p.shutdown()
            if not self._connected:
                self._connected = self.connection.connect()
        self.connection.remove_remote_files(self._remote_paths)
        self.connection.close_port_connection()
        if not self._firewall_on:
            self.connection.turn_on_firewall()
        self._connected = self.connection.disconnect()
        self._remote_prepared = False
        return self._connected

    def read_pin_status(self):
        sim_sate = self.p.read_pin_status()
        if isinstance(sim_sate, tuple):
            return sim_sate
        raise RemoteException('sim status not properly retrieved, due to {}'.format(sim_sate))

    def report_phone_activity_status(self):
        phone_status = self.p.report_phone_activity_status()
        if isinstance(phone_status, tuple):
            return phone_status
        raise RemoteException('Phone activity status not properly retrived, due to {}'.format(phone_status))

    def get_signal_quality(self):
        signal_quality = self.p.get_signal_quality()
        if isinstance(signal_quality, list):
            return signal_quality
        raise RemoteException('Signal Quality not properly retrieved, due to {}'.format(signal_quality))

    def set_rat_mode(self, rat='auto', mcc=0, mnc=0):
        if rat.upper() not in {'AUTO', 'LTE', 'NR_LTE', 'NR'}:
            return ValueError(' rat value should be one of AUTO, LTE, NR_LTE or NR')
        rat_mode = self.p.set_rat_mode(rat.lower(), mcc, mnc)
        if isinstance(rat_mode, tuple):
            return rat_mode
        raise RemoteException('something gone wrong while setting the rat mode, due to {}'.format(rat_mode))

    def get_network_registration_params(self):
        registration_params = self.p.get_network_registration_params()
        if isinstance(registration_params, tuple):
            return registration_params
        raise RemoteException(
            'Something gone wrong while geeting the registration params, due to {}'.format(registration_params))

    def get_pdp_address(self):
        return self.p.get_pdp_address()

    def get_ue(self):
        if self._remote_prepared:
            self.connect()
            self.ue_ready = self.p.get_ue(self._com_id)
            if self.ue_ready is True:
                logger.info('ue ready value:{}'.format(self.ue_ready))
                return self.ue_ready
            raise RemoteException(
                'exception while preparing ue: {}'.format(self.ue_ready)
            )

    def attach(self):
        attach_state = self.p.attach()
        if 'Attached' in attach_state:
            return True
        raise RemoteAttachException('attach gone wrong, due to :  {}'.format(attach_state))


    def detach(self):
        self._attached = self.p.detach()
        if not self._attached:
            logger.info('ue detach successful')
            return self._attached
        raise RemoteDetachException('detach exception: {}'.format(self._attached))


    def connect(self):
        self.connection.set_pyro_log_path_on_server()
        with Proxy(self.PYRO_SERVER_NAME.format(self._hostname)) as self.p:
            logger.info('connecting to server')
            time.sleep(10)
            ver = self.p.at_version()
            logger.info('version on server is {}'.format(ver))
            if ver == self.AT_VERSION:
                self.connected = True
                logger.info('connection established')
        return self.connected