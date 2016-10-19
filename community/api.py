"""API interactions with community.lsst.org API."""

import os
import csv
# import json
from collections import namedtuple
import requests


BASE_URL = 'https://community.lsst.org'
KEY = os.getenv('DISCOURSE_KEY')
USER = os.getenv('DISCOURSE_USER')

if KEY is None or USER is None:
    print('Please set $DISCOURSE_KEY and $DISCOURSE_USER environment '
          'variables.')


def get(path, params=None):
    """Generic GET against the Discourse API."""
    if not path.startswith('/'):
        path = '/' + path
    _params = {'api_key': KEY, 'api_user': USER}
    if params is not None:
        _params.update(params)
    r = requests.get(BASE_URL + path, params=_params)
    print(r.status_code)
    return r


def put(path, data=None, params=None):
    """Generic PUT against the Discourse API."""
    if not path.startswith('/'):
        path = '/' + path
    _params = {'api_key': KEY, 'api_user': USER}
    if params is not None:
        _params.update(params)
    r = requests.put(BASE_URL + path, data=data, params=_params)
    return r


def all_users(export_csv_path):
    """Iterate over all API users.

    Yields
    ------
    user : DiscourseUser
        A discourse user
    """
    exported_users = ExportList(export_csv_path)
    for u in exported_users.users:
        yield DiscourseUser.from_username(u.username, email=u.email)

    # base_path = '/groups/trust_level_0/members.json?limit=50&offset=50'
    # limit = 50
    # offset = 0
    # while True:
    #     r = get(base_path, params={'limit': limit, offset: offset})
    #     data = r.json()
    #     for user_json in data['members']:
    #         print(user_json['username'])
    #         yield DiscourseUser.from_username(user_json['username'])
    #     if len(data['members']) == limit:
    #         offset += limit
    #     else:
    #         break


class DiscourseUser(object):
    """A user in Discourse."""

    def __init__(self, json_data=None, email=None):
        super().__init__()
        self.data = json_data
        self._email = email

    @classmethod
    def from_username(cls, username, email=None):
        r = get('/users/{0}.json'.format(username))
        assert r.status_code == 200
        return cls(json_data=r.json(), email=email)

    @property
    def email(self):
        try:
            return self.data['user']['email']
        except KeyError:
            return self._email

    @property
    def groups(self):
        return self.data['user']['groups']


ExportUser = namedtuple('ExportUser',
                        ['id', 'name', 'username', 'email', 'title',
                         'created_at', 'last_seen_at', 'last_posted_at',
                         'last_emailed_at', 'trust_level', 'approved',
                         'suspended_at', 'suspended_till', 'blocked',
                         'active', 'admin', 'moderator', 'ip_address',
                         'topics_entered', 'posts_read_count', 'time_read',
                         'topic_count', 'post_count', 'likes_given',
                         'likes_received', 'Institution', 'group_names'])


class ExportList(object):
    """User list from a CSV export

    https://community.lsst.org/admin/users/list/active
    """

    def __init__(self, csv_path):
        super().__init__()
        self.users = []
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                if len(row) == 1:
                    continue
                p = ExportUser(*[s.strip() for s in row[:27]])
                self.users.append(p)

    def find_by_email(self, email):
        for u in self.users:
            if u.email == email:
                return u
        return None

    def find_by_username(self, username):
        for u in self.users:
            if u.username == username:
                return u
        return None
