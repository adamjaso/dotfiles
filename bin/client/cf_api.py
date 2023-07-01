#!/usr/bin/env python3
import re
import os
import sys
import json
import time
from base64 import b64decode
from urllib import parse
from urllib import request as request_
from urllib.parse import urlencode
from urllib.error import HTTPError


def is_expired(jwt, now):
    parts = jwt.split('.', 2)
    if len(parts) != 3:
        raise RequestException('JWT is invalid: {}'.format(jwt))
    data = b64decode((parts[1] + '==')).decode('utf-8')
    data = json.loads(data)
    if 'exp' not in data:
        raise RequestException('JWT expiration not found: {}'.format(data))
    return int(data['exp']) <= now


class RequestException(Exception):
    request = None

    def __init__(self, msg, request=None):
        super(RequestException, self).__init__(msg)
        self.request = request


class ResponseException(Exception):
    response = None

    def __init__(self, msg, response=None):
        super(ResponseException, self).__init__(msg)
        self.response = response


class ConfigException(Exception):
    config = None

    def __init__(self, msg, config=None):
        super(ConfigException, self).__init__(msg)
        self.config = config


def configure(config):
    url = '/'.join([config.base_url, 'v2/info'])
    req = request_.Request(url)
    try:
        res = request_.urlopen(req)
    except HTTPError as e:
        raise ResponseException('Error configuring {}.'
                                .format(e.status), e)
    config.info = json.load(res)
    return config


def authenticate(config):
    config.assert_info()
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'client_id': config.client_id,
            'client_secret': config.client_secret}
    if config.username is not None and config.password is not None:
        if config.auth is None:
            data['grant_type'] = 'password'
            data['username'] = config.username
            data['password'] = config.password
        elif 'refresh_token' in config.auth:
            data['grant_type'] = 'refresh_token'
            data['refresh_token'] = config.auth['refresh_token']
        else:
            raise RequestException('Unable to build authentication request.')
    else:
        data['grant_type'] = 'client_credentials'
    data = parse.urlencode(data).encode('utf-8')
    url = '/'.join([config.info['token_endpoint'], 'oauth/token'])
    req = request_.Request(url, method='POST', data=data, headers=headers)
    try:
        res = request_.urlopen(req)
    except HTTPError as e:
        raise ResponseException('Error authenticating {}.'.format(e.status), e)
    config.auth = json.load(res)
    return config


class Config(object):
    base_url = os.getenv('CF_URL')
    version = os.getenv('CF_VERSION', 'v2')
    username = os.getenv('CF_USERNAME')
    password = os.getenv('CF_PASSWORD')
    client_id = os.getenv('CLIENT_ID', 'cf')
    client_secret = os.getenv('CLIENT_SECRET', '')
    info = None
    auth = None

    def assert_info(self):
        if self.info is None:
            raise ConfigException('Config info is required.')

    def assert_auth(self):
        self.assert_info()
        if self.auth is None:
            raise ConfigException('Config auth is required.')


class Resource(object):
    data = None

    def __init__(self, data):
        self.data = data

    def __repr__(self):
        name = str(self.host or self.label or self.name)
        return '\t'.join([self.guid, name])

    def __getattr__(self, name):
        return self.data[name]

    def __getitem__(self, name):
        return self.data[name]

    def __contains__(self, name):
        return name in self.data


class V2Resource(Resource):

    @property
    def guid(self):
        return self.data['metadata'].get('guid')

    @property
    def host(self):
        return self.data['entity'].get('host')

    @property
    def name(self):
        return self.data['entity'].get('name')

    @property
    def label(self):
        return self.data['entity'].get('label')

    @property
    def space_guid(self):
        return self.data['entity'].get('space_guid')

    @property
    def organization_guid(self):
        return self.data['entity'].get('organization_guid')


class V3Resource(Resource):

    @property
    def guid(self):
        return self.data.get('guid')

    @property
    def name(self):
        return self.data.get('name')

    @property
    def host(self):
        return self.data.get('host')

    @property
    def label(self):
        return self.data.get('label')

    @property
    def space_guid(self):
        try:
            return self['relationships']['space']['data']['guid']
        except KeyError:
            return None

    @property
    def organization_guid(self):
        try:
            return self['relationships']['organization']['data']['guid']
        except KeyError:
            return None


