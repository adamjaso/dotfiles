#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Client(object):
    def __init__(self, url, verify=True):
        self.url = url
        self.verify = verify
        self.token = None

    def auth_approle_login(self, role_id, secret_id):
        url = '/'.join([self.url, 'v1/auth/approle/login'])
        return requests.post(url, verify=self.verify,
                             json={'role_id': role_id, 'secret_id': secret_id})

    def auth_ldap_login(self, username, password):
        url = '/'.join([self.url, 'v1/auth/ldap/login', username])
        return requests.post(url, verify=self.verify,
                             json={'password': password})

    def write(self, path, data):
        if 'secret' not in path:
            path = '/'.join(['secret', path])
        url = '/'.join([self.url, 'v1', path])
        return requests.post(url, verify=self.verify, json=data,
                             headers={'X-Vault-Token': self.token})

    def read(self, path):
        if 'secret' not in path:
            path = '/'.join(['secret', path])
        url = '/'.join([self.url, 'v1', path])
        return requests.get(url, verify=self.verify,
                            headers={'X-Vault-Token': self.token})

    def list(self, path):
        if 'secret' not in path:
            path = '/'.join(['secret', path])
        url = '/'.join([self.url, 'v1', path])
        return requests.request('LIST', url, verify=self.verify,
                                headers={'X-Vault-Token': self.token})


def get_token(res):
    data = json.loads(res.text)
    try:
        return data['auth']['client_token']
    except:
        print(res.text, file=sys.stderr)
        raise


def get_data(res):
    res = json.loads(res.text)
    return res['data']


def authenticate_client(client, auth):
    t, un, pw = auth.split(':', 2)
    username = os.getenv(un)
    password = os.getenv(pw)
    if t == 'approle':
        res = client.auth_approle_login(username, password)
        client.token = get_token(res)
    elif t == 'ldap':
        res = client.auth_ldap_login(username, password)
        client.token = get_token(res)
    else:
        raise Exception('Unsupported auth: {}'.format(auth))


def main():
    args = argparse.ArgumentParser()
    args.add_argument('-u', '--url', dest='url', required=True)
    args.add_argument('-a', '--auth', dest='auth', required=True)
    args.add_argument('--no-verify', dest='no_verify', action='store_true')
    args.add_argument('action', choices=['read', 'write', 'list'])
    args.add_argument('path')
    args = args.parse_args()

    cli = Client(args.url, verify=not args.no_verify)
    authenticate_client(cli, args.auth)

    if args.action == 'read':
        res = cli.read(args.path)
        print(res.request.method, res.request.url,
              file=sys.stderr)  # noqa: E999
        json.dump(res.json(), sys.stdout, indent=2)
    elif args.action == 'list':
        res = cli.list(args.path)
        print(res.request.method, res.request.url,
              file=sys.stderr)  # noqa: E999
        json.dump(res.json(), sys.stdout, indent=2)
    elif args.action == 'write':
        data = json.load(sys.stdin)
        res = cli.write(args.path, data)
        print(res.request.method, res.request.url,
              file=sys.stderr)  # noqa: E999
        print(res.text)


if '__main__' == __name__:
    main()
