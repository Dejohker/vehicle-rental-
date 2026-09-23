from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'
urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.CustomerLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html', success_url='/accounts/profile/'), name='password_change'),
]
