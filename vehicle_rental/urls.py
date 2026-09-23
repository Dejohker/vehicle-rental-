"""
URL configuration for vehicle_rental project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from accounts import views as account_views
from accounts.forms import StaffAuthenticationForm

admin.site.login_template = 'accounts/admin_login.html'
admin.site.login_form = StaffAuthenticationForm
admin.site.site_header = 'RideFlow administration'
admin.site.site_title = 'RideFlow Admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('vehicles/', include('vehicles.urls')),
    path('bookings/', include('bookings.urls')),
    path('payments/', include('payments.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('media/licenses/<path:filename>', account_views.license_image, name='license_image'),
]

# Only public image folders are served directly; licenses require authorization.
urlpatterns += static(f'{settings.MEDIA_URL}vehicles/', document_root=settings.MEDIA_ROOT / 'vehicles')
urlpatterns += static(f'{settings.MEDIA_URL}profiles/', document_root=settings.MEDIA_ROOT / 'profiles')

handler403 = 'core.views.permission_denied'
handler404 = 'core.views.page_not_found'
handler500 = 'core.views.server_error'
