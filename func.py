# -*- coding: UTF-8 -*-

import random
import string

from hashlib import sha1


def hash_password(password):
    return sha1(password).hexdigest()


def generate_token():
    r = random.SystemRandom()
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits

    return ''.join(alphabet[r.randint(0, len(alphabet) - 1)] for _ in range(18))


class RequestStatusIds:
    NEW = 0
    ACCEPTED = 1
    REJECTED = 2

    names = {
        NEW: 'new',
        ACCEPTED: 'accepted',
        REJECTED: 'rejected',
    }


def generate_missing_param_message(param_name):
    return 'Parameter {param_name} is missing'.format(param_name=param_name)
