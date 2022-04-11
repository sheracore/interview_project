import random
import string

from django.utils.crypto import get_random_string


# def concatenate(left: str, right: str):
#     return "{}.{}".format(left, right)
#
#
# def split(concatenated: str):
#     left, _, right = concatenated.partition(".")
#     return left, right


class KeyGenerator:
    def __init__(self, prefix_length: int = 8, key_length: int = 32):
        self.prefix_length = prefix_length
        self.key_length = key_length

    def get_prefix(self):
        return get_random_string(self.prefix_length)

    def generate(self):
        # prefix = self.get_prefix()
        key = ''.join(random.choice(string.digits + string.ascii_letters)for i in range(self.key_length))
        return key

