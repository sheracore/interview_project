import datetime
import json

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import translation

from core.mixins import SafeModelFieldMixin


class CICharField(models.CharField):

    def to_python(self, value):
        value = super().to_python(value)
        return value and value.lower() or None

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if value:
            setattr(model_instance, self.attname, value.lower())

        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return value and value.lower() or None


class SafeCharField(models.CharField, SafeModelFieldMixin):

    def pre_save(self, model_instance, add):
        return self._do_pre_save(model_instance, add)


class SafeTextField(models.TextField, SafeModelFieldMixin):

    def pre_save(self, model_instance, add):
        return self._do_pre_save(model_instance, add)


class JSONField(models.TextField):

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value

        try:
            return json.loads(value)

        except:
            return value

    def to_python(self, value):
        if isinstance(value, (dict, list)):
            return value

        if value == '' or value is None:
            return value

        try:
            return json.loads(value)

        except:
            return value

    def get_prep_value(self, value):
        if isinstance(value, set):
            value = list(value)

        if isinstance(value, (dict, list)):
            return json.dumps(value)

        return value

    def get_db_prep_save(self, value, connection):
        if isinstance(value, set):
            value = list(value)

        if isinstance(value, (dict, list)):
            value = json.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_db_prep_save(value, connection)
