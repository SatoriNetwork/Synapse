import typing as t
import json

SYNAPSE_PORT = 24600


class Vesicle():
    '''
    any object sent over the wire to a peer must inhereit from this so it's
    guaranteed to be convertable to dict so we can have nested dictionaries
    then convert them all to json once at the end (rather than nested json).

    in the future we could use this as a place to hold various kinds of context
    to support advanced protocol features.
    '''

    def __init__(self, className: str = None, **kwargs):
        self.className = className or self.__class__.__name__
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def toDict(self):
        return {
            'className': self.className,
            **{
                key: value
                for key, value in self.__dict__.items()
                if key != 'className'}}

    @property
    def toJson(self):
        return json.dumps(self.toDict)


class Ping(Vesicle):
    ''' initial ping is False, response ping is True '''

    def __init__(self, ping: bool = False, **_kwargs):
        super().__init__()
        self.ping = ping

    @staticmethod
    def empty() -> 'Ping':
        return Ping()

    @staticmethod
    def fromMessage(msg: bytes) -> 'Ping':
        obj = Ping(**json.loads(msg.decode()
                                if isinstance(msg, bytes) else msg))
        if obj.className == Ping.empty().className:
            return obj
        raise Exception('invalid object')

    @property
    def toDict(self):
        return {'ping': self.ping, **super().toDict}

    @property
    def toJson(self):
        return json.dumps(self.toDict)

    @property
    def isValid(self):
        return isinstance(self.ping, bool)

    @property
    def isResponse(self):
        return self.ping


class Envelope():
    ''' messages sent between neuron and synapse '''

    def __init__(self, ip: str, vesicle: Vesicle):
        self.ip = ip
        self.vesicle = vesicle

    @staticmethod
    def fromJson(msg: bytes) -> 'Envelope':
        structure: t.Dict = json.loads(
            msg.decode() if isinstance(msg, bytes) else msg)
        return Envelope(
            ip=structure.get('ip', ''),
            vesicle=Vesicle(**structure.get('vesicle', {'content': '', 'context': {}})))

    @property
    def toDict(self):
        return {
            'ip': self.ip,
            'vesicle': (
                self.vesicle.toDict
                if isinstance(self.vesicle, Vesicle)
                else self.vesicle)}

    @property
    def toJson(self):
        return json.dumps(self.toDict)
