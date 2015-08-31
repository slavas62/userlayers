# coding: utf-8

###############################################################################
# CONFIG EXAMPLE
###############################################################################
# {
#     "fragment_rkt": {
#         "owner_id": 1,
#         "verbose_name": "verbose name",
#         "verbose_name_plural": "verbose name plural",
#         "fields": {
#             "name": {
#                 "type": "varchar",
#                 "args": {
#                     "max_length": 500,
#                     "null": false,
#                     "blank": false,
#                     "verbose_name": "name ahaha"
#                 }
#             }
#         }
#     },
#     "fragment_rkt_again": {
#         "owner_id": 1,
#         "verbose_name": "verbose name again",
#         "verbose_name_plural": "verbose name plural again",
#         "fields": {
#             "track": {
#                 "type": "line_string",
#                 "args": {
#                     "srid": 4326,
#                     "null": false,
#                     "blank": false,
#                     "geography": true,
#                     "verbose_name": "track name"
#                 }
#             }
#         }
#     },
# }
###############################################################################

import json
import logging
from collections import OrderedDict
from django.core.management.base import BaseCommand
from userlayers.models import ModelDefinition
from userlayers.api.forms import FIELD_TYPES

logger = logging.getLogger('console_no_level')


class Command(BaseCommand):
    args = '<path_to_cfg_file>'

    def handle(self, *args, **options):
        try:
            with open(args[0], 'r') as f:
                config = json.load(f, object_pairs_hook=OrderedDict)
                f.close()
        except (IndexError, IOError) as e:
            logger.critical(u'Bad json config file "%s"' % (args[0] if args else ''))
            exit()
        field_types = dict(FIELD_TYPES)
        md_count = len(config)
        for i, (md_name, md_data) in enumerate(config.items()):
            try:
                md = ModelDefinition.objects.get_by_name(md_name)
                md_created = False
            except ModelDefinition.DoesNotExist:
                md = ModelDefinition(name=md_name)
                md_created = True
            for required, flist in {
                True: ['owner_id'],
                False: ['verbose_name', 'verbose_name_plural']
            }.items():
                for f in flist:
                    if f in md_data:
                        setattr(md, f, md_data[f])
                    elif required:
                        logger.error(u'Field "%s.%s" is required' % (md_name, f))
                        exit()
            md.save()
            logger.info('%s/%s %s (%s) [%s]' % (i + 1, md_count, md_name, md.db_table, 'C' if md_created else 'U'))
            f_count = len(md_data['fields'])
            for j, (f_name, f_data) in enumerate(md_data.get('fields', {}).items()):
                if 'type' not in f_data or f_data['type'] not in field_types:
                    logger.error(u'Not valid field type "%s" for "%s"…"%s"' % (
                        f_data['type'] if 'type' in f_data else '', md_name, f_name))
                    exit()
                f_class = field_types[f_data['type']]
                try:
                    f = f_class.objects.get(model_def_id=md.pk, name=f_name)
                    f_created = False
                except f_class.DoesNotExist:
                    f = f_class(model_def_id=md.pk, name=f_name)
                    f_created = True
                for k, v in f_data.get('args', {}).items():
                    setattr(f, k, v)
                f.save()
                logger.info(
                    '\t%s/%s %s (%s) [%s]' % (j + 1, f_count, f_name, f_data['type'], 'C' if f_created else 'U'))
