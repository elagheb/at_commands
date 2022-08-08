from ...commands.at import AtCommand
from .exceptions import MobileTerminalMethodException


class CPAS(AtCommand):
    COMMAND = 'AT+CPAS'

    def __init__(self, serial_target, timeout):
        super(CPAS, self).__init__(serial_target, timeout)
        self.expected_values = {
            0: "Ready : UE allows commands from AT",
            1: "Unavailable: UE does Not allow commands from AT",
            2: "Unknown : UE response to instructions is not guaranteed",
            3: "Ringing: UE ready for commands",
            4: "Call in progress: UE ready for commands, but a call is in progress",
            5: "asleep (UE is unable to process commands from TA/TE because it is in a low functionality state)"
        }
        self.timeout = timeout

    def get(self):
        return self.read(read_char='')

    def parse_output(self, result):
        if result in self.expected_values.keys():
            return result, self.expected_values[result]
        return result


class CLAC(AtCommand):
    COMMAND = 'AT+CLAC'

    def __init__(self, serial_target, timeout):
        super(CLAC, self).__init__(serial_target)
        self.timeout = timeout

    def get(self):
        result = self.serial_target.run(commad=self.COMMAND,
                                        timeout=self.timeout,
                                        exception=MobileTerminalMethodException,
                                        message="Error occurred while getting supported commands"
                                        )
        return result


class CFUN(AtCommand):
    COMMAND = 'AT+CFUN'
    ACTIVATE = 1
    DEACTIVATE = 0

    def __init__(self, serial_target, timeout):
        super(CFUN, self).__init__(serial_target, timeout)
        self.level = 0
        self.expected_values = {
            0: 'CFUN deactivated : mobile minimum functionality',
            1: 'CFUN activated: mobile full functionality ',
            2: "MT transmit RF circuits only disabled",
            3: "MT receive RF circuits only disabled",
            4: "both MT transmit and receive RF circuits are disabled"
        }

    def set(self, level):
        if level < 0 or level > 129:
            raise ValueError('level out of range')
        self.serial_target.run(
            command=self.COMMAND + "={}".format(level),
            timeout=self.timeout,
            exception=MobileTerminalMethodException,
            message="Error occurred while setting phone functionality level to {}".format(level)
        )
        return self.read()

    def parse_output(self, result):
        for value in result:
            if '+CFUN:' in value:
                self.level = value.split(': ')[-1]
        if self.level in self.expected_values.keys():
            return self.level, self.expected_values[self.level]
        return self.level, 'Not in expected values'


class CPIN(AtCommand):
    COMMAND = 'AT+CPIN'

    def __init__(self, serial_target, timeout):
        super(CPIN, self).__init__(serial_target, timeout)
        self.sim_state = "READY"
        self.expected_values = {
            "READY": "ME is not pending for any password",
            "SIM PIN": "ME is waiting SIM PIN to be given",
            "SIM PUK": "ME is waiting SIM PUK to be given",
            "PH-SIM PIN": "ME is waiting phone-to-SIM card password to be given",
            "PH-FSIM PIN": "ME is waiting phone-to-very first SIM card password to be given",
            "PH-FSIM PUK": "ME is waiting phone-to-very first SIM card unblocking password to be given",
            "SIM PIN2": "ME is waiting SIM PIN2 to be given",
            "SIM PUK2": "SIM PUK2 - ME is waiting SIM PUK2 to be given",
            "PH-NET PIN": "MT is waiting network personalization password to be given",
            "PH-NET PUK": "MT is waiting network personalization unblocking password to be given",
            "PH-NETSUB PIN": "MT is waiting network subset personalization password to be given",
            "PH-NETSUB PUK": "MT is waiting network subset personalization unblocking password to be given",
            "PH-SP PIN": "MT is waiting service provider personalization password to be given",
            "PH-SP PUK": "MT is waiting service provider personalization unblocking password to be given",
            "PH-CORP PIN": "MT is waiting corporate personalization password to be given",
            "PH-CORP PUK": " MT is waiting corporate personalization unblocking password to be given"
        }

    def enter(self, pin):
        if not isinstance(pin, str):
            raise ValueError('Value should be a string, passed value is {}'.format(type(pin)))
        self.serial_target.run(command=self.COMMAND + "={}".format(pin),
                               timeout=self.timeout,
                               exception=MobileTerminalMethodException,
                               message="Error occurred while entering PIN,")
        return self.read()

    def parse_output(self, result):
        for value in result:
            if '+CPIN:' in value:
                self.sim_state = value.split(': ')[-1]
        if self.sim_state in self.expected_values.keys():
            return self.sim_state, self.expected_values[self.sim_state]
        raise KeyError('state not in expected values , found state is {}'.format(self.sim_state))


