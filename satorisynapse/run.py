import sys


def run(type: str = 'threaded'):
    if type == 'threaded':
        from satorisynapse.synapse.threaded import runSynapse
    else:
        from satorisynapse.synapse.asynchronous import runSynapse
    runSynapse()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        run(sys.argv[1])
        exit(0)
    run()
    exit(0)
