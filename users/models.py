from django.db import transaction
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin, Permission
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import RegexValidator
from django.core.mail import send_mail
from django.db import models
from django.db.models import BooleanField, CharField, EmailField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from core.fields import SafeCharField


class UserManager(BaseUserManager):
    """
    Operations on user objects are manged by this manager class.

    Redefines Django UserManager model because of User model redefining.
    """

    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """Create and save a user object.

        private helper method for create_user and
        create_superuser methods.
        """
        if not username:
            raise ValueError(_('The username not given.'))

        with transaction.atomic():
            if email:
                email = self.normalize_email(email)
            username = self.model.normalize_username(username)

            user = self.model(username=username, email=email, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)

            return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create a user.

        Args:
            username (str): username of this user
            email (str): email address of this user
            password (str): plain password of this user
            **extra_fields: other fields of this user (optional)

        Returns:
            user object
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None,
                         **extra_fields):
        """Create a superuser.

        Args:
            username (str): username of this user
            email (str): email address of this user
            password (str): plain password of this user
            **extra_fields: other fields of this user (optional)

        Returns:
            user object
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))

        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Users within the authentication system are represented by this
    model.

    Redefines Django User model to have complete access on User model
    and authentication system.
    Username and password are required. Other fields are optional.
    """

    phone_regex_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("Phone number must be entered in the format: '+999999999'. "
                  "Up to 15 digits allowed.")
    )

    username = CharField(
        'username',
        max_length=32,
        unique=True,
        help_text=_('Required. 32 characters or fewer. Letters, digits and '
                    '@/./+/-/_ only.'),
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    password = CharField('password', max_length=128)
    full_name = SafeCharField('full name', max_length=64, blank=True)
    email = EmailField('email address', max_length=128, unique=True, null=True)
    phone_number = CharField(max_length=17, blank=True,
                             validators=[phone_regex_validator])

    is_superuser = BooleanField(
        'superuser status', default=False,
        help_text=_('Designates that this user has all permissions without '
                    'explicitly assigning them.')
    )
    is_staff = BooleanField(
        'staff status', default=False,
        help_text=_('Designates whether the user can log into this '
                    'admin site.')
    )
    is_active = BooleanField(
        'active status', default=True,
        help_text=_('Designates whether this user should be treated '
                    'as active.')
    )
    # is_deleted = BooleanField('deletion status', default=False)

    last_login = models.DateTimeField('last login', blank=True, null=True)
    date_joined = models.DateTimeField('date joined', default=timezone.now)
    created_at = models.DateTimeField('created at', auto_now_add=True)
    modified_at = models.DateTimeField('modified at', auto_now=True)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        swappable = 'AUTH_USER_MODEL'
        permissions = [
            ('change_app_settings', 'Can change app settings'),
            ('view_sys_info', 'Can view system info'),
        ]

    @property
    def perms(self):
        cat1 = self.user_permissions.all().values_list('pk', flat=True)
        cat2 = self.groups.all().values_list('permissions__pk', flat=True)
        all = list(set(cat1) | set(cat2))
        return Permission.objects.filter(pk__in=all)

    def clean(self):
        """Normalize username and email attrs."""
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """Return the full_name."""
        full_name = str(self.full_name)
        return full_name.strip()

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user.

        Args:
            subject (str): subject of the email
            message (str): message
            from_email (str): sender email address

        Returns:
            None
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    # def create_reset_password_token(self, user_agent='', ip_address=None):
    #     password_reset_token_validation_time = \
    #         get_password_reset_token_expiry_time()
    #     now_minus_expiry_time = timezone.now() - timedelta(
    #         hours=password_reset_token_validation_time
    #     )
    #     clear_expired(now_minus_expiry_time)
    #
    #     users = User.objects.filter(
    #         **{'{}__iexact'.format(
    #             get_password_reset_lookup_field()): self.email}
    #     )
    #     active_user_found = False
    #
    #     for user in users:
    #         if user.eligible_for_reset():
    #             active_user_found = True
    #
    #     if not active_user_found and not getattr(
    #             settings,
    #             'DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE',
    #             False
    #     ):
    #         raise ValidationError({'email': [_("There is no active user "
    #                                            "associated with this e-mail "
    #                                            "address or the password can "
    #                                            "not be changed")]})
    #
    #     for user in users:
    #         if user.eligible_for_reset():
    #             token = None
    #
    #         if user.password_reset_tokens.all().count() > 0:
    #             token = user.password_reset_tokens.all()[0]
    #         else:
    #             token = ResetPasswordToken.objects.create(
    #                 user=user,
    #                 user_agent=user_agent,
    #                 ip_address=ip_address,
    #             )
    #         reset_password_token_created.send(sender=self.__class__,
    #                                           instance=self,
    #                                           reset_password_token=token)
    #         return token
    #
    #     else:
    #         raise ValidationError({'email': [_("There is no active user "
    #                                            "associated with this e-mail "
    #                                            "address or the password can "
    #                                            "not be changed")]})