class CSQ(AtCommand):
    COMMAND = "AT+CSQ"

    def __init__(self, serial_target, timeout):
        super(CSQ, self).__init__(serial_target, timeout)
        self.bit_error_rates = {
            0: 'less than 0.2%',
            1: '0.2% to 0.4%',
            2: '0.4% to 0.8%',
            3: ' 0.8% to 1.6%',
            4: '1.6% to 3.2%',
            5: '3.2% to 6.4%',
            6: '6.4% to 12.8%',
            7: 'more than 12.8%'
        }

    @staticmethod
    def get_signal_condition(rssi):
        if rssi < 10:
            return 'MARGINAL'
        if rssi >= 10 and rssi <= 14:
            return 'OK'
        if rssi > 14 and rssi <= 19:
            return 'GOOD'
        if rssi >= 20 and rssi >= 31:
            return 'Excellent'
        if rssi == 99:
            return 'Unknown or undetectable'

    def parse_rssi_and_ber(self, values):
        signal_quality = []
        for value in values:
            if '+CSQ:' in value:
                indicators = value.split(': ')
                rssi, ber = indicators[-1].split(',')
                rssi, ber = int(rssi), int(ber)
                if rssi != 99:
                    signal_quality.append(
                        {'RSSI value': rssi, 'RSSI in dBm': '({}) dBm'.format(-113 + rssi * 2),
                         'condition': self.get_signal_condition(rssi)})
                elif rssi == 99:
                    signal_quality.append(
                        {'RSSI value': rssi, 'RSSI in dBm': ' not known or not detectable',
                         'condition': self.get_signal_condition(rssi)}
                    )
                if ber == 99:
                    signal_quality.append({
                        'BER value': ber, 'BER in percent': ' not known or not detectable'
                    })
                elif ber != 99:
                    if ber in self.bit_error_rates.keys():
                        signal_quality.append({
                            'BER Value': ber, 'BER in percent': '{}'.format(
                                self.bit_error_rates[ber],
                            )})
                    else:
                        signal_quality.append({'BER Value': ber, 'BER in percent': 'unknown'})
        return signal_quality

    def get(self):
        result = self.serial_target.run(command=self.COMMAND,
                                        timeout=self.timeout,
                                        exception=MobileTerminalMethodException,
                                        message="Error occurred while reading signal quality,")
        return self.parse_rssi_and_ber(result)


class GSN(AtCommand):
    COMMAND = 'AT+GSN'

    def __init__(self, serial_target, timeout):
        super(GSN, self).__init__(serial_target, timeout)

    def get(self):
        return self.read(read_char='')

    def parse_output(self, result):
        return int(result[1].strip())


class CIMI(AtCommand):
    COMMAND = 'AT+CIMI'

    def __init__(self, serial_target, timeout):
        super(CIMI, self).__init__(serial_target, timeout)

    def get(self):
        return self.read(read_char='')

    def parse_output(self, result):
        return result[1].split()


class CGMM(AtCommand):
    COMMAND = 'AT+CGMM'

    def __init__(self, serial_target, timeout):
        super(CGMM, self).__init__(serial_target, timeout)

    def get(self):
        result = self.serial_target.run(
            command=self.COMMAND,
            timeout=self.timeout,
            exception=MobileTerminalMethodException,
            message="Error while getting model identification,"
        )
        return result[1].strip()


class WS46(AtCommand):
    COMMAND = 'AT+WS46'

    def __init__(self, serial_target, timeout=20):
        super(WS46, self).__init__(serial_target, timeout)
        self.expected_values = expected_values = {
            12: "GSM Digital Cellular Systems (GERAN only)",
            22: "UTRAN only",
            25: "3GPP Systems (GERAN, UTRAN and E-UTRAN)",
            28: "E-UTRAN only",
            29: "GERAN and UTRAN",
            30: "GERAN and E-UTRAN",
            31: "UTRAN and E-UTRAN",
            35: "GERAN, UTRAN, E-UTRAN and NG-RAN",
            36: "NG-RAN only",
            37: "NG-RAN and E-UTRAN ",
            38: "NG-RAN, E-UTRAN and UTRAN",
            39: "NG-RAN, E-UTRAN and GERAN",
            40: "NG-RAN and UTRAN",
            41: "NG-RAN, UTRAN and GERAN",
            42: "NG-RAN and GERAN"
        }

    def parse_output(self, result):
        return int(result[1]), self.expected_values[int(result[1])]


class ATI(AtCommand):
    COMMAND = 'ATI'

    def __init__(self, serial_target, timeout=20):
        super(ATI, self).__init__(serial_target, timeout)

    def get(self):
        return self.read(read_char='')

    def parse_output(self, result):
        return result[1:]