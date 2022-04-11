import importlib

from rest_framework.routers import DefaultRouter


class ExtendableDefaultRouter(DefaultRouter):
    """
    Extends `DefaultRouter` class to add a method for extending url
    routes from another router.
    """

    def extend(self, router_path):
        """
        Extend the routes with url routes of the passed in router.

        Args:
             router_path: SimpleRouter instance's path containing
                          route definitions.
        """
        split_router_path = router_path.split('.')
        urls_path = '.'.join(split_router_path[:-1])
        router_object_name = split_router_path[-1]
        urls = importlib.import_module(urls_path)
        router = getattr(urls, router_object_name)
        self.registry.extend(router.registry)
