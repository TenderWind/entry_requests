# -*- coding: UTF-8 -*-

import json

from tornado import httpserver
from tornado import gen
from tornado.ioloop import IOLoop
import tornado.web
import motor.motor_tornado
from hashlib import sha1
import random
import string



def hash_password(password):
    return sha1(password).hexdigest()


def generate_token():
    r = random.SystemRandom()
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits

    return ''.join(alphabet[r.randint(0, len(alphabet) - 1)] for _ in range(18))



class RegistrationHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        username = request_body.get('username', None)
        if not username:
            self.send_error(400, reason='username should be setted')
            return
        password = request_body.get('password', None)
        if not password:
            self.send_error(400, reason='password should be setted')
            return
        password = hash_password(password)

        users = self.settings['db'].users
        user = yield users.find_one({'username': username})
        if user:
            self.send_error(400, reason='Username {username} already registered in the system'.format(
                username=user['username']))
            return

        result = yield users.insert_one({'username': username, 'password': password})
        if result:
            self.write('User successfully registered')
            return

        return


class LoginHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        username = request_body.get('username', None)
        if not username:
            self.send_error(400, reason='username should be setted')
            return
        password = request_body.get('password', None)
        if not password:
            self.send_error(400, reason='password should be setted')
            return
        password = hash_password(password)

        users = self.settings['db'].users
        user = yield users.find_one({'username': username})
        if not user:
            self.send_error(400, reason='Username not registered in the system')
            return
        if password != user['password']:
            self.send_error(400, reason='Invalid password')
            return

        user_id = user['_id']
        tokens = self.settings['db'].tokens
        token = yield tokens.find_one({'user_id': user_id})
        if token:
            self.write({'token': token['token']})
            return

        token = generate_token()
        result = yield tokens.insert_one({'user_id': user_id, 'token': token})
        if result:
            self.write({'token': token})
            return

        return


class LogoutHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        token = request_body.get('token', None)
        if not token:
            self.send_error(400, reason='token should be setted')
            return

        tokens = self.settings['db'].tokens
        token = yield tokens.find_one_and_delete({'token': token})
        if not token:
            self.send_error(401, reason='Invalid token')
            return

        self.write('')
        return


class Application(tornado.web.Application):
    def __init__(self):
        base_path = '/api/v1/{function}'
        db = motor.motor_tornado.MotorClient('mongodb://localhost:27017').entry_requests

        handlers = [
            (r'/api/v1/registration/?', RegistrationHandler),
            (r'/api/v1/login/?', LoginHandler),
            (r'/api/v1/logout/?', LogoutHandler),
            # (r"/api/v1/requsts/?", MainHandler),
            # (r"/api/v1/requsts/(?P<make>[a-zA-Z0-9_\-]+)/?", MainHandler),
            # (r"/api/v1/{function}/?", MainHandler),
        ]
        tornado.web.Application.__init__(self, handlers, db=db)


def main():
    app = Application()
    app.listen(8080)
    IOLoop.instance().start()


if __name__ == '__main__':
    main()

# регистрация пользователя registration -
# авторизация login -
# логаут logout
# регистрация менеджера set_magager
# отправка заявки send_request
# подтверждение или отказ от заявки (функционал менеджера) accept_requset reject_requst
# получение списка заявок (пользователь - заявки пользователя, менеджер - все заявки) request_list
# получение статуса заявки request

# обработка ошибок записи