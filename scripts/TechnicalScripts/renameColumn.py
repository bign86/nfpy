#
# Rename Column Script
# Script to rename a table's column
#

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Rename a table's column script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    tf = DB.TableFiddler()
    inh = IO.InputHandler()

    # Select table and fetch structure
    table_name = inh.input("Which table you want to alter?: ", idesc='str')
    if not qb.exists_table(table_name):
        raise ValueError('The table you provided does not exists')

    print(f'Current structure:\n{qb.get_structure_string(table_name)}',
          end='\n\n')

    # Get column to rename and perform consistency checks
    idx = inh.input('Give the index of the column to rename: ', idesc='int')
    old_fields = tuple(qb.get_fields(table_name))
    while (idx < 0) | (idx >= len(old_fields)):
        msg = '\tThe given index is out of the limits. Give another one: '
        idx = inh.input(msg, idesc='int')

    new_name = inh.input(f'Rename [{old_fields[idx]}] to: ')
    while new_name in old_fields:
        new_name = inh.input(f'Cannot use this name. Choose another one: ')

    # Create a the new table structure
    new_struct = tf.rename_column(
        qb.get_table(table_name),
        old_fields[idx],
        new_name
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
    fields = list(new_struct.get_fields())
    q_ins = qb.insert(table_name, ins_fields=fields, fields=old_fields,
                      keys=(), table=old_table_name)
    print(f'The query to copy the data is the following:\n{q_ins}\n'
          f'Copying the data in the new table')
    db.execute(q_ins)

    # Drop old table
    if inh.input("Drop the old table?: ", idesc='bool', default=False):
        db.execute(qb.drop(old_table_name))

    print('All done!')
