import uuid
from transliterate import translit
from django.utils.text import slugify

def translit_and_slugify(name):
    return slugify(translit(name, 'ru', reversed=True))

def get_app_label_for_user(user):
    return 'ul_%s' % user.pk

def get_db_table_name(user, name):
    return 'userlayer_%s_%s' % (user.pk, uuid.uuid1())

def normalize_field_name(name):
    new_name = translit_and_slugify(name)
    if new_name == 'id':
        new_name = 'id_'
    return new_name
