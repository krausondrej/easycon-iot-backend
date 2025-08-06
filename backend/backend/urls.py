"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth import views as auth_views
from api.views import get_data, logout_view


urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('api/data/', get_data),
    path('api/', include('api.urls')),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('accounts/logout/', logout_view, name='logout'),
    path('accounts/login/', auth_views.LoginView.as_view( template_name='login.html', redirect_authenticated_user=True), name='login'),

]
