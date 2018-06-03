# -*- coding: UTF-8 -*-

import json

from tornado import httpserver
from tornado import gen
from tornado.ioloop import IOLoop
import tornado.web
import motor.motor_tornado


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


class MainHandler(tornado.web.RequestHandler):
    def post(self, *args, **kwargs):
        self.write('Hello, world')


class Application(tornado.web.Application):
    def __init__(self):
        base_path = '/api/v1/{function}'
        db = motor.motor_tornado.MotorClient('mongodb://localhost:27017').entry_requests

        handlers = [
            (r"/api/v1/registration/?", RegistrationHandler),
            (r"/api/v1/login/?", MainHandler),
            (r"/api/v1/logout/?", MainHandler),
            (r"/api/v1/requsts/?", MainHandler),
            (r"/api/v1/requsts/(?P<make>[a-zA-Z0-9_\-]+)/?", MainHandler),
            (r"/api/v1/{function}/?", MainHandler),
        ]
        tornado.web.Application.__init__(self, handlers, db=db)


def main():
    app = Application()
    app.listen(8080)
    IOLoop.instance().start()


if __name__ == '__main__':
    main()

# регистрация пользователя registration
# авторизация login
# логаут logout
# регистрация менеджера set_magager
# отправка заявки send_request
# подтверждение или отказ от заявки (функционал менеджера) accept_requset reject_requst
# получение списка заявок (пользователь - заявки пользователя, менеджер - все заявки) request_list
# получение статуса заявки request
