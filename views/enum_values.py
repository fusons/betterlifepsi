# coding=utf-8
from flask.ext.babelex import lazy_gettext
from views import ModelViewWithAccess

class EnumValuesAdmin(ModelViewWithAccess):
    column_list = ('id', 'type', 'code', 'display',)

    column_editable_list = ['display']
    column_searchable_list = ['code', 'display']
    # column_filters = ('code', 'display',)
    column_labels = {
        'id': lazy_gettext('id'),
        'type': lazy_gettext('Type'),
        'code': lazy_gettext('Code'),
        'display': lazy_gettext('Display'),
    }