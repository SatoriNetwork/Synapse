def greyPrint(msg: str):
    return print(
        "\033[90m"  # grey
        + msg +
        "\033[0m"  # reset
    )


def satoriUrl(endpoint='') -> str:
    return 'http://localhost:24601/synapse' + endpoint
