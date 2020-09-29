#
# Rebuild Table Script
# Script to rebuild a table
#

from nfpy.DB.DB import get_db_glob, backup_db
from nfpy.Handlers.Inputs import InputHandler
from nfpy.Handlers.QueryBuilder import get_qb_glob

__version__ = '0.1'
_TITLE_ = "<<< Rebuild a table script >>>"

Q_CREATE = 'SELECT sql FROM sqlite_master where tbl_name = ?;'
Q_RENAME_TBL = 'alter table _TBL_ rename to _OLDTBL_;'


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    inh = InputHandler()

    # Select table and fetch structure
    table = inh.input("Which table you want to rebuild?: ", idesc='str')
    if not qb.exists_table(table):
        raise Exception('The table you provided does not exists')

    old_struct = qb.get_columns(table)

    print('The query used to generate the old table is:')
    create = db.execute(Q_CREATE, (table,)).fetchone()
    print(create[0], end='\n')

    # Ask for the changes in structure
    to_remove = inh.input("List columns to remove, comma separated (default: None): ",
                          idesc='str', optional=True, is_list=True)
    to_add = inh.input("List columns to add, comma separated (default: None): ",
                       idesc='str', optional=True, is_list=True)
    to_add_dict = {}
    if to_add:
        for c in to_add:
            p = inh.input("Insert column type for [{}], add optional 'NOT NULL' (comma separated): "
                          .format(c), idesc='str', is_list=True)
            to_add_dict[c] = p

    # Generate the new create query
    new_struct = qb.new_from_existing(table, to_add_dict, to_remove)
    q_create = qb.create(new_struct)

    print('The new create query is the following:')
    print(q_create, end='\n')
    proceed = inh.input("Do you want to proceed?: ", idesc='bool')
    if not proceed:
        exit()

    # Perform backup
    do_backup = inh.input("Do you want to backup the database?: ", idesc='bool')
    if do_backup:
        backup_db()

    if to_add_dict and not to_remove:
        # Add columns one by one
        for k, v in to_add_dict.items():
            q_add = qb.add_column(table, k, v)
            print('Adding column {}'.format(k))
            print(q_add)
            db.execute(q_add)
    else:
        # Copy table
        old_table = table + '_old'
        print('Renaming {} to {}'.format(table, old_table))
        q_rename = Q_RENAME_TBL.replace('_OLDTBL_', old_table)
        q_rename = q_rename.replace('_TBL_', table)
        db.execute(q_rename)

        # Create new table
        print('Creating the new table')
        db.execute(q_create)

        # Copy data in new table
        modified_struct = qb.new_from_existing(table, remove=to_remove)
        fields = list(modified_struct.get_fields())
        q_ins = qb.insert(table, ins_fields=fields, fields=fields, keys=(), table=old_table)
        print('Copying the data in the new table')
        # print(q_ins)
        db.execute(q_ins)

        # Drop old table
        do_drop = inh.input("Do you want to drop the old table?: ", idesc='bool')
        if do_drop:
            db.execute(qb.drop(old_table))

    print('All done!')
