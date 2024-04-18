'''
we discovered that udp hole punching inside docker containers is not always
possible because of the way the docker nat works. we thought it was.
this host script is meant to run on the host machine.
it will establish a sse connection with the flask server running inside
the container. it will handle the UDP hole punching, passing data between the
flask server and the remote peers.
'''

import time
import typing as t
import socket
import asyncio
import requests  # ==2.31.0
import aiohttp  # ==3.8.4
from satorisynapse.lib.error import SseTimeoutFailure
from satorisynapse.lib.domain import Envelope, Ping, SYNAPSE_PORT
from satorisynapse.lib.requests import requests
from satorisynapse.lib.utils import greyPrint


class Synapse():
    ''' go-between for the flask server and the remote peers '''

    def __init__(self, port: int = None):
        self.port = port or SYNAPSE_PORT
        self.socketListener = None
        self.neuronListener = None
        self.peers: t.List[str] = []
        self.session = aiohttp.ClientSession()
        self.socket: socket.socket = self.createSocket()
        self.loop = asyncio.get_event_loop()
        self.broke = asyncio.Event()

    @staticmethod
    def satoriUrl(endpoint='') -> str:
        return 'http://localhost:24601/synapse' + endpoint

    ### INIT ###

    async def run(self):
        ''' runs forever '''
        await self.initNeuronListener()
        await self.initSocketListener()

    async def initNeuronListener(self):
        await self.cancelNeuronListener()
        self.neuronListener = asyncio.create_task(self.createNeuronListener())

    async def initSocketListener(self):
        await self.cancelSocketListener()
        self.socketListener = asyncio.create_task(self.listenToSocket())

    async def createNeuronListener(self):
        timeout = aiohttp.ClientTimeout(total=None, sock_read=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(Synapse.satoriUrl('/stream')) as response:
                    async for line in response.content:
                        if line.startswith(b'data:'):
                            asyncio.create_task(
                                self.handleNeuronMessage(
                                    line.decode('utf-8')[5:].strip()))
            except asyncio.TimeoutError:
                greyPrint('Neuron connection timed out...')
            except aiohttp.ClientConnectionError as e:
                greyPrint(f'Neuron connection error... {e}')
            except aiohttp.ClientError:
                greyPrint('Neuron error...')
            self.broke.set()

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
                sock.setblocking(False)
                return sock
            except Exception as e:
                greyPrint(f'unable to bind to port {localPort}, {e}')
                waitBeforeRaise(60)
                raise Exception('unable to create socket')

        return bind(self.port)

    async def listenToSocket(self):
        while not self.broke.is_set():
            try:
                data, address = await self.loop.sock_recvfrom(self.socket, 1024)
                if data != b'':
                    await self.handlePeerMessage(data, address)
            except asyncio.CancelledError:
                greyPrint('listen task cancelled')
                break
            except Exception as e:
                greyPrint(f'listenToSocket error: {e}')
                break
        self.broke.set()

    ### SPEAK ###

    async def speak(self, remoteIp: str, remotePort: int, data: str = ''):
        # greyPrint(f'sending to {remoteIp}:{remotePort} {data}')
        await self.loop.sock_sendto(self.socket, data.encode(), (remoteIp, remotePort))

    async def maybeAddPeer(self, ip: str):
        if ip not in self.peers:
            await self.addPeer(ip)

    async def addPeer(self, ip: str):
        await self.speak(ip, self.port, data=Ping().toJson)
        self.peers.append(ip)

    ### HANDLERS ###

    async def handleNeuronMessage(self, message: str):
        msg = Envelope.fromJson(message)
        await self.maybeAddPeer(msg.ip)
        await self.speak(
            remoteIp=msg.ip,
            remotePort=self.port,
            data=msg.vesicle.toJson)

    async def handlePeerMessage(self, data: bytes, address: t.Tuple[str, int]):
        # greyPrint(f'Received {data} from {address[0]}:{address[1]}')
        # # no need to ping back - it has issues anyway
        # ping = None
        # try:
        #    ping = Ping.fromMessage(data)
        # except Exception as e:
        #    greyPrint(f'error parsing message: {e}')
        # if isinstance(ping, Ping):
        #    if not ping.isResponse:
        #        await self.maybeAddPeer(address[0])
        #        await self.speak(
        #            remoteIp=address[0],
        #            remotePort=self.port,
        #            data=Ping(True).toJson)
        #        return
        #    if ping.isResponse:
        #        greyPrint(f'connection to {address[0]} established!')
        #        return
        await self.relayToNeuron(data=data, ip=address[0], port=address[1])

    async def relayToNeuron(self, data: bytes, ip: str, port: int):
        try:
            async with self.session.post(
                    Synapse.satoriUrl('/message'),
                    data=data,
                    headers={
                        'Content-Type': 'application/octet-stream',
                        'remoteIp': ip
                    },
            ) as response:
                if response.status != 200:
                    greyPrint(
                        f'POST request to {ip} failed with status {response.status}')
        except aiohttp.ClientError as e:
            # Handle client-side errors (e.g., connection problems).
            greyPrint(f'ClientError occurred: {e}')
        except asyncio.TimeoutError:
            # Handle timeout errors specifically.
            greyPrint('Request timed out')
        except Exception as e:
            # A catch-all for other exceptions - useful for debugging.
            greyPrint(f'Unexpected error occurred: {e}')

    ### SHUTDOWN ###

    async def cancelSocketListener(self):
        if self.socketListener:
            self.socketListener.cancel()
            try:
                await self.socketListener
            except asyncio.CancelledError:
                greyPrint('Socket listener task cancelled successfully.')

    async def cancelNeuronListener(self):
        if self.neuronListener:
            self.neuronListener.cancel()
            try:
                await self.neuronListener
            except asyncio.CancelledError:
                greyPrint('Neuron listener task cancelled successfully.')

    async def shutdown(self):
        await self.session.close()
        await self.cancelSocketListener()
        await self.cancelNeuronListener()
        self.socket.close()
        greyPrint('Synapse shutdown complete.')


def silentlyWaitForNeuron():
    while True:
        try:
            r = requests.get(Synapse.satoriUrl('/ping'))
            if r.status_code == 200:
                return
        except Exception as _:
            pass
        time.sleep(1)


async def main(port: int = None):

    async def waitForNeuron():
        notified = False
        while True:
            try:
                r = requests.get(Synapse.satoriUrl('/ping'))
                if r.status_code == 200:
                    if notified:
                        greyPrint('established connection to Satori Neuron')
                    return
            except Exception as _:
                if not notified:
                    greyPrint('waiting for Satori Neuron to start')
                    notified = True
            await asyncio.sleep(1)

    while True:
        await waitForNeuron()
        synapse = Synapse(port)
        await synapse.run()
        greyPrint("Satori P2P Relay is running. Press Ctrl+C to stop.")
        try:
            await synapse.broke.wait()
            raise Exception('synapse not running')
        except KeyboardInterrupt:
            pass
        except SseTimeoutFailure:
            pass
        except Exception as _:
            pass
        finally:
            await synapse.shutdown()


def runSynapse(port: int = None):
    try:
        asyncio.run(main(port))
    except KeyboardInterrupt:
        print('Interrupted by user')


if __name__ == '__main__':
    runSynapse()
