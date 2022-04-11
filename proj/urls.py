"""proj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings

from core.routers import ExtendableDefaultRouter
from proj.swagger import schema_view


default_router = ExtendableDefaultRouter()

default_router.extend('users.urls.router')
default_router.extend('core.urls.router')

if settings.I_CAN_MANAGE_KIOSKS:
    default_router.extend('kiosks.urls.router')
else:
    default_router.extend('scans.urls.router')
    default_router.extend('agents.urls.router')


urlpatterns = i18n_patterns(
    # Admin route
    path('admin/', admin.site.urls),

    # Rosetta routes
    path('rosetta/', include('rosetta.urls')),

    # Captcha routes
    path('api/v1/captcha/', include('rest_captcha.urls')),

    # DefaultRouter's routes
    path('api/v1/', include(default_router.urls)),

    # Other applications' routes
    path('api/v1/', include('users.urls')),
    # path('api/v1/', include('scans.urls')),

)

if settings.DEBUG:
    urlpatterns += i18n_patterns(
        # Swagger routes
        re_path(r'^swagger(?P<format>\.json|\.yaml)$',
                schema_view.without_ui(cache_timeout=0),
                name='schema-json'),
        path('swagger/',
             schema_view.with_ui('swagger', cache_timeout=0),
             name='schema-swagger-ui'),
        path('redoc/',
             schema_view.with_ui('redoc', cache_timeout=0),
             name='schema-redoc'),
    )
