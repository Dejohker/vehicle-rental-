from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [path('', views.payment_list, name='list'), path('record/', views.payment_create, name='create'), path('<int:pk>/', views.payment_detail, name='detail')]
