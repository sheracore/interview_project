from django.db import transaction
from django.utils.html import strip_tags

from core.utils import asyncing


class AsyncMixin:
    @staticmethod
    def perform_async(signature, countdown=0, on_commit=True, **kwargs):
        if on_commit:
            transaction.on_commit(
                lambda: asyncing.perform_async(signature, countdown, **kwargs)
            )

        else:
            return asyncing.perform_async(signature, countdown, **kwargs)


class SafeModelFieldMixin(object):

    def _do_pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if value:
            value = strip_tags(value)

        return value
