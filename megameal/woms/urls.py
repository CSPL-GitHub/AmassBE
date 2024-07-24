from django.urls import path
from . import views



urlpatterns = [
   path('login/', views.waiter_login),
   path('tables/', views.get_tables),
   path('get_waiters/', views.get_waiters),
   path('assign_waiter/', views.assign_waiter_to_table),
   path('update_table_status/', views.update_table_status),
   path('singleProdMod/<str:prod>/<int:order>/', views.singleProdMod),
]
