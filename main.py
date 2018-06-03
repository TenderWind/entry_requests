# -*- coding: UTF-8 -*-

import json
import motor.motor_tornado
import random
import string
import tornado.web

from bson.objectid import ObjectId
from hashlib import sha1
from tornado import gen
from tornado.ioloop import IOLoop


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


class RegistrationHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        username = request_body.get('username', None)
        if not username:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='username'))
            return
        password = request_body.get('password', None)
        if not password:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='password'))
            return
        password = hash_password(password)

        users = self.settings['db'].users
        user = yield users.find_one({'username': username})
        if user:
            self.write({'message': 'Username {username} already registered in the system'.format(
                username=user['username']
            )})
            return

        result = yield users.insert_one({
            'username': username,
            'password': password,
            'is_manager': None,
            'can_entry': None,
        })
        if result:
            self.write({'message': 'User successfully registered'})
            return

        return


class LoginHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        username = request_body.get('username', None)
        if not username:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='username'))
            return
        password = request_body.get('password', None)
        if not password:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='password'))
            return
        password = hash_password(password)

        users = self.settings['db'].users
        user = yield users.find_one({'username': username})
        if not user:
            self.write({'message': 'Username not registered in the system'})
            return
        if password != user['password']:
            self.write({'message': 'Invalid password'})
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
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='token'))
            return

        tokens = self.settings['db'].tokens
        token = yield tokens.find_one_and_delete({'token': token})
        if not token:
            self.send_error(401, reason='Invalid token')
            return

        self.write({'message': ''})
        return


class ManagerHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self, *args, **kwargs):
        SET = 'set_manager'
        REMOVE = 'remove_manager'
        command = (self.request.uri.split('/')[-1]
                   and self.request.uri.split('/')[-1] or self.request.uri.split('/')[-2])

        token = kwargs.get('token', None)
        if not token:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='token'))
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        token = yield tokens.find_one({'token': token})
        if not token:
            self.send_error(401, reason='Invalid token')
            return

        user_id = token['user_id']
        user = yield users.find_one({'_id': user_id})
        if command == SET:
            if user['is_manager']:
                self.write({'message': 'User {username} is manager'.format(username=user['username'])})
                return

            result = users.update_one({'_id': user_id}, {'$set': {
                'is_manager': True,
                'can_entry': True,
            }})
            if result:
                self.write({'message': 'User {username} is manager'.format(username=user['username'])})
                return
        elif command == REMOVE:
            if not user['is_manager']:
                self.write({'message': 'User {username} is not manager'.format(username=user['username'])})
                return

            result = users.update_one({'_id': user_id}, {'$set': {
                'is_manager': False,
            }})
            if result:
                self.write({'message': 'User {username} is not manager'.format(username=user['username'])})
                return

        return


class SendRequestHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        token = request_body.get('token', None)
        if not token:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='token'))
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        requests = self.settings['db'].requests
        token = yield tokens.find_one({'token': token})
        if not token:
            self.send_error(401, reason='Invalid token')
            return

        user_id = token['user_id']
        user = yield users.find_one({'_id': user_id})
        if user['can_entry']:
            self.write({'message': 'User {username} already has permission for entry'.format(
                username=user['username']
            )})
            return

        request = yield requests.find_one({'user_id': user_id})
        if request and request['status'] != RequestStatusIds.REJECTED:
            self.write({'message': 'User {username} already has submitted request'.format(
                username=user['username']
            )})
            return

        result = yield requests.insert_one({
            'user_id': user_id,
            'username': user['username'],
            'status': RequestStatusIds.NEW,
        })
        if result:
            self.write({'message': 'Request has been sent'})
            return

        return


class RequestsHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)

        token = request_body.get('token', None)
        if not token:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='token'))
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        requests = self.settings['db'].requests
        token = yield tokens.find_one({'token': token})
        if not token:
            self.send_error(401, reason='Invalid token')
            return

        user_id = token['user_id']
        user = yield users.find_one({'_id': user_id})
        if user['is_manager']:
            requests_cursor = requests.find({'user_id': {'$ne': user_id}})

            count = yield requests_cursor.count()
            if count == 0:
                self.write({'message': 'No requests'})

                return

            while (yield requests_cursor.fetch_next):
                request = requests_cursor.next_object()

                self.write({
                    'id': str(request['_id']),
                    'username': request['username'],
                    'status': RequestStatusIds.names[request['status']],
                })

            return
        else:
            request = yield requests.find_one({'user_id': user_id})
            if request:
                self.write({
                    'id': str(request['_id']),
                    'status': RequestStatusIds.names[request['status']],
                })

                return
            else:
                self.write({'message': 'User {username} does not have any requests'.format(
                    username=user['username']
                )})

        return


class AcceptHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        ACCEPT = 'accept'
        REJECT = 'reject'
        command = (self.request.uri.split('/')[-1]
                   and self.request.uri.split('/')[-1] or self.request.uri.split('/')[-2])

        request_body = json.loads(self.request.body)

        token = request_body.get('token', None)
        if not token:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='token'))
            return

        request_id = kwargs.get('request_id', None)
        if not request_id:
            self.send_error(400, reason='Parameter {param_name} is missing'.format(param_name='request_id'))
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        requests = self.settings['db'].requests
        token = yield tokens.find_one({'token': token})
        if not token:
            self.send_error(401, reason='Invalid token')
            return

        user_id = token['user_id']
        user = yield users.find_one({'_id': user_id})
        if not user['is_manager']:
            self.write({'message': 'User {username} does not have permission for this action'.format(
                username=user['username']
            )})
            return

        if not ObjectId.is_valid(request_id):
            self.send_error(401, reason='Invalid request_id')
        request = yield requests.find_one({'_id': ObjectId(request_id)})
        if not request:
            self.send_error(401, reason='Invalid request_id')
        result = requests.update_one({'_id': ObjectId(request_id)}, {'$set': {
            'status': command == ACCEPT and RequestStatusIds.ACCEPTED or RequestStatusIds.REJECTED,
        }})
        if result:
            result = users.update_one({'_id': request['user_id']}, {'$set': {
                'can_entry': command == ACCEPT,
            }})
            if result:
                if command == ACCEPT:
                    self.write({'message': 'User {username} has received a entry permit'.format(
                        username=request['username']
                    )})
                else:
                    self.write({'message': 'User {username} application was rejected'.format(
                        username=request['username']
                    )})

            return

        return


class Application(tornado.web.Application):
    def __init__(self):
        db = motor.motor_tornado.MotorClient('mongodb://localhost:27017').entry_requests

        handlers = [
            (r'/api/v1/registration/?', RegistrationHandler),
            (r'/api/v1/login/?', LoginHandler),
            (r'/api/v1/logout/?', LogoutHandler),
            (r"/api/v1/(?P<token>[a-zA-Z0-9]+)/set_manager/?", ManagerHandler),
            (r"/api/v1/(?P<token>[a-zA-Z0-9]+)/remove_manager/?", ManagerHandler),
            (r'/api/v1/send_request/?', SendRequestHandler),
            (r'/api/v1/requests/?', RequestsHandler),
            (r'/api/v1/requests/(?P<request_id>[a-zA-Z0-9]+)/accept/?', AcceptHandler),
            (r'/api/v1/requests/(?P<request_id>[a-zA-Z0-9]+)/reject/?', AcceptHandler),
        ]
        tornado.web.Application.__init__(self, handlers, db=db)


def main():
    app = Application()
    app.listen(8080)
    IOLoop.instance().start()


if __name__ == '__main__':
    # db = motor.motor_tornado.MotorClient('mongodb://localhost:27017').entry_requests
    # db.drop_collection('users')
    # db.drop_collection('tokens')
    # db.drop_collection('requests')
    main()
