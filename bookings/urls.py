from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
    path('', views.booking_list, name='list'),
    path('manage/', views.manage, name='manage'),
    path('create/<int:vehicle_id>/', views.booking_create, name='create'),
    path('<str:reference>/success/', views.booking_success, name='success'),
    path('<str:reference>/cancel/', views.booking_cancel, name='cancel'),
    path('<str:reference>/manage/', views.manage_detail, name='manage_detail'),
    path('<str:reference>/return/', views.process_return, name='return'),
    path('<str:reference>/', views.booking_detail, name='detail'),
]
