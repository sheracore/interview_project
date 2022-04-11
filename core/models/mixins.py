from django.db import models, transaction


class UpdateModelMixin:

    def update(self, commit=True, update_fields=None, **values):
        if not commit:
            if set(values.keys()) & \
                    set([m2m.name for m2m in self._meta.many_to_many]):
                raise AssertionError('Cannot pass m2m arguments when '
                                     'commit is False.')

        m2m_fields = []
        for field, value in values.items():
            field_obj = self._meta.get_field(field)
            if isinstance(field_obj, models.ManyToManyField):
                m2m_fields.append(field)

            else:
                setattr(self, field, value)

        if commit:
            with transaction.atomic():
                self.save(update_fields=update_fields)

                for field in m2m_fields:
                    m2m_field = getattr(self, field)
                    m2m_value = values[field]
                    m2m_field.set(m2m_value, clear=True)


class DateMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
