from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from core.fields import SafeCharField, SafeTextField
from core.models import DateMixin, UpdateModelMixin

User = get_user_model()


class Period(DateMixin, UpdateModelMixin):
    name = SafeCharField(max_length=100)
    days = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        verbose_name = _('Period')
        verbose_name_plural = _('Periods')

    def __str__(self):
        return self.name


class Plan(DateMixin, UpdateModelMixin):
    name = SafeCharField(max_length=128, null=True)
    description = SafeTextField(blank=True)
    period = models.ForeignKey(Period, on_delete=models.PROTECT)
    scan_count = models.PositiveIntegerField(null=True)
    volume = models.PositiveIntegerField(null=True)
    price = models.PositiveIntegerField()
    rebate = models.IntegerField(default=0)
    available_from = models.DateField()
    available_to = models.DateField(null=True)

    class Meta:
        verbose_name = _('Plan')
        verbose_name_plural = _('Plans')

    def __str__(self):
        return self.name

    @property
    def current_copy(self):
        return self.copies.order_by('pk').last()

    @property
    def is_free(self):
        return self.price == 0

    @property
    def available(self):
        if not self.available_to:
            return True

        return \
            self.available_from <= timezone.now().date() <= self.available_to


class PlanCopy(DateMixin):
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL,
                             related_name='copies', null=True)
    name = SafeCharField(max_length=128, null=True)
    description = SafeTextField(blank=True)
    period_name = SafeCharField(max_length=100)
    period_days = models.PositiveSmallIntegerField()
    scan_count = models.PositiveIntegerField(null=True)
    volume = models.PositiveIntegerField(null=True)
    price = models.PositiveIntegerField()
    rebate = models.IntegerField(default=0)

    class Meta:
        verbose_name = _('Plan Copy')
        verbose_name_plural = _('Plan Copies')
        default_permissions = []


@receiver(post_save, sender=Plan)
def copy_plan(sender, instance, **kwargs):
    PlanCopy.objects.create(
        plan=instance,
        name=instance.name,
        description=instance.description,
        period_name=instance.period.name,
        period_days=instance.period.days,
        scan_count=instance.scan_count,
        volume=instance.volume,
        price=instance.price,
        rebate=instance.rebat
    )


class UserPlan(DateMixin, UpdateModelMixin):
    user = models.OneToOneField(User, related_name='plan', on_delete=models.CASCADE)
    plan = models.ForeignKey(PlanCopy, on_delete=models.PROTECT,
                             related_name='users', editable=False)
    expiry = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.user.username} - {self.plan.name}'
