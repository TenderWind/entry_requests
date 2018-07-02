# -*- coding: UTF-8 -*-

import json
import motor.motor_tornado
import pymongo

import tornado.web

from bson.objectid import ObjectId
from datetime import datetime
from tornado import gen
from tornado.ioloop import IOLoop

from func import hash_password, generate_token, RequestStatusIds, generate_missing_param_message


class SignUpHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)
        username = request_body.get('username', None)
        if not username:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('username')})
            return
        password = request_body.get('password', None)
        if not password:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('password')})
            return
        password = hash_password(password)

        users = self.settings['db'].users

        user = yield users.find_one({'username': username})
        if user:
            self.write({
                'error': {
                    'code': 4000,
                    'message': 'Username {username} already registered in the system'.format(
                        username=user['username'])
                }
            })
            return

        result = yield users.insert_one({
            'username': username,
            'password': password,
            'is_manager': False,
            'can_entry': False,
            'sign_up_date': datetime.utcnow(),
            'modification_date': None,
        })
        if result:
            self.write({'message': 'User successfully registered'})
            return

        return


class SignInHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)
        username = request_body.get('username', None)
        if not username:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('username')})
            return
        password = request_body.get('password', None)
        if not password:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('password')})
            return
        password = hash_password(password)

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens

        user = yield users.find_one({'username': username})
        if not user:
            self.write({
                'error': {
                    'code': 4001,
                    'message': 'Username not registered in the system'
                }
            })
            return
        if password != user['password']:
            self.write({
                'error': {
                    'code': 4002,
                    'message': 'Invalid password'
                }
            })
            return

        user_id = user['_id']
        token = yield tokens.find_one({'user_id': user_id})
        if token:
            self.write({'token': token['token']})
            return

        token = generate_token()
        result = yield tokens.insert_one({
            'user_id': user_id,
            'token': token,
        })
        if result:
            self.write({'token': token})
            return

        return


class SignOutHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)
        token = request_body.get('token', None)
        if not token:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('token')})
            return

        tokens = self.settings['db'].tokens

        token = yield tokens.find_one_and_delete({'token': token})
        if not token:
            self.set_status(401)
            self.write({'message': 'Invalid token'})
            return

        self.write({'message': 'User successfully signed out'})
        return


class UsersHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)
        token = request_body.get('token', None)
        if not token:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('token')})
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens

        token = yield tokens.find_one({'token': token})
        if not token:
            self.set_status(401)
            self.write({'message': 'Invalid token'})
            return
        user = yield users.find_one({'_id': token['user_id']})
        if not user['is_manager']:
            self.set_status(403)
            self.write({'message': 'User {username} does not have permission for this action'.format(
                username=user['username']
            )})
            return

        users_cursor = users.find().sort('username', pymongo.ASCENDING)
        count = yield users_cursor.count()
        if count == 0:
            self.write({'message': 'No users'})
            return
        users_list = []
        while (yield users_cursor.fetch_next):
            user = users_cursor.next_object()
            users_list.append({
                'id': str(user['_id']),
                'username': user['username'],
                'is_manager': user['is_manager'],
                'can_entry': user['can_entry'],
                'sign_up_date': user['sign_up_date'].strftime('%d.%m.%Y %H:%M:%S'),
                'modification_date': user['modification_date']
                    and user['modification_date'].strftime('%d.%m.%Y %H:%M:%S') or '',
            })
        if users_list:
            self.write(json.dumps(users_list))
            return

        return


class ManagerHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)
        token = request_body.get('token', None)
        if not token:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('token')})
            return
        username = request_body.get('username', None)
        if not username:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('username')})
            return
        is_manager = request_body.get('is_manager', None)
        if is_manager not in (True, False):
            self.set_status(400)
            self.write({'message': generate_missing_param_message('is_manager')})
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens

        token = yield tokens.find_one({'token': token})
        if not token:
            self.set_status(401)
            self.write({'message': 'Invalid token'})
            return
        # user = yield users.find_one({'_id': token['user_id']})
        # if not user['is_manager']:
        #     if not user['is_manager']:
        #         self.set_status(403)
        #         self.write({'message': 'User {username} does not have permission for this action'.format(
        #             username=user['username']
        #         )})
        #         return

        user = yield users.find_one({'username': username})
        if is_manager:
            if user['is_manager']:
                self.write({'message': 'User {username} already a manager'.format(username=user['username'])})
                return

            result = users.update_one({'username': username}, {'$set': {
                'is_manager': True,
                'can_entry': True,
                'modification_date': datetime.utcnow(),
            }})
            if result:
                self.write({'message': 'User {username} is a manager'.format(username=user['username'])})
                return
        else:
            if not user['is_manager']:
                self.write({'message': 'User {username} already not a manager'.format(username=user['username'])})
                return

            result = users.update_one({'username': username}, {'$set': {
                'is_manager': False,
                'modification_date': datetime.utcnow(),
            }})
            if result:
                self.write({'message': 'User {username} is not a manager'.format(username=user['username'])})
                return

        return


class SendRequestHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self, *args, **kwargs):
        request_body = json.loads(self.request.body)
        token = request_body.get('token', None)
        if not token:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('token')})
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        requests = self.settings['db'].requests

        token = yield tokens.find_one({'token': token})
        if not token:
            self.set_status(401)
            self.write({'message': 'Invalid token'})
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
            'status': RequestStatusIds.NEW,
            'creation_date': datetime.utcnow(),
            'modification_date': None,
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
            self.set_status(400)
            self.write({'message': generate_missing_param_message('token')})
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        requests = self.settings['db'].requests

        token = yield tokens.find_one({'token': token})
        if not token:
            self.set_status(401)
            self.write({'message': 'Invalid token'})
            return

        user_id = token['user_id']
        user = yield users.find_one({'_id': user_id})
        if user['is_manager']:
            requests_cursor = requests.find({'user_id': {'$ne': user_id}, 'status': {'$eq': RequestStatusIds.NEW}})

            count = yield requests_cursor.count()
            if count == 0:
                self.write({'message': 'No requests'})
                return
            requests_list = []
            while (yield requests_cursor.fetch_next):
                request = requests_cursor.next_object()
                user = yield users.find_one({'_id': request['user_id']})
                requests_list.append({
                    'id': str(request['_id']),
                    'username': user['username'],
                    'status': RequestStatusIds.names[request['status']],
                    'creation_date': request['creation_date'].strftime('%d.%m.%Y %H:%M:%S'),
                    'modification_date': request['modification_date']
                        and request['modification_date'].strftime('%d.%m.%Y %H:%M:%S') or '',
                })
            if requests_list:
                self.write(json.dumps(requests_list))
                return

            return
        else:
            request = yield requests.find_one({'user_id': user_id, 'status': {'$ne': RequestStatusIds.REJECTED}})
            if request:
                self.write({
                    'id': str(request['_id']),
                    'status': RequestStatusIds.names[request['status']],
                    'creation_date': request['creation_date'].strftime('%d.%m.%Y %H:%M:%S'),
                    'modification_date': request['modification_date']
                        and request['modification_date'].strftime('%d.%m.%Y %H:%M:%S') or '',
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
        request_body = json.loads(self.request.body)

        token = request_body.get('token', None)
        if not token:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('token')})
            return
        request_id = request_body.get('request_id', None)
        if not request_id:
            self.set_status(400)
            self.write({'message': generate_missing_param_message('request_id')})
            return
        can_entry = request_body.get('can_entry', None)
        if can_entry not in (True, False):
            self.set_status(400)
            self.write({'message': generate_missing_param_message('can_entry')})
            return

        users = self.settings['db'].users
        tokens = self.settings['db'].tokens
        requests = self.settings['db'].requests

        token = yield tokens.find_one({'token': token})
        if not token:
            self.set_status(401)
            self.write({'message': 'Invalid token'})
            return

        user_id = token['user_id']
        user = yield users.find_one({'_id': user_id})
        if not user['is_manager']:
            self.set_status(403)
            self.write({'message': 'User {username} does not have permission for this action'.format(
                username=user['username']
            )})
            return

        if not ObjectId.is_valid(request_id):
            self.set_status(401)
            self.write({'message': 'Invalid request_id'})
            return
        request = yield requests.find_one({'_id': ObjectId(request_id)})
        if not request:
            self.set_status(401)
            self.write({'message': 'Invalid request_id'})
            return

        result = requests.update_one({'_id': ObjectId(request_id)}, {'$set': {
            'status': can_entry and RequestStatusIds.ACCEPTED or RequestStatusIds.REJECTED,
            'modification_date': datetime.utcnow(),
        }})
        if result:
            result = users.update_one({'_id': request['user_id']}, {'$set': {
                'can_entry': can_entry,
                'modification_date': datetime.utcnow(),
            }})
            if result:
                if can_entry:
                    self.write({'message': 'User has received a entry permit'})
                else:
                    self.write({'message': 'User application was rejected'})
            return

        return


class Application(tornado.web.Application):
    def __init__(self):
        db = motor.motor_tornado.MotorClient('mongodb://localhost:27017').entry_requests

        api_version = '1.1'
        base_path = '/api/v{0}'.format(api_version)
        handlers = [
            (r'{0}/auth/sign_up/?'.format(base_path), SignUpHandler),
            (r'{0}/auth/sign_in/?'.format(base_path), SignInHandler),
            (r'{0}/auth/sign_out/?'.format(base_path), SignOutHandler),
            (r'{0}/users/?'.format(base_path), UsersHandler),
            (r'{0}/users/set_manager/?'.format(base_path), ManagerHandler),
            (r'{0}/users/send_request/?'.format(base_path), SendRequestHandler),
            (r'{0}/requests/?'.format(base_path), RequestsHandler),
            (r'{0}/requests/accept/?'.format(base_path), AcceptHandler),
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
