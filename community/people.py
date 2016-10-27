"""Lightweight attempt at tracking people from contacts db and community."""

import csv
import json
from collections import namedtuple


class Person(object):
    """A person in ContactsDB and Community."""
    def __init__(self, first=None, last=None, community_email=None,
                 username=None, active=False, community_groups=None,
                 cdb_email=None, cdb_collabs=None):
        super().__init__()
        self.first = first
        self.last = last
        self.community_email = community_email
        self.username = username
        self.active = active
        self.cdb_email = cdb_email
        if cdb_collabs is not None:
            self.cdb_collabs = cdb_collabs
        else:
            self.cdb_collabs = {}  # key is collaboration label
        if community_groups is not None:
            self.community_groups = community_groups
        else:
            self.community_groups = []

    @classmethod
    def from_cdb_person(cls, cdb_person):
        return cls(
            first=cdb_person.first,
            last=cdb_person.last,
            cdb_email=cdb_person.email,
            cdb_collabs={cdb_person.category: {'role': cdb_person.role}}
        )

    @property
    def json_data(self):
        return {
            'first': self.first,
            'last': self.last,
            'username': self.username,
            'community_email': self.community_email,
            'active': self.active,
            'cdb_email': self.cdb_email,
            'cdb_collabs': self.cdb_collabs,
            'community_groups': self.community_groups
        }

    def __str__(self):
        s = json.dumps(self.json_data, sort_keys=True, indent=2)
        return s

    def __repr__(self):
        s = 'Person(username={self.username!r}, first={self.first!r}, ' \
            'last={self.last!r}, community_email={self.community_email!r}, ' \
            'active={self.active!r}, cdb_email={self.cdb_email!r}, ' \
            'cdb_collabs={self.cdb_collabs!r})'
        return s.format(self=self)


class People(object):
    """A set of people known to ContactsDB and Community."""

    def __init__(self, people=None):
        super().__init__()
        if people is not None:
            self.people = people
        else:
            self.people = []

    def __str__(self):
        return '{0:d} people'.format(len(self.people))

    def __repr__(self):
        return 'People(people={self.people!r})'.format(self=self)

    @classmethod
    def from_json_data(cls, json_data):
        people = []
        for item in json_data:
            person = Person(**item)
            people.append(person)
        return cls(people)

    @classmethod
    def from_json_file(cls, json_path):
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        return cls.from_json_data(json_data)

    @property
    def json_data(self):
        return [p.json_data for p in self.people]

    def match_discourse_export_users_by_email(self, export_users):
        """Given a community.api.ExportList, register community user names
        and group membership in this People object.
        """
        for discourse_user in export_users.users:
            person = self.get_by_cdb_email(discourse_user.email)
            if person is None:
                continue
            print('Matched {discourse_user.email}'.format(
                discourse_user=discourse_user))
            self._import_community_export_user(person, discourse_user)

    def refresh_community_data(self, export_users):
        """Update Discourse/Community data about a Person who's already been
        matched between ContactsDB and the Community IDs.

        Information like username, email and group membership is updated.
        """
        for p in self.people:
            export_user = None
            if p.username is not None:
                export_user = export_users.find_by_username(p.username)
            elif export_user is None and p.community_email is not None:
                export_user = export_users.find_by_email(p.community_email)
            if export_user is None:
                print('Missing {p}'.format(p=p))
                continue

            # refresh data
            self._import_community_export_user(p, export_user)

    def write_json(self, path):
        with open(path, 'w') as f:
            json.dump(self.json_data, f, sort_keys=True, indent=2)

    def get_by_cdb_email(self, email):
        for p in self.people:
            if p.cdb_email == email and email is not None:
                return p
        return None

    def get_by_community_email(self, email):
        for p in self.people:
            if p.community_email == email and email is not None:
                return p
        return None

    def get_by_username(self, username):
        for p in self.people:
            if p.username == username and username is not None:
                return p
        return None

    def import_cdb_csv(self, csv_path):
        """Add and update people based on a ContactsDB export."""
        cdb_people = open_cdb_export(csv_path)
        self.import_cdb_people(cdb_people)

    def import_cdb_people(self, cdb_people):
        for cdb_person in cdb_people:
            existing_person = self.get_by_cdb_email(cdb_person.email)
            if existing_person:
                # check if the group information exists
                if cdb_person.category not in \
                        existing_person.cdb_collabs:
                    existing_person.cdb_collabs[cdb_person.category] = {
                        'role': cdb_person.role
                    }
            else:
                # Make a new person
                p = Person.from_cdb_person(cdb_person)
                self.people.append(p)

    def match_community_user(self, export_user, cdb_email):
        """Manually match a user from community.api.ExportList to an email
        address in ContactsDB.
        """
        p = self.get_by_cdb_email(cdb_email)
        assert p is not None
        self._import_community_export_user(p, export_user)

    def _import_community_export_user(self, p, export_user):
        p.active = True  # they've been seen on community
        p.username = export_user.username
        p.community_email = export_user.email
        p.community_groups = export_user.group_names

    def list_forum_invites(self, collaboration_name, group_name):
        """Print people to invite to a the forum for this collaboration."""
        for p in self.people:
            if collaboration_name in p.cdb_collabs and p.active is False:
                print(p.first, p.last, p.cdb_email)

    def list_group_invites(self, collaboration_name, group_name):
        """People people on the forum that should be invited to the group."""
        for p in self.people:
            if collaboration_name in p.cdb_collabs and p.active is True and \
                    group_name not in p.community_groups:
                print(p.first, p.last, p.cdb_email)


ContactDbPerson = namedtuple('ContactDbPerson', ['first', 'last', 'email',
                                                 'phone', 'company',
                                                 'category', 'role'])


def open_cdb_export(csv_path):
    people = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) == 1:
                continue
            p = ContactDbPerson(*[s.strip() for s in row[:7]])
            people.append(p)
    return people
