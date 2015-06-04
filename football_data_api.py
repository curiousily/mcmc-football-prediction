from abc import ABCMeta, abstractmethod
from datetime import datetime
from collections import namedtuple
import re
import time
import os.path

import tortilla


__all__ = ['FootballData', 'Timeframe']

URL = 'http://api.football-data.org/alpha'

api = tortilla.wrap(URL)


#Results namedtuple so we can return result in an object
Results = namedtuple('Results', ['goalsHomeTeam', 'goalsAwayTeam'])


def requests_middleware(r, *args, **kwargs):
    """
    A middleware that edits the responses from the api.
    The api data contains the key "self" in various responses but using this breaks tortilla because it
    conflicts with python self. So we search and replace every key  "self" with "_self"
    """
    content = r.content.decode(r.encoding)
    content = content.replace('"self":', '"_self":')
    r._content = content.encode(r.encoding)

    #Sleep so we do not flood the server with requests

    time.sleep(1)


class FootballData():

    def __init__(self, api_key=None, api_key_file='key.txt'):
        headers = dict()
        if api_key is not None:
            api.config['headers']['X-Auth-Token'] = api_key

        if api_key_file is not None and os.path.isfile(api_key_file) :
            with open(api_key_file, 'r') as f:
                key = f.readline()
                api.config['headers']['X-Auth-Token'] = key

        self.soccerseason = SoccerSeason
        self.fixtures = Fixture
        self.teams = Team


class Timeframe():

    def __init__(self, past=False, no=7):
        self.past = past
        self.no = no

    @classmethod
    def past(cls, no):
        return cls(True, no)

    @classmethod
    def next(cls, no):
        return cls(False, no)

    def __str__(self):
        if self.past:
            direction = 'p'
        else:
            direction = 'n'

        return direction + str(self.no)


class PageBase():

    __metaclass__ = ABCMeta

    def __init__(self, id=None, data=None):
        if id is not None:
            self.data = self.get(id)
        else:
            self.data = data

    @property
    def id(self):
        self_link = self.data['_links']['_self']['href']
        return self._extract_id_from_link(self_link)

    def _extract_id_from_link(self, href):
        id = re.findall("\d+$", href)[0]
        return int(id)

    @staticmethod
    @abstractmethod
    def get(*id):
        pass

    @classmethod
    def all(cls):
        objects = list()
        all_data = cls().get()
        for line in all_data:
            objects.append(cls(data=line))
        return objects

    @classmethod
    def data_list(cls, data_list):
        objects = list()
        for line in data_list:
            objects.append(cls(data=line))
        return objects


class SoccerSeason(PageBase):

    @property
    def caption(self):
        return self.data['caption']

    @property
    def lastUpdated(self):
        return _strp_iso8601(self.data['lastUpdated'])

    @property
    def league(self):
        return self.data['league']

    @property
    def numberOfGames(self):
        return self.data['numberOfGames']

    @property
    def numberOfTeams(self):
        return self.data['numberOfTeams']

    @property
    def year(self):
        return int(self.data['year'])

    @property
    def teams(self):
        teams_data = api.soccerseasons(self.id).teams.get(hooks=dict(response=requests_middleware))
        return Team.data_list(teams_data['teams'])

    @property
    def leagueTable(self, matchday=None):
        params = {'matchday':matchday}
        league_table_data = api.soccerseasons(self.id).leagueTable.get(params=params, hooks=dict(response=requests_middleware))
        return LeagueTable.data_list(league_table_data['standing'])

    @property
    def fixtures(self, matchday=None, timeFrame=None):
        params = {'matchday': matchday}
        if timeFrame is not None:
            params['timeFrame'] = str(timeFrame)
        fixtures_table_data = api.soccerseasons(self.id).fixtures.get(params=params, hooks=dict(response=requests_middleware))
        return Fixture.data_list(fixtures_table_data['fixtures'])

    @staticmethod
    def get(season=None, *id):
        params = {'season':season}
        data = api.soccerseasons.get(*id, params=params, hooks=dict(response=requests_middleware))
        return data


