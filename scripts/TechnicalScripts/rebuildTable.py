#
# Rebuild Table
# Script to rebuild a table by adding or removing columns
#

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< Rebuild a table script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    tf = DB.TableFiddler()
    inh = IO.InputHandler()

    # Select table and fetch structure
    table_name = inh.input("Which table do you want to rebuild?: ", idesc='table')
    print(f'Current structure:\n{qb.get_structure_string(table_name)}',
          end='\n\n')

    # Ask for the changes in structure
    to_remove = inh.input("List columns to remove by name, comma separated (default: None): ",
                          idesc='str', optional=True, is_list=True, default=[])
    to_add = inh.input("List columns to add by name, comma separated (default: None): ",
                       idesc='str', optional=True, is_list=True, default=[])

    for i in range(len(to_add)):
        col = to_add[i]
        msg = f"> Column [{col}]:\ninsert column type followed by optional " \
              f"attributes such as 'NOT NULL' (comma separated): "
        p = inh.input(msg, idesc='str', is_list=True)
        to_add[i] = (col, p)

    # Quick exit for no changes
    if (not to_add) & (not to_remove):
        print('No changes')
        exit()

    # Perform backup
    if inh.input(
            "Do you want to backup the database? (default True): ",
            idesc='bool', default=True
    ):
        DB.backup_db()

    # If there are only additions it is better to add the columns to the
    # existing table instead of creating a new one
    if to_add and (not to_remove):
        # Add columns one by one
        for v in to_add:
            q_add = qb.add_column(table_name, *v)
            print(f'> Adding column {v[0]}\n\t{q_add}')
            db.execute(q_add)
    else:
        # Generate the new create query
        table_struct = qb.get_table(table_name)
        tf.add_columns(table_struct, to_add, inplace=True)
        tf.remove_columns(table_struct, to_remove, inplace=True)
        q_create = qb.create(table_struct)
        # print(q_create)

        # Copy table
        old_table_name = table_name + '_old'
        print(f'Renaming {table_name} to {old_table_name}')
        db.execute(qb.get_rename_table(table_name))

        # Create new table
        print('Creating the new table')
        db.execute(q_create)

        # Copy data in new table
        fields = list(table_struct.get_fields())
        q_ins = qb.insert(table_name, ins_fields=fields, fields=fields,
                          keys=(), table=old_table_name)
        print('Copying the data in the new table')
        db.execute(q_ins)

        # Drop old table
        if inh.input(
                "Drop the old table?: (default False) ",
                idesc='bool', default=False
        ):
            db.execute(qb.drop(old_table_name))

    print('All done!')
