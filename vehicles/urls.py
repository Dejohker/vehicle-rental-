from django.urls import path
from . import views

app_name = 'vehicles'
urlpatterns = [
    path('', views.vehicle_list, name='list'),
    path('showcase/', views.showcase, name='showcase'),
    path('saved/', views.saved_vehicles, name='saved'),
    path('manage/', views.manage, name='manage'),
    path('add/', views.vehicle_edit, name='add'),
    path('<int:pk>/edit/', views.vehicle_edit, name='edit'),
    path('<int:pk>/deactivate/', views.vehicle_deactivate, name='deactivate'),
    path('<int:pk>/save/', views.save_vehicle, name='save'),
    path('<int:pk>/cart/', views.add_to_cart, name='add_to_cart'),
    path('<int:pk>/unsave/', views.unsave_vehicle, name='unsave'),
    path('<int:pk>/', views.vehicle_detail, name='detail'),
]
