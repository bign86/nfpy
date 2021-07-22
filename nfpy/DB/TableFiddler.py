#
# Table fiddler
# Convenience functions to alter tables
#

from copy import deepcopy
from typing import Sequence

from .Table import (Table, Column)


class TableFiddler(object):
    """ Class to store and alter the structure of the database tables. """

    @staticmethod
    def add_columns(table: Table, cols: Sequence = (),
                    inplace: bool = True) -> Table:
        """ Modifies a Table object by adding selected columns.

            Input:
                table [Table]: table to be altered
                cols [Sequence]: sequence of columns w/ properties to add
                inplace [bool]: in place modify the Table object (default: True)

            Output:
                t [Table]: modified table object

            Bugs & Limitations:
                It is not possible to add a column with primary key enabled.
        """
        # Not in place
        if not inplace:
            table = deepcopy(table)

        # Add columns
        i = table.__len__()
        for v in cols:
            c = Column(v[0])
            c.ordinal = i
            c.type = v[1]
            c.notnull = True if 'NOT NULL' in v else False
            c.is_primary = True if 'PRIMARY' in v else False
            table.add_field(c)
            i = i + 1

        return table

    @staticmethod
    def remove_columns(table: Table, cols: Sequence = (),
                       inplace: bool = True) -> Table:
        """ Modifies a Table object by adding/removing selected columns.

            Input:
                table [Table]: table to be altered
                cols [Sequence]: sequence of columns to remove
                inplace [bool]: in place modify the Table object (default: True)

            Output:
                t [Table]: modified table object
        """
        # Not in place
        if not inplace:
            table = deepcopy(table)

        # Remove columns
        for c in cols:
            table.remove_field(c)

        return table

    @staticmethod
    def reorder_columns(table: Table, order: Sequence) -> Table:
        """ Reorder the columns of a table.

            Input:
                table [Table]: table to reorder
                order [Sequence]: new ordering

            Output:
                new_table [Table]: new table object

            Exceptions:
                ValueError: duplicated values in ordering list
                ValueError: wrong length of ordering elements

            Bug & Limitations:
                This is a slow operation as the dictionary of columns must be
                recreated and no in place change is possible.
        """
        # Perform consistency checks on the new ordering
        old_cols = table.columns
        len_new = len(order)
        if len_new != len(set(order)):
            raise ValueError('There are duplicates in your ordering list')
        elif len_new != old_cols.__len__():
            raise ValueError('Wrong number of ordering elements supplied')

        # Rebuild the table
        names = tuple(old_cols.keys())
        new_table = Table(table.name)
        new_table.set_fields(tuple(old_cols[names[i]] for i in order))

        return new_table

    @staticmethod
    def rename_column(table: Table, old_name: str, new_name: str) -> Table:
        """ Rename the <old_name> column to <new_name> and return the table.

            Input:
                table [Table]: table to alter
                old_name [str]: column to rename
                new_name [str]: new name of the column

            Output:
                new_table [Table]: new table object

            Bug & Limitations:
                This operation is done by adding the new column, removing the
                old and restoring the ordering. Therefore, this is an operation
                that cannot be done fully in place.
        """
        column = table.columns[old_name]
        column.field = new_name

        table.add_field(column)
        TableFiddler.remove_columns(table, (old_name,), inplace=True)

        order = list(range(table.__len__()))
        order.insert(column.ordinal, order.pop())

        return TableFiddler.reorder_columns(table, order)