class Response(object):
    resource_class = Resource
    response = None
    data = None

    def __init__(self, response):
        self.response = response
        self.data = json.load(response)

    def assert_ok(self):
        raise ResponseException('Response.assert_ok() not implemented.')

    @property
    def ok(self):
        return 200 <= self.response.status < 300

    @property
    def resources(self):
        self.assert_ok()
        if 'resources' in self.data:
            return [self.resource_class(r)
                    for r in self.data.get('resources', [])]
        else:
            return [self.resource_class(self.data)]

    @property
    def resource(self):
        self.assert_ok()
        if 'resources' in self.data:
            return self.resource_class(next(iter(self.data['resources'])))
        else:
            return self.resource_class(self.data)


class V2Response(Response):
    resource_class = V2Resource

    @property
    def next_url(self):
        return self.data.get('next_url', None)

    def assert_ok(self):
        if not self.ok:
            if 'error_code' in self.data:
                msg = self.data['error_code']
            else:
                msg = str(self.response)
            msg = 'HTTP {} {}'.format(self.response.status, msg)
            msg = 'An API error occurred: {}.'.format(msg)
            raise ResponseException(msg, self.response)


class V3Response(Response):
    resource_class = V3Resource

    @property
    def next_url(self):
        if 'pagination' in self.data and \
                'next' in self.data['pagination'] and \
                self.data['pagination']['next'] is not None and \
                'href' in self.data['pagination']['next']:
            return self.data['pagination']['next']['href']
        return None

    def assert_ok(self):
        if not self.ok:
            if 'errors' in self.data:
                msg = ' - '.join([
                    self.data['errors'][0]['title'],
                    self.data['errors'][0]['detail'],
                ])
            else:
                msg = str(self.response)
            msg = 'HTTP {} {}'.format(self.response.status, msg)
            msg = 'An API error occurred: {}.'.format(msg)
            raise ResponseException(msg, self.response)


class Request(object):
    response_class = Resource
    config = None
    method = None
    body = None
    url = None

    def __init__(self, config, path, **query):
        self.config = config
        self.headers = {}
        self.set_url(path, **query)

    def set_url(self, path, **query):
        path = re.sub(r'^(https?://[^/]+)?/(v\d+/)?', '', path)
        parts = list(parse.urlsplit(self.config.base_url))
        parts[2] = '/'.join([self.config.version, path])
        parts[3] = urlencode(query)
        self.url = parse.urlunsplit(parts)
        return self

    def set_body(self, body):
        self.body = json.dumps(body).encode('utf-8')
        self.headers['Content-Type'] = 'application/json'
        return self

    def send(self, method):
        if self.config.auth is None or \
                is_expired(self.config.auth['access_token'], time.time()):
            authenticate(self.config)
        auth = 'bearer {}'.format(self.config.auth['access_token'])
        headers = {'Authorization': auth,
                   'Accept': 'application/json'}
        req = request_.Request(self.url, method=method, data=self.body,
                               headers=headers)
        try:
            res = request_.urlopen(req)
        except HTTPError as e:
            res = e
        return self.response_class(res)

    def get(self):
        return self.send('GET')

    def post(self):
        return self.send('POST')

    def put(self):
        return self.send('PUT')

    def delete(self):
        return self.send('DELETE')


class V2Request(Request):
    response_class = V2Response


class V3Request(Request):
    response_class = V3Response


class CloudController(object):
    request_class = None
    config = None

    def __init__(self, config, request_class=V2Request):
        self.config = config
        self.request_class = request_class

    def request(self, path, **query):
        return self.request_class(self.config, path, **query)


def get_all_resources(req, verbose=False):
    while True:
        if verbose:
            print(req.url, file=sys.stderr)
        res = req.get()
        for r in res.resources:
            yield r
        if res.next_url is None:
            break
        req.set_url(res.next_url)


def new_cloud_controller(config):
    configure(config)
    request_class = getattr(sys.modules[__name__],
                            config.version.upper() + 'Request')
    return CloudController(config, request_class)


def main():
    import argparse

    args = argparse.ArgumentParser()
    args.add_argument('-X', dest='method', default='GET')
    args.add_argument('-d', dest='body', action='store_true')
    args.add_argument('-l', dest='list', action='store_true')
    args.add_argument('-v', dest='verbose', action='store_true')
    args.add_argument('--short', action='store_true')
    args.add_argument('url')
    args = args.parse_args()
    config = Config()
    cc = new_cloud_controller(config)
    req = cc.request(args.url)
    if args.body:
        req.body = sys.stdin.read().encode('utf-8')
    if args.list:
        res = get_all_resources(req, args.verbose)
    else:
        res = req.send(args.method).resources
    if args.short:
        for item in res:
            print(item)
    else:
        json.dump(list(res), sys.stdout, indent=2, default=lambda o: o.data)


if __name__ == '__main__':
    main()
