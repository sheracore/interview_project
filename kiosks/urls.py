from rest_framework.routers import SimpleRouter

from kiosks.views import KioskViewSet, ScanLogViewSet, KioskAuditLogViewSet


router = SimpleRouter()

router.register(r'kiosks', KioskViewSet)
router.register(r'kiosksscanlogs', ScanLogViewSet)
router.register(r'kiosksauditlogs', KioskAuditLogViewSet)
