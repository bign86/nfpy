#
# Query builder for DB
#

from collections import OrderedDict
from copy import deepcopy
from operator import itemgetter
from typing import (Generator, List, Sequence)

from nfpy.Tools import (Singleton, Exceptions as Ex)

from .DB import get_db_glob
from .Table import (Table, Column)


class QueryBuilder(metaclass=Singleton):
    """ Class to store the tables information and create queries. """

    def __init__(self):
        self._db = get_db_glob()
        self._tables = {}

    # http://sebastianraschka.com/Articles/2014_sqlite_in_python_tutorial.html
    def _fetch_table_info(self, table: str) -> Table:
        """ Fetch the columns and info for table from DB:
            (id, name, type, notnull, default_value, primary_key)
        """
        res = self._db.execute("PRAGMA TABLE_INFO([{}]);".format(table)).fetchall()
        if not res:
            raise Ex.MissingData('Table {} not found in the database'.format(table))
        res = sorted(res, key=itemgetter(0))

        l = []
        for r in res:
            c = Column(str(r[1]))
            c.ordinal = int(r[0])
            c.type = str(r[2])
            c.notnull = True if r[3] else False
            c.is_primary = True if r[5] else False
            l.append(c)

        t = Table(table)
        t.set_fields(l)

        self._add_table(t)
        return t

    def _get_table(self, table: str) -> Table:
        """ Return the Table object from the dictionary having the right name. """
        try:
            t = self._tables[table]
        except KeyError:
            t = self._fetch_table_info(table)
        return t

    def _add_table(self, table: Table):
        """ Add the Table object to the dictionary. """
        assert isinstance(table, Table)
        self._tables[table.name] = table

    def print_structure(self, table: str):
        """ Print out the structure of the table. """
        t = self._get_table(table)
        print(t.structure)

    def exists_table(self, table: str) -> bool:
        """ Return True or False whether the input table exists. """
        q = """SELECT name FROM sqlite_master WHERE type = 'table' AND name = '{}';"""
        res = self._db.execute(q.format(table)).fetchall()
        return False if not res else True

    def get_tables_list(self) -> List[str]:
        """ List all the tables in the database. """
        q = """SELECT name FROM sqlite_master WHERE type IN ('table','view')
               AND name NOT LIKE 'sqlite_%' ORDER BY 1;"""
        res = self._db.execute(q).fetchall()
        return [t[0] for t in res]

    def get_columns(self, table: str) -> OrderedDict:
        """ Return the table's dictionary of column objects. """
        return self._get_table(table).columns

    def get_fields(self, table: str) -> Generator[str, None, None]:
        """ Return the generator of fields in table. """
        return self._get_table(table).get_fields()

    def get_keys(self, table: str) -> Generator[str, None, None]:
        """ Return the generator of primary keys. """
        return self._get_table(table).get_keys()

    def is_primary(self, table: str, field: str) -> bool:
        """ Return True if field is a primary key """
        return self._get_table(table).is_primary(field)

    def new_from_existing(self, table: str, add: dict = None,
                          remove: Sequence = None) -> Table:
        """ Create a Table object by adding/removing selected columns from an
            existing one.

            Input:
                table [str]: table to be used as base
                add [dict]: dictionary of columns and properties to add
                remove [Sequence]: sequence of columns to remove

            Bugs & Limitations:
                It is currently not possible to add a column with primary key enabled.
        """
        t = deepcopy(self._get_table(table))

        # Add columns
        if add:
            i = len(t)
            for k, v in add.items():
                c = Column(k)
                c.ordinal = i
                c.type = v[0]
                c.notnull = True if 'NOT NULL' in v else False
                c.is_primary = False
                t.add_field(c)
                i = i + 1

        # Remove columns
        if remove:
            for c in remove:
                t.remove_field(c)

        return t

    def select(self, table: str, fields: Sequence = None, rolling: Sequence = (),
               keys: Sequence = None, partial_keys: Sequence = (),
               where: str = "", order: str = None) -> str:
        """ Builds a select query for input table:

            Input:
                table [str]: for the from clause
                fields [Sequence[str]]: if present select only these columns
                rolling [Sequence[str]]: if present remove these from the list
                    of keys used for the where condition
                keys [Sequence[str]]: if present use only these keys to create
                    the where condition, if given empty no keys will be used.
                    If None is given use ALL primary keys to build the query
                partial_keys [Sequence[str]]: additional keys to be evaluated
                    by a 'like' clause. If none are given, none are used
                where [str]: additional where condition
                order [str]: additional order condition
            
            Return:
                query [str]: query ready to be used in an execute
        """
        t = self._get_table(table)

        if not fields:
            fields = t.get_fields()
        query = "select [" + "],[".join(fields) + "] from [" + table + "]"

        # where on keys
        if keys is None:
            if not partial_keys:
                keys = (k for k in t.get_keys() if k not in rolling)
            else:
                keys = ()
        qk = ["[" + k + "] = ? " for k in keys]

        # like conditions
        qk += ["[" + k + "] like ? " for k in partial_keys]

        # where on rolling
        for r in rolling:
            qk += ["[" + r + "] >= ? ", "[" + r + "] <= ? "]

        # handle the external where
        if len(where) > 0:
            qk.append(where)

        # build the complete where statement
        q_where = " and ".join(map(str, qk))
        if len(q_where) > 0:
            query += " where " + q_where

        # add ordering
        if order:
            query += " order by " + order

        return query + ';'

    def insert(self, ins_table: str, ins_fields: Sequence = (), **kwargs) -> str:
        """ Builds an insert query for input table:
            Input:
                ins_table [str]: for the from clause
                ins_fields [Sequence[str]]: list of fields to insert
                kwargs [Any]: arguments for a 'select' query

            Return:
                query [str]: query ready to be used in an execute
        """
        return self._get_insert(ins_table, ins_fields, 'insert', **kwargs)

    def merge(self, ins_table: str, ins_fields: Sequence = (), **kwargs) -> str:
        """ Builds an insert or replace query for input table:
            Input:
                ins_table [str]: for the from clause
                ins_fields [Sequence[str]]: list of fields to insert
                kwargs [Any]: arguments for a 'select' query

            Return:
                query [str]: query ready to be used in an execute
        """
        return self._get_insert(ins_table, ins_fields, 'insert or replace', **kwargs)

    def _get_insert(self, ins_table: str, ins_fields: Sequence,
                    command: str, **kwargs) -> str:
        """ Creates an insert like query. """
        keys = self.get_keys(ins_table)
        if not ins_fields:
            ins_fields = self.get_fields(ins_table)

        miss_keys = set(keys) - set(ins_fields)
        if miss_keys:
            msg = "Missing the following keys in the insert list " + \
                  ",".join(map(str, miss_keys))
            raise ValueError(msg)

        query = command + " into [" + str(ins_table) + "]"
        query += " ([" + "],[".join(ins_fields) + "]) "

        if not kwargs:
            query += " values (" + ",".join(['?'] * len(ins_fields)) + ");"
        else:
            query += self.select(**kwargs)

        return query

    def update(self, table: str, fields: Sequence = (), keys: Sequence = (),
               where: str = "") -> str:
        """ Builds an insert query the for input table. The where condition is
            applied by default on the primary key of the table:
            
            Input:
                table [str]: for the from clause
                fields [Sequence[str]]: list of fields to update
                keys [Sequence[str]]: if present use only these keys to create
                    the where condition, if given empty no keys will be used.
                    If None is given use ALL primary keys to build the query
                where [str]: additional where condition

            Return:
                query [str]: query ready to be used in an execute
        """
        # FIXME: add check on keys for safety
        if not keys:
            keys = self.get_keys(table)

        if not fields:
            fields = self.get_fields(table)

        query = "update [" + str(table) + "]"
        query += " set [" + "] = ?, [".join(fields) + "] = ?"
        query += " where " + " = ? and ".join(keys) + " = ?" + where

        return query + ';'

    def upsert(self, table: str, fields: Sequence = None, where: str = "") -> str:
        """ Builds an upsert query for the input table. The where condition is
            applied by default on the primary key of the table:

            Input:
                table [str]: for the from clause
                fields [Sequence[str]]: list of fields to update
                where [str]: additional where condition

            Return:
                query [str]: query ready to be used in an execute
        """
        keys = self.get_keys(table)
        if not fields:
            fields = self.get_fields(table)

        query = "insert into [" + str(table) + "]"
        query += " ([" + "],[".join(fields) + "]) "
        query += " values (" + ",".join(['?'] * len(fields)) + ")"
        query += " on conflict ([" + "],[".join(keys) + "]) do update set "
        query += ", ".join(("[" + f + "] = excluded.[" + f + "]" for f in fields))
        query += where

        return query + ';'

    @staticmethod
    def selectall(table: str) -> str:
        """ Builds a select query for input table. """
        return 'select * from ' + table + ';'

    @staticmethod
    def delete(table: str, fields: Sequence = ()) -> str:
        """ Builds a delete query for input table:
            Input:
                table [str]: for the from clause
                fields [List[str]]: used for the where condition

            Return:
                query [str]: query ready to be used in an execute
        """
        query = "delete from [" + str(table) + "]"
        if fields:
            query += " where " + " = ? and ".join(fields) + " = ?"

        return query + ';'

    @staticmethod
    def truncate(table: str) -> str:
        """ Builds a truncate query for input table:
            Input:
                table [str]: for the from clause

            Return:
                query [str]: query ready to be used in an execute
        """
        return "truncate table [" + str(table) + '];'

    @staticmethod
    def drop(table: str) -> str:
        """ Builds a drop query for input table:
            Input:
                table [str]: for the from clause

            Return:
                query [str]: query ready to be used in an execute
        """
        # PRAGMA foreign_keys=OFF;
        # PRAGMA foreign_keys = ON;
        return "drop table [" + str(table) + '];'

    @staticmethod
    def create(struct: Table) -> str:
        """ Builds a create query from a given table structure. """

        query = "create table [" + struct.name + "] ("

        # Build columns query
        cols = []
        pk = []
        for k, v in struct.columns.items():
            nn = 'NOT NULL' if v.notnull else ''
            cols.append(' '.join(map(str, ['[' + k + ']', v.type, nn])))
            if v.is_primary:
                pk.append(k)
        query += ', '.join(cols)

        # Build primary keys query
        if pk:
            query += ', primary key ([' + '], ['.join(pk) + '])'

        query += ") without rowid;"
        return query

    @staticmethod
    def add_column(table: str, col_name: str, col_prop: Sequence) -> str:
        """ Builds a add column query for the given table. """
        q = 'alter table ' + table + ' add ' + col_name + ' ' + ' '.join(col_prop)
        return q + ';'


def get_qb_glob() -> QueryBuilder:
    """ Returns the pointer to the global QueryBuilder """
    return QueryBuilder()
