

import time
from nebula3.common.ttypes import ErrorCode
import pandas as pd
from nebula3.gclient.net import Connection
from nebula3.gclient.net.SessionPool import SessionPool
from nebula3.Config import SessionPoolConfig
from nebula3.common import *
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from gdb_clients import GdbFactory
from nebula3.data.ResultSet import ResultSet
from typing import Dict


def result_to_df(result: ResultSet) -> Dict:
    if not result.is_succeeded():
        return None
    columns = result.keys()
    d: Dict[str, list] = {}
    for col_num in range(result.col_size()):
        col_name = columns[col_num]
        col_list = result.column_values(col_name)
        d[col_name] = [x.cast() for x in col_list]
    return d

class Nebula(GdbFactory):
    def __init__(self,database="defaultdb"):
        config = Config()
        config.max_connection_pool_size = 10
        self.connection_pool = ConnectionPool()
        self.database = database
        ok = self.connection_pool.init([('127.0.0.1', 9669)], config)
        if not ok:
            exit(1)

        with self.get_session() as session:
            result = result_to_df(session.execute(f'CREATE SPACE IF NOT EXISTS {self.database} (vid_type=FIXED_STRING(30))'))
            assert result != None

    def get_session(self):
        return self.connection_pool.session_context('root', 'nebula')

    def run(self, query):
        time.sleep(2.5)
        with self.get_session() as session:
            session.execute(f'USE {self.database}')
            result = session.execute(query)
            df = result_to_df(result)
            return df, 0
    
    def batch_run(self, query):
        with self.get_session() as session:
            session.execute(f'USE {self.database}')
            for q in query:
                session.execute(q)

    def clear(self):
        with self.get_session() as session:
            result = result_to_df(session.execute(f'DROP SPACE IF EXISTS {self.database}'))
            assert result != None


if __name__ == '__main__':
    nb = Nebula("nbtest")

    with open('./cypher/ngql/schema/create.log', 'r') as f:
        while True:
            statement = f

    nb.clear()
