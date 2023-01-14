#
# Reorder Table Columns Script
# Script to rebuild the table's columns order
#

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Reorder the table's columns script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    tf = DB.TableFiddler()
    inh = IO.InputHandler()

    # Select table and fetch structure
    table_name = inh.input("Which table you want to reorder?: ", idesc='str')
    if not qb.exists_table(table_name):
        raise ValueError('The table you provided does not exists')

    print(f'Current structure:\n{qb.get_structure_string(table_name)}',
        end='\n\n')

    # Get new order
    order = inh.input("Insert new order of the columns (empty for no action): ",
                      idesc='int', optional=True, is_list=True)
    if order is None:
        print('Leaving the table alone...')
        exit()

    # Generate new create query
    new_struct = tf.reorder_columns(
        qb.get_table(table_name),
        order
    )
    q_create = qb.create(new_struct)
    print(f'The new create query is the following:\n{q_create}')

    # Confirmations and perform backup
    if not inh.input("Do you want to proceed?: ", idesc='bool', default=False):
        exit()

    if inh.input("Do you want to backup the database?: ",
                 idesc='bool', default=True):
        DB.backup_db()

    # Copy table
    old_table_name = table_name + '_old'
    print(f'Renaming {table_name} to {old_table_name}')
    db.execute(qb.get_rename_table(table_name))

    # Create new table
    print('Creating the new table')
    db.execute(q_create)

    # Generate the query to copy data in new table
    fields = tuple(new_struct.get_fields())
    q_ins = qb.insert(table_name, ins_fields=fields, fields=fields,
                      keys=(), table=old_table_name)
    # print('The query to copy the data is the following:\n{}'.format(q_ins))
    print('Copying the data in the new table')
    db.execute(q_ins)

    # Drop old table
    if inh.input("Drop the old table?: ", idesc='bool', default=False):
        db.execute(qb.drop(old_table_name))

    print('All done!')
