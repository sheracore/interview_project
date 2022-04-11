from rest_framework.routers import SimpleRouter

from agents.views import AgentViewSet, UpdateFileViewSet


router = SimpleRouter()

router.register(r'agents', AgentViewSet)
router.register(r'updates', UpdateFileViewSet)
