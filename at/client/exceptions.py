class PyroConnectionException(Exception):
    pass


class ProcessTerminationException(Exception):
    pass


class FileTransmissionException(Exception):
    pass


class RemoteFileCleaningException(Exception):
    pass


class FirewallServiceNotInstalledException(Exception):
    pass


class RemoteAttachException(Exception):
    pass


class RemoteDetachException(Exception):
    pass


class RemoteException(Exception):
    pass


class InvalidConfiguration(Exception):
    pass


class FirewallRuleException(Exception):
    pass


class ServiceOperationException(Exception):
    pass