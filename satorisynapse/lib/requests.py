
import urllib.request
import urllib.parse


class requests:
    '''
    simple wrapper for urllib to mimic requests.get and requests.post api.
    made so we could remove our dependancy on reuqests library and still use 
    the same api.
    '''
    @staticmethod
    def get(url: str) -> str:
        ''' Using urllib.request to open a URL and read the response '''
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read().decode('utf-8')
        except Exception as _:
            return ''

    @staticmethod
    def post(url: str, data: bytes, headers: dict = None) -> str:
        ''' Using urllib to post with an API similar to requests.post '''
        headers = headers or {}
        # If data is a dictionary, encode it into bytes using urllib.parse.urlencode
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        request = urllib.request.Request(
            url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(request) as response:
            return response.read().decode('utf-8')
