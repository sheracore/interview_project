import requests
from django.conf import settings


def validate_download_size(url):
    """
    Validate URL file size

    :param url: URL of file to check
    :returns: True/False wether file size valid or not, Error to show
    """
    try:
        resp = requests.head(url, allow_redirects=True)
    except requests.exceptions.RequestException:
        return False, 'There was an error downloading file.'

    if int(resp.headers.get('content-length', 0)) > settings.MAX_DOWNLOAD_SIZE:
        return False, 'File too large.'

    return True, None
