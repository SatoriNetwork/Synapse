'''
we discovered that udp hole punching inside docker containers is not always
possible because of the way the docker nat works. we thought it was.
this host script is meant to run on the host machine.
it will establish a sse connection with the flask server running inside
the container. it will handle the UDP hole punching, passing data between the
flask server and the remote peers.

Why threaded? because...
this linux version drops the need for asyncio and uses 2 threads instead.
this is because we encountered an error:
"'_UnixSelectorEventLoop' object has no attribute 'sock_recvfrom'"
and it seemed this might be due to a python version issue:
https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.sock_recvfrom
given that we are unwilling to require a more recent version of python than 3.7
we are going to use threads instead of asyncio. we will use this simplified 
version on mac as well. luckily we only need 2 threads: one that listens to the
neuron and relays messages to peers, and one that listens to the socket and
relays messages from peers to the neuron.
'''

import typing as t
import time
import threading
import socket
import urllib.request
import urllib.parse
from satorisynapse.lib.error import SseTimeoutFailure
from satorisynapse.lib.domain import Envelope, Ping, SYNAPSE_PORT
from satorisynapse.lib.requests import requests
from satorisynapse.lib.utils import greyPrint, satoriUrl


class Synapse():
    ''' go-between for the flask server and the remote peers '''

    def __init__(self, port: int = None):
        self.port = port or SYNAPSE_PORT
        self.running = False
        self.neuronListener = None
        self.peers: t.List[str] = []
        self.socket: socket.socket = self.createSocket()
        self.run()

    ### INIT ###

    def run(self):
        ''' runs forever '''
        self.running = True
        self.initNeuronListener()

    def initNeuronListener(self):
        self.neuronListener = threading.Thread(target=self.listenToNeuron)
        self.neuronListener.start()

    def initSocketListener(self):
        self.listenToSocket()

    def listenToNeuron(self):
        try:
            request = urllib.request.Request(satoriUrl('/stream'))
            with urllib.request.urlopen(request) as response:
                for line in response:
                    if not self.running:
                        break
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data:'):
                        self.handleNeuronMessage(decoded[5:].strip())
        except KeyboardInterrupt:
            pass
        except SseTimeoutFailure:
            pass
        except Exception as e:
            greyPrint(f'neuron listener error: {e}')
        finally:
            self.shutdown()

    def createSocket(self) -> socket.socket:
        def waitBeforeRaise(seconds: int):
            '''
            if this errors, but the neuron is reachable, it will immediately 
            try again, and mostlikely fail for the same reason, such as perhaps
            the port is bound elsewhere. So in order to avoid continual 
            attempts and printouts we'll wait here before raising
            '''
            time.sleep(seconds)

        def bind(localPort: int) -> t.Union[socket.socket, None]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.bind(('0.0.0.0', localPort))
                return sock
            except Exception as e:
                greyPrint(f'unable to bind to port {localPort}, {e}')
                waitBeforeRaise(60)
                raise Exception('unable to create socket')

        return bind(self.port)

    def listenToSocket(self):
        while self.running:
            try:
                data, address = self.socket.recvfrom(1024)
                if data != b'':
                    # greyPrint(f'RECEIVED: {data}, {address}')
                    self.handlePeerMessage(data, address)
            except Exception as _:
                break
        self.shutdown()

    ### SPEAK ###

    def speak(self, remoteIp: str, remotePort: int, data: str = ''):
        # greyPrint(f'SENDING: {data} {remoteIp}:{remotePort} ')
        self.socket.sendto(data.encode(), (remoteIp, remotePort))

    def maybeAddPeer(self, ip: str):
        if ip not in self.peers:
            self.addPeer(ip)

    def addPeer(self, ip: str):
        self.speak(ip, self.port, data=Ping().toJson)
        self.peers.append(ip)

    ### HANDLERS ###

    def handleNeuronMessage(self, message: str):
        msg = Envelope.fromJson(message)
        self.maybeAddPeer(msg.ip)
        self.speak(
            remoteIp=msg.ip,
            remotePort=self.port,
            data=msg.vesicle.toJson)

    def handlePeerMessage(self, data: bytes, address: t.Tuple[str, int]):
        # greyPrint(f'Received {data} from {address[0]}:{address[1]}')
        # # no need to ping back - it has issues anyway
        # ping = None
        # try:
        #    ping = Ping.fromMessage(data)
        # except Exception as e:
        #    greyPrint(f'error parsing message: {e}')
        # if isinstance(ping, Ping):
        #    if not ping.isResponse:
        #        self.maybeAddPeer(address[0])
        #        self.speak(
        #            remoteIp=address[0],
        #            remotePort=self.port,
        #            data=Ping(True).toJson)
        #        return
        #    if ping.isResponse:
        #        greyPrint(f'connection to {address[0]} established!')
        #        return
        self.relayToNeuron(data=data, ip=address[0], port=address[1])

    def relayToNeuron(self, data: bytes, ip: str, port: int):
        try:
            response = requests.post(
                satoriUrl('/message'),
                data=data,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'remoteIp': ip})
            if response != 'ok':
                raise Exception(response)
        except Exception as e:
            greyPrint(
                'unable to relay message to neuron: error: '
                f'{e}, address: {ip}:{port}, data: {data}')

    ### SHUTDOWN ###

    def shutdown(self):
        self.running = False
        if self.socket:
            greyPrint('closing socket')
            self.socket.close()
            self.socket = None
        if (
            self.neuronListener != None and
            threading.current_thread() != self.neuronListener
        ):
            greyPrint('closing neuron listener')
            self.neuronListener.join()
            self.neuronListener = None


def silentlyWaitForNeuron():
    while True:
        try:
            r = requests.get(satoriUrl('/ping'))
            if r == 'ready':
                return
            if r == 'ok':
                return
        except Exception as _:
            pass
        time.sleep(1)


def waitForNeuron():
    notified: bool = False
    while True:
        try:
            r = requests.get(satoriUrl('/ping'))
            if r == 'ready':
                if notified:
                    greyPrint(
                        'established connection to Satori Neuron')
                return
            if r == 'ok' and not notified:
                greyPrint('waiting for Satori Neuron...')
        except Exception as _:
            pass
        if not notified:
            greyPrint('waiting for Satori Neuron...')
            notified = True
        time.sleep(1)


def main(port: int = None):
    while True:
        waitForNeuron()
        try:
            greyPrint("Satori Synapse is running. Press Ctrl+C to stop.")
            synapse = Synapse(port)
            synapse.listenToSocket()
        except KeyboardInterrupt:
            pass
        except SseTimeoutFailure:
            pass
        except Exception as _:
            pass
        finally:
            greyPrint('Satori Synapse is shutting down')
            synapse.shutdown()
            time.sleep(5)


def runSynapse(port: int = None):
    try:
        greyPrint('Synapse started (threaded version)')
        main(port)
    except KeyboardInterrupt:
        greyPrint('Synapse exited by user')


if __name__ == '__main__':
    runSynapse()
