def get_app_label_for_user(user):
    return 'ul_%s' % user.pk

def get_db_table_name(user, name):
    return '%s_%s' % (get_app_label_for_user(user), name)
