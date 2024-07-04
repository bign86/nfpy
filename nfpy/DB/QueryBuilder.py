#
# Query builder for DB
#

from collections import OrderedDict
from operator import itemgetter
from typing import (Any, Generator, KeysView, Optional, Sequence, Union)

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
        res = self._db.execute(f"PRAGMA TABLE_INFO([{table}]);").fetchall()
        if not res:
            raise Ex.MissingData(f'Table {table} not found in the database')

        l = []
        res = sorted(res, key=itemgetter(0))
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

    def get_table(self, table: str) -> Table:
        """ Return the Table object from the dictionary having the right name. """
        try:
            t = self._tables[table]
        except KeyError:
            t = self._fetch_table_info(table)
        return t

    def _add_table(self, table: Table) -> None:
        """ Add the Table object to the dictionary. """
        assert isinstance(table, Table)
        self._tables[table.name] = table

    def get_structure_string(self, table: str) -> str:
        """ Return a string representing the structure of the table. """
        return self.get_table(table).structure

    def exists_table(self, table: str) -> bool:
        """ Return True or False whether the input table exists. """
        q = f"SELECT [name] FROM [sqlite_master] " \
            f"WHERE [type] = 'table' AND [name] = '{table}';"
        res = self._db.execute(q).fetchall()
        return False if not res else True

    def get_tables_list(self) -> Generator[Any, Any, None]:
        """ List all the tables in the database. """
        q = """SELECT [name] FROM [sqlite_master] WHERE [type] IN ('table','view')
               AND [name] NOT LIKE 'sqlite_%' ORDER BY 1;"""
        res = self._db.execute(q).fetchall()
        return (t[0] for t in res)

    def get_columns(self, table: str) -> OrderedDict:
        """ Return the table's dictionary of column objects. """
        return self.get_table(table).columns

    def get_fields(self, table: str) -> KeysView:
        """ Return the generator of fields in table. """
        return self.get_table(table).get_fields()

    def get_keys(self, table: str) -> Generator[Any, Any, None]:
        """ Return the generator of primary keys. """
        return self.get_table(table).get_keys()

    def is_primary(self, table: str, field: str) -> bool:
        """ Return True if field is a primary key """
        return self.get_table(table).is_primary(field)

    def get_create_query(self, table: str) -> str:
        """ Return the create query relative to the table in input. """
        q_create = 'SELECT [sql] FROM [sqlite_master] WHERE [tbl_name] = ?;'
        return self._db.execute(q_create, (table,)).fetchone()[0]

    @staticmethod
    def get_rename_table(table: str) -> str:
        """ Return the alter table query to rename a table. """
        return f"ALTER TABLE [{table}] RENAME TO {table + '_old'};"

    def insert(self, ins_table: str, ins_fields: Sequence[str] = (),
               **kwargs) -> str:
        """ Builds an insert query for input table:
            Input:
                ins_table [str]: for the <FROM> clause
                ins_fields [[str]]: list of fields to insert
                kwargs [Any]: arguments for a 'select' query

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        return self._get_insert(ins_table, ins_fields, 'insert', **kwargs)

    def select(
            self,
            table: str,
            fields: Optional[Union[KeysView, Sequence[str]]] = None,
            rolling: Sequence[str] = (),
            keys: Optional[Sequence[str]] = None,
            partial_keys: Sequence[str] = (), where: str = "",
            order: Optional[str] = None,
            distinct: bool = False
    ) -> str:
        """ Builds a select query for input table:

            Input:
                table [str]: for the from clause
                fields [[str]]]: if present select only these columns
                rolling [[str]]: if present remove these from the list of
                    keys used for the where condition
                keys [[str]]: if present use only these keys to create the
                    where condition, if given empty no keys will be used. If
                    None is given use ALL primary keys to build the query
                partial_keys [[str]]: additional keys to be evaluated by a
                    'like' clause. If none are given, none are used
                where [str]: additional where condition
                order [str]: additional order condition
                distinct [bool]: add DISTINCT

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        t = self.get_table(table)

        if not fields:
            fields = t.get_fields()

        query = "SELECT DISTINCT " if distinct else "SELECT "
        query += f"t.[{'], t.['.join(fields)}] FROM [{table}] AS t"

        # where on keys
        if keys is None:
            if not partial_keys:
                keys = (k for k in t.get_keys() if k not in rolling)
            else:
                keys = ()
        qk = [f"t.[{k}] = ? " for k in keys]

        # like conditions
        qk += [f"t.[{k}] LIKE ? " for k in partial_keys]

        # where on rolling
        for r in rolling:
            qk += [f"t.[{r}] >= ? ", f"t.[{r}] <= ? "]

        # handle the external where
        if len(where) > 0:
            qk.append(where)

        # build the complete where statement
        q_where = f"{' AND '.join(map(str, qk))}"
        if len(q_where) > 0:
            query += f" WHERE {q_where}"

        # add ordering
        if order:
            query += f" ORDER BY {order}"

        return query + ';'

    def merge(self, ins_table: str, ins_fields: Sequence[str] = (),
              **kwargs) -> str:
        """ Builds an insert or replace query for input table:
            Input:
                ins_table [str]: for the <FROM> clause
                ins_fields [[str]]: list of fields to insert
                kwargs [Any]: arguments for a 'select' query

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        return self._get_insert(
            ins_table,
            ins_fields,
            'INSERT OR REPLACE',
            **kwargs
        )

    def _get_insert(self, ins_table: str, ins_fields: Sequence[str],
                    command: str, **kwargs) -> str:
        """ Creates an insert like query. """
        keys = self.get_keys(ins_table)
        if not ins_fields:
            ins_fields = self.get_fields(ins_table)

        miss_keys = set(keys) - set(ins_fields)
        if miss_keys:
            msg = f"Missing the following keys in the insert list " \
                  f"{','.join(map(str, miss_keys))}"
            raise ValueError(msg)

        query = f"{command} INTO [{str(ins_table)}]" \
                f"([{'],['.join(ins_fields)}])"

        if not kwargs:
            query += f" VALUES ({','.join(['?'] * len(ins_fields))});"
        else:
            query += self.select(**kwargs)

        return query

    def update(self, table: str, fields: Sequence[str] = (),
               keys: Sequence[str] = (), where: str = "") -> str:
        """ Builds an insert query the for input table. The where condition is
            applied by default on the primary key of the table:
            
            Input:
                table [str]: for the <FROM> clause
                fields [Sequence[str]]: list of fields to update
                keys [Sequence[str]]: if present use only these keys to create
                    the where condition, if given empty no keys will be used.
                    If None is given use ALL primary keys to build the query
                where [str]: additional where condition

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        # FIXME: add check on keys for safety
        if not keys:
            keys = self.get_keys(table)

        if not fields:
            fields = self.get_fields(table)

        query = f"UPDATE [{str(table)}] set [{'] = ?, ['.join(fields)}] = ?" \
                f" WHERE [{'] = ? AND ['.join(keys)}] = ?"
        if where:
            query += f" AND {where}"

        return query + ';'

    def upsert(self, table: str, fields: Optional[Sequence[str]] = None,
               where: str = "") -> str:
        """ Builds an upsert query for the input table. The where condition is
            applied by default on the primary key of the table:

            Input:
                table [str]: for the <FROM> clause
                fields [Sequence[str]]: list of fields to update
                where [str]: additional where condition

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        keys = self.get_keys(table)
        if not fields:
            fields = self.get_fields(table)

        query = f"INSERT INTO [{str(table)}] ([{'],['.join(fields)}]) " \
                f"VALUES ({','.join(['?'] * len(fields))}) " \
                f"ON CONFLICT ([{'],['.join(keys)}]) DO UPDATE SET " \
                f"{', '.join((f'[{f}] = excluded.[{f}]' for f in fields))}"
        if where:
            query += f" WHERE {where}"

        return query + ';'

    @staticmethod
    def selectall(table: str, fields: Optional[Sequence[str]] = None) -> str:
        """ Builds a select query for input table. """
        f_str = '*'
        if fields:
            f_str = f"[{'],['.join(fields)}]"

        return f'SELECT {f_str} FROM [{table}];'

    @staticmethod
    def delete(table: str, fields: Optional[Sequence[str]] = None) -> str:
        """ Builds a 'delete' query for input table:
            Input:
                table [str]: for the <FROM> clause
                fields [Sequence[str]]: used for the where condition

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        query = f"DELETE FROM [{str(table)}]"
        if fields:
            query += f" WHERE [{'] = ? AND ['.join(fields)}] = ?"

        return query + ';'

    @staticmethod
    def truncate(table: str) -> str:
        """ Builds a truncate query for input table:
            Input:
                table [str]: for the <FROM> clause

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        return f"TRUNCATE TABLE [{str(table)}];"

    @staticmethod
    def drop(table: str) -> str:
        """ Builds a drop query for input table:
            Input:
                table [str]: for the <FROM> clause

            Return:
                query [str]: query ready to be used in an 'execute'
        """
        # PRAGMA foreign_keys=OFF;
        # PRAGMA foreign_keys = ON;
        return f"DROP TABLE [{str(table)}];"

    @staticmethod
    def create(struct: Table) -> str:
        """ Builds a create query from a given table structure. """

        query = f"CREATE TABLE [{struct.name}] ("

        # Build columns query
        cols = []
        pk = []
        for k, v in struct.columns.items():
            nn = 'NOT NULL' if v.notnull else ''
            cols.append(' '.join(map(str, [f'[{k}]', v.type, nn])))
            if v.is_primary:
                pk.append(k)
        query += ', '.join(cols)

        # Build primary keys query
        if pk:
            query += f", PRIMARY KEY ([{'], ['.join(pk)}])"

        query += ") WITHOUT ROWID;"
        return query

    @staticmethod
    def add_column(table: str, col_name: str,
                   col_prop: Optional[Sequence[str]]) -> str:
        """ Builds an add column query for the given table. """
        return f"ALTER TABLE [{table}] ADD [{col_name}] {' '.join(col_prop)};"


def get_qb_glob() -> QueryBuilder:
    """ Returns the pointer to the global QueryBuilder """
    return QueryBuilder()
