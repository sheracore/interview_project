from rest_framework.routers import SimpleRouter

from core.views import SystemViewSet, APIViewSet, TaskViewSet, \
    MimeTypeCatViewSet, MimeTypeViewSet, VideoViewSet, AuditLogViewSet

router = SimpleRouter()

router.register(r'system', SystemViewSet, basename='system')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'auditlogs', AuditLogViewSet)
router.register(r'apis', APIViewSet)
router.register(r'mimetypecats', MimeTypeCatViewSet)
router.register(r'mimetypes', MimeTypeViewSet)
router.register(r'videos', VideoViewSet)