class Team(PageBase):

    @property
    def code(self):
        return self.data['code']

    @property
    def crestUrl(self):
        return self.data['crestUrl']

    @property
    def name(self):
        return self.data['name']

    @property
    def shortName(self):
        return self.data['shortName']

    @property
    def squadMarketValue(self):
        return self.data['squadMarketValue']

    @property
    def fixtures(self, season=None, timeFrame=None, venue=None):
        params = {'season': season, 'venue': venue}
        if timeFrame is not None:
            params['timeFrame'] = str(timeFrame)
        fixtures_table_data = api.teams(self.id).fixtures.get(params=params, hooks=dict(response=requests_middleware))
        return Fixture.data_list(fixtures_table_data['fixtures'])

    @property
    def players(self):
        data = api.teams(self.id).players.get(hooks=dict(response=requests_middleware))
        return Player.data_list(data['players'])

    @staticmethod
    def get(*id):
        data = api.teams.get(*id, hooks=dict(response=requests_middleware))
        return data


class LeagueTable(PageBase):

    @property
    def goalDifference(self):
        return self.data['goalDifference']

    @property
    def goals(self):
        return self.data['goals']

    @property
    def goalsAgainst(self):
        return self.data['goalsAgainst']

    @property
    def playedGames(self):
        return self.data['playedGames']

    @property
    def points(self):
        return self.data['points']

    @property
    def position(self):
        return self.data['position']

    @property
    def teamName(self):
        return self.data['teamName']

    @property
    def team(self):
        team_link = self.data['_links']['team']['href']
        id = re.findall("\d+$", team_link)[0]
        return Team(id=id)

    @staticmethod
    def get(*id):
        data = api.teams.get(*id, hooks=dict(response=requests_middleware))
        return data


class Fixture(PageBase):

    @property
    def awayTeamName(self):
        return self.data['awayTeamName']

    @property
    def date(self):
        return self.data['date']

    @property
    def homeTeamName(self):
        return self.data['homeTeamName']

    @property
    def matchday(self):
        return self.data['matchday']

    @property
    def result(self):
        result = Results(goalsAwayTeam=self.data['result']['goalsAwayTeam'],
                         goalsHomeTeam=self.data['result']['goalsHomeTeam'])
        return result

    @property
    def status(self):
        return self.data['status']

    @property
    def awayTeam(self):
        id = self._extract_id_from_link(self.data['_links']['awayTeam']['href'])
        return Team(id)

    @property
    def homeTeam(self):
        id = self._extract_id_from_link(self.data['_links']['homeTeam']['href'])
        return Team(id)

    @property
    def soccerseason(self):
        id = self._extract_id_from_link(self.data['_links']['soccerseason']['href'])
        return SoccerSeason(id)

    @staticmethod
    def get(timeFrame=None, *id):
        params = dict()
        if timeFrame is not None:
            params['timeFrame'] = str(timeFrame)
        data = api.fixtures.get(*id, params=params, hooks=dict(response=requests_middleware))
        if 'fixture' in data:
            return data['fixture']
        else:
            return data['fixtures']


class Player(PageBase):

    @property
    def id(self):
        return self.data['id']

    @property
    def contractUntil(self):
        return self.data['contractUntil']

    @property
    def dateOfBirth(self):
        return self.data['dateOfBirth']

    @property
    def jerseyNumber(self):
        return self.data['jerseyNumber']

    @property
    def marketValue(self):
        return self.data['marketValue']

    @property
    def name(self):
        return self.data['name']

    @property
    def nationality(self):
        return self.data['nationality']

    @property
    def position(self):
        return self.data['position']

    @staticmethod
    def get(*id):
        pass



def _strp_iso8601(string):
    #Replace Z with UTC
    string = string.replace('Z', ' UTC')
    return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S %Z")
