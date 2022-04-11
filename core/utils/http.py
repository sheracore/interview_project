from unittest.mock import patch
from urllib3.util.url import _remove_path_dot_segments
import mimetypes
import requests


def request(url, method=None, headers=None, verify=None, timeout=(5, 30),
            json=None, data=None, files=None, params=None):
    """ Request to agent """

    def mocked_remove_path_dot_segments(path):
        if path.endswith('/.') or '/./' in path:
            return path

        return _remove_path_dot_segments(path)

    method = method or 'GET'
    with patch('urllib3.util.url._remove_path_dot_segments',
               new=mocked_remove_path_dot_segments):
        content_type = headers.get('Content-Type')
        if files and content_type and 'multipart/form-data' in content_type:

            boundary = content_type.split(';')[-1].strip().split('=')[-1]
            data = StreamingMultipart(data, files, boundary)

            response = requests.request(method,
                                        url,
                                        headers=headers,
                                        verify=verify,
                                        timeout=timeout,
                                        json=json,
                                        data=data,
                                        params=params)
        else:
            response = requests.request(method,
                                        url,
                                        headers=headers,
                                        verify=verify,
                                        timeout=timeout,
                                        json=json,
                                        data=data,
                                        files=files,
                                        params=params)

    return response


class StreamingMultipart(object):
    def __init__(self, data, files, boundary, chunk_size=1024):
        self.data = data
        self.files = files
        self.boundary = boundary
        self.itering_files = False
        self.chunk_size = chunk_size

    def __len__(self):
        # TODO Optimize as currently we are iterating data and files twice
        # Possible solution: Cache body into file and stream from it
        size = 0
        for i in self.__iter__():
            size += len(i)
        return size

    def __iter__(self):
        return self.generator()

    def generator(self):
        for (k, v) in self.data.items():
            yield ('%s\r\n\r\n' % self.build_multipart_header(k)).encode('utf-8')
            yield ('%s\r\n' % str(v)).encode('utf-8')

        for (k, v) in self.files.items():
            content_type = mimetypes.guess_type(v.name)[0] or 'application/octet-stream'
            yield ('%s\r\n\r\n' % self.build_multipart_header(k, v.name, content_type)).encode('utf-8')

            # Seek back to start as __len__ has already read the file
            v.seek(0)

            # Read file chunk by chunk
            while True:
                data = v.read(self.chunk_size)
                if not data:
                    break
                yield data
            yield b'\r\n'
        yield self.build_multipart_footer().encode('utf-8')

    def build_multipart_header(self, name, filename=None, content_type=None):
        output = []
        output.append('--%s' % self.boundary)

        string = 'Content-Disposition: form-data; name="%s"' % name
        if filename:
            string += '; filename="%s"' % filename
        output.append(string)

        if content_type:
            output.append('Content-Type: %s' % content_type)

        return '\r\n'.join(output)

    def build_multipart_footer(self):
        return '--%s--\r\n' % self.boundary
