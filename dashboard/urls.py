from django.urls import path
from . import views

app_name = 'dashboard'
urlpatterns = [path('', views.index, name='index'), path('customer/', views.customer, name='customer'), path('cart/', views.cart, name='cart'), path('staff/', views.staff, name='staff'), path('customers/', views.customers, name='customers')]
