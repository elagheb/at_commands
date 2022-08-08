"""
:author: Elagheb Carr
:contact: celagheb@gmail.com
"""
from ...commands.at import AtCommand
from .exceptions import NetworkMethodException


class CREG(AtCommand):
    COMMAND = 'AT+CREG'

    def __init__(self, serial_target, timeout=120):
        super(CREG, self).__init__(serial_target, timeout)
        self.expected_values = [
            {
                0: "network registration unsolicited result code disabled",
                1: "network registration unsolicited result code format +CREG: <stat>",
                2: "network registration unsolicited result code format +CREG: <stat>[,[<lac>],[<ci>],[<AcT>]]",
                3: "network registration unsolicited result code format" +
                   " +CREG: <stat>[,[<lac>],[<ci>],[<AcT>][,<cause_type>,<reject_cause>]]"
            },
            {
                0: "not registered, MT is not currently searching a new operator to register to",
                1: "registered, home network",
                2: "not registered, but MT is currently searching a new operator to register to",
                3: "registration denied",
                4: "unknown (e.g. out of GERAN/UTRAN/E-UTRAN coverage)",
                5: "registered, roaming",
                6: "registered for 'SMS only', home network (applicable only when <AcT> indicates E-UTRAN)",
                7: "registered for 'SMS only', roaming (applicable only when <AcT> indicates E-UTRAN)",
                8: "attached for emergency bearer services only",
                9: "registered for 'CSFB not preferred', home network",
                10: "registered for 'CSFB not preferred', roaming",
            },
            {
                0: "GSM",
                1: "GSM Compact",
                2: "UTRAN",
                3: "GSM w/EGPRS",
                4: "UTRAN w/HSDPA",
                5: "UTRAN w/HSUPA",
                6: "UTRAN w/HSDPA and HSUPA",
                7: "E-UTRAN",
                8: "EC-GSM-IoT (A/Gb mode)",
                9: "E-UTRAN (NB-S1 mode)",
                10: "E-UTRA connected to a 5GCN",
                11: "NR connected to a 5GCN",
                12: "NG-RAN",
                13: "E-UTRA-NR dual connectivity"
            }
        ]

    def parse_output(self, result):
        for value in result:
            if "+CREG: " in value:
                indicators = value.split(': ')
                n, stat = indicators[-1].split(',')
                n, stat = int(n), int(stat)
                if n in self.expected_values[0].keys() and stat in self.expected_values[1].keys():
                    return n, self.expected_values[0][n], stat, self.expected_values[1][stat]
        raise NetworkMethodException('network registration params not found, AT+CREG? result  : {}'.format(result))

    def set(self, level=2):
        state = self.serial_target.run(command=self.COMMAND + '={}'.format(level),
                                       timeout=self.timeout,
                                       exception=NetworkMethodException,
                                       message='Error occurred while getting network registration infos, ')
        output = self.parse_output(state)
        if output[0] == level:
            return output


class COPS(AtCommand):
    COMMAND = 'AT+COPS'
    AUTO = 0
    LTE = 7
    NR_LTE = 13
    NR = 11

    def __init__(self, serial_target, timeout=180):
        super(COPS, self).__init__(serial_target, timeout)
        self.expected_values = [
            {
                0: "automatic",
                1: "manual",
                2: "deregister from network",
                3: "set only",
                4: "manual/automatic",
            },
            {
                0: "long format alphanumeric",
                1: "short format alphanumeric",
                2: "numeric",
            },
            {
                0: "GSM",
                2: "UTRAN",
                3: "GSM w/EGPRS",
                4: "UTRAN w/HSDPA",
                5: "UTRAN w/HSUPA",
                6: "UTRAN w/HSUPA and HSUPA",
                7: "E-UTRAN",
                8: "EC-GSM-IoT",
                9: "E-UTRAN",
                10: "E-UTRA connected to a 5GCN",
                11: "NR connected to a 5GCN",
                12: "NG-RAN",
                13: "E-UTRA-NR dual connectivity",

            }
        ]

    def set(self, rat=0, mcc=0, mnc=0):
        if rat not in self.expected_values[2].keys():
            raise ValueError('rat value not supported')
        self.serial_target.run(command=self.COMMAND + '=4,2,"{}{}",{}'.format(mcc, mnc, rat),
                               timeout=self.timeout,
                               exception=NetworkMethodException,
                               message='Error occurred while setting rat :{},mcc :{}, mnc:{} '.format(
                                   rat, mcc, mnc
                               ))
        return self.read()

    def parse_output(self, result):
        for value in result:
            if '+COPS:' in value:
                return value[-1], self.expected_values[2][value[-1]]


class CGATT(AtCommand):
    COMMAND = "AT+CGATT"
    ATTACH = 1
    DETACH = 0

    def __init__(self, serial_target, timeout=180):
        super(CGATT, self).__init__(serial_target, timeout)
        self.expected_values = {
            0: "Detached",
            1: "Attached",
        }

    def set(self, value=1):
        if value not in self.expected_values.keys():
            raise ValueError('Value out of scope of CGATT command : passed value : {}'.format(
                value
            ))
        self.serial_target.run(command=self.COMMAND + '={}'.format(value),
                               timeout=self.timeout,
                               exception=NetworkMethodException,
                               message='Error occurred while setting attach status to {}, '.format(value))
        return self.read()

    def parse_output(self, result):
        for value in result:
            if '+CGATT:' in value:
                self.level = value[-1]
        if self.level in self.expected_values.keys():
            return self.level, self.expected_values[self.level]
        raise NetworkMethodException('Value out of scope of CGATT : {}'.format(self.level))