import sys


def run(
    type: str = 'threaded',
    port: str = None,
    version: str = None,
    restartPath: str = None,
    installDir: str = None,
):
    if type == 'threaded':
        from satorisynapse.synapse.threaded import runSynapse
    else:
        from satorisynapse.synapse.asynchronous import runSynapse
    runSynapse(
        port=int(port) if isinstance(port, str) else port,
        version=version,
        restartPath=restartPath,
        installDir=installDir)
    exit(0)


if __name__ == '__main__':
    if len(sys.argv) == 6:
        run(type=sys.argv[1],
            port=sys.argv[2],
            version=sys.argv[3],
            restartPath=sys.argv[4],
            installDir=sys.argv[5])
    elif len(sys.argv) == 5:
        run(type=sys.argv[1],
            port=sys.argv[2],
            version=sys.argv[3],
            restartPath=sys.argv[4])
    elif len(sys.argv) == 4:
        run(type=sys.argv[1],
            port=sys.argv[2],
            version=sys.argv[3])
    elif len(sys.argv) == 2:
        if sys.argv[1] == 'help':
            print(
                "Usage: python3 -m satorisynapse.run ['threaded' or 'async'] [port number] [version (docker image version)] [restartPath] [installDir]")
        else:
            run(type=sys.argv[1])
    else:
        run()
