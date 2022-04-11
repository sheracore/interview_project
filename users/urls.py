from django.urls import path
from django.conf import settings
from rest_framework.routers import SimpleRouter
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView, TokenVerifyView)

from core.permissions import CaptchaRequired
from users.views import (UserViewSet, PermissionViewSet, GroupViewSet)
from .serializers import CustomTokenObtainPairSerializer, CustomTokenRefreshSerializer


router = SimpleRouter()

router.register(r'users', UserViewSet)
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'groups', GroupViewSet)

permission_classes = [AllowAny] if settings.DEBUG else [CaptchaRequired]

urlpatterns = [
    path('jwt/create/',
         TokenObtainPairView.as_view(
             permission_classes=permission_classes,
             serializer_class=CustomTokenObtainPairSerializer, )
         ,
         name='token_obtain'),
    path('jwt/refresh/', TokenRefreshView.as_view(serializer_class=CustomTokenRefreshSerializer), name='token_refresh'),
    path('jwt/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
