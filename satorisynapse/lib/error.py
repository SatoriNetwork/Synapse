
class SseTimeoutFailure(Exception):
    '''
    sometimes we the connection to the neuron fails and we want to identify
    that failure easily with this custom exception so we can handle reconnect.
    '''

    def __init__(self, message='Sse timeout failure', extraData=None):
        super().__init__(message)
        self.extraData = extraData

    def __str__(self):
        return f"{self.__class__.__name__}: {self.args[0]} (Extra Data: {self.extraData})"
