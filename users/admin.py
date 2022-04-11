from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


User = get_user_model()


class UserAdmin(BaseUserAdmin):
    readonly_fields = [
        'last_login',
        'date_joined',
        'created_at',
        'modified_at'
    ]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('full_name', 'email')}),
        ('Permissions', {'fields': (
            # 'is_deleted',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions'
        )}),
        ('Important dates', {'fields': (
            'last_login',
            'date_joined',
            'created_at',
            'modified_at'
        )}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
    list_display = (
        'username',
        'email',
        'full_name',
        'is_staff',
        # 'is_deleted',
    )
    list_filter = (
        # 'is_deleted',
        'is_active',
        'is_staff',
        'is_superuser',
        'groups',
    )
    search_fields = ('username', 'full_name', 'email')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)


admin.site.register(User, UserAdmin)
