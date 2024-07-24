from django.urls import path
from . import views


urlpatterns = [
   path('login/', views.waiter_login),
   path('tables/', views.get_tables),
   path('get_waiters/', views.get_waiters),
   path('assign_waiter/', views.assign_waiter_to_table),
   path('update_table_status/', views.update_table_status),
   path('table/', views.showtabledetals), # show tables details
   path('onbording/', views.womsonbordingscreen), # onborading tables details
   path('createTables/', views.createTables), # onborading tables detail 
   path('deleteTables/', views.deleteTables), # onborading tables detail 
   path('search/<str:search>/', views.searchProduct), # show products 
   path('allCategory/', views.allCategory), # show products
   path('allCategory/<int:id>/', views.allCategory), # show products
   path('productByCategory/', views.productByCategory), # show products by category
   path('productByCategory/<int:id>/', views.productByCategory), # show products by category
   path('createOrder/', views.createOrder), # show products 
   path('singleProdMod/<str:prod>/<int:order>/', views.singleProdMod), # show products modifiers
   path('switchOrderTables/', views.switchOrderTables)
]



