from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet

router = DefaultRouter()
router.register(r'clients', DeviceViewSet, basename='client')

urlpatterns = [
    *router.urls,
]
