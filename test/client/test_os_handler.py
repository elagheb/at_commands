from .. import mock, unittest, patch
from at.client.os_handler import WindowsHandler, LinuxHandler
from at.client.ssh import ssh


class TestWindowsHandler(unittest.TestCase):

    def setUp(self):
        self.wds = WindowsHandler(
            ssh(),
            'PYRO'
        )

    def test_is_firewall_active(self):
        ssh.execute = mock.MagicMock(
            return_vaue="""
            Domain Profile Settings:
            ----------------------------------------------------------------------
            State                                 ON

            Private Profile Settings:
            ----------------------------------------------------------------------
            State                                 ON

            Public Profile Settings:
            ----------------------------------------------------------------------
            State                                 OFF

            Ok.

            """)
        self.assertFalse(self.wds.is_firewall_active())

    def test_is_port_in_open_ports(self):
        ssh.execute = mock.MagicMock(
            return_value="""
            9093   TCP       Enable  Inbound               AT Pyro Application connection
            9093   TCP       Enable  Inbound               AT Pyro Application connection""")
        self.assertTrue(self.wds.is_port_in_open_ports(9093))

    def test_open_firewall_port(self):
        ssh.execute = mock.MagicMock(
            return_value="""
            9093   TCP       Enable  Inbound               AT Pyro Application connection
            9093   TCP       Enable  Inbound               AT Pyro Application connection""")
        self.assertTrue(self.wds.open_firewall_port(9093))

    def test_close_firewall_port(self):
        ssh.execute = mock.MagicMock(return_value="""
        Deleted 2 rule(s).
        Ok.""")
        self.assertTrue(self.wds.close_firewall_port(9093))

    def test_turn_firewall_off(self):
        ssh.execute = mock.MagicMock(
            return_value="""
            Domain Profile Settings:
            ----------------------------------------------------------------------
            State                                 OFF

            Private Profile Settings:
            ----------------------------------------------------------------------
            State                                 OFF

            Public Profile Settings:
            ----------------------------------------------------------------------
            State                                 OFF
            Ok."""
        )
        self.assertTrue(self.wds.turn_firewall_off())

    def test_turn_firewall_on(self):
        ssh.execute = mock.MagicMock(
            return_value="""
        Domain Profile Settings:
            ----------------------------------------------------------------------
            State                                 ON

            Private Profile Settings:
            ----------------------------------------------------------------------
            State                                 ON

            Public Profile Settings:
            ----------------------------------------------------------------------
            State                                 ON
            Ok.
        """)
        self.assertTrue(self.wds.turn_firewall_on())

    def test_save_processes(self):
        with patch.object(ssh, 'execute'):
            ssh.file_exists = mock.MagicMock(return_value=True)
            self.assertIsInstance(
                self.wds.save_processes(remote_dir=r'c:\Users\localuser\\'),
                str)

    def test_save_firewall_rules(self):
        with patch.object(ssh, "execute"):
            ssh.file_exists = mock.MagicMock(return_value=True)
            self.assertIsInstance(
                self.wds.save_firewall_rules(remote_dir=r'c:\Users\localuser\\'),
                str
            )

    def test_is_service_active(self):
        ssh.execute = mock.MagicMock(
            return_value="""
            TelnetClient                                          | Enabled
            """
        )
        self.assertTrue(self.wds.is_service_active(service='TelnetClient'))


class TestLinuxHandler(unittest.TestCase):
    firewall_port = """
            ACCEPT     tcp  --  anywhere             anywhere             tcp dpt:9093
            ACCEPT     tcp  --  anywhere             anywhere             tcp dpt:9093 ctstate NEW
            """
    firewall_active = """
          Active: active (running) since Mon 2020-04-13 16:36:25 CEST; 1 weeks 3 days ago"""

    def setUp(self):
        self.lnx = LinuxHandler(
            ssh(),
            'PYRO'
        )

    def test_is_port_in_open_ports(self):
        ssh.execute = mock.MagicMock(
            return_value=self.firewall_port)
        self.assertTrue(self.lnx.is_port_in_open_ports(9093))

    def test_is_firewall_active(self):
        ssh.execute = mock.MagicMock(return_value=self.firewall_active)
        self.assertTrue(self.lnx.is_firewall_active())

    def test_open_firewall_port(self):
        ssh.execute = mock.MagicMock(
            return_value=self.firewall_port)
        self.assertTrue(self.lnx.open_firewall_port(9093))

    def test_close_firewall_port(self):
        with patch.object(ssh, 'execute'):
            self.assertTrue(self.lnx.close_firewall_port(9093))

    def test_turn_firewall_off(self):
        with patch.object(ssh, 'execute'):
            self.assertTrue(
                self.lnx.turn_firewall_off()
            )

    def test_turn_firewall_on(self):
        ssh.execute = mock.MagicMock(
            return_value=self.firewall_active
        )
        self.assertTrue(
            self.lnx.turn_firewall_on()
        )

    def test_save_processes(self):
        with patch.object(ssh, 'execute'):
            ssh.file_exists = mock.MagicMock(return_value=True)
            self.assertIsInstance(
                self.lnx.save_processes(remote_dir='/home/localuser/'),
                str
            )

    def test_save_firewall_rules(self):
        with patch.object(ssh, 'execute'):
            ssh.file_exists = mock.MagicMock(return_value=True)
            self.assertIsInstance(
                self.lnx.save_processes(remote_dir='/home/localuser/'),
                str
            )

    def test_is_service_active(self):
        with self.assertRaises(NotImplementedError):
            self.lnx.is_service_active()

    def test_activate_service(self):
        with self.assertRaises(NotImplementedError):
            self.lnx.activate_service('TelentClient')

    def test_deactivate_service(self):
        with self.assertRaises(NotImplementedError):
            self.lnx.deactivate_service('TelentClient')

    def test_is_port_listening(self):
        self.assertIsInstance(
            self.lnx.is_port_listening(80),
            str
        )

    def test_set_pyro_log_path(self):
        self.assertIsInstance(
            self.lnx.set_pyro_log_path('/home/localuser/'),
            str
        )

    def test_get_pyro_logpath(self):
        assert self.lnx.get_pyro_log_path() == "echo $PYRO_LOGFILE"
