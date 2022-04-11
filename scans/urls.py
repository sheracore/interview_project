from rest_framework.routers import SimpleRouter

from scans.views import SessionViewSet, FileViewSet, ScanViewSet


router = SimpleRouter()

router.register(r'sessions', SessionViewSet)
router.register(r'files', FileViewSet)
router.register(r'scans', ScanViewSet)

urlpatterns = router.urls
