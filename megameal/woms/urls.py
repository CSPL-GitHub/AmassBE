from django.urls import path
from . import views


urlpatterns = [
   # path('login/',views.getLoginauthkey), # Loging api for waiter
   path('login/',views.waiter_login),
   path('table/',views.showtabledetals), # show tables details
   path('assingwaiter/',views.assinTableupdate), # assign tables details
   path('onbording/',views.womsonbordingscreen), # onborading tables details
   path('getwaiter/', views.get_waiters),
   path('createTables/',views.createTables), # onborading tables detail 
   path('deleteTables/',views.deleteTables), # onborading tables detail 
   path('tableUpdate/',views.Table_update_api), # tableupdate  tables detail 
   path('search/<str:search>/',views.searchProduct), # show products 
   path('allCategory/',views.allCategory), # show products
   path('allCategory/<int:id>/',views.allCategory), # show products
   path('productByCategory/',views.productByCategory), # show products by category
   path('productByCategory/<int:id>/',views.productByCategory), # show products by category
   path('tableCapacity/<int:id>/',views.show_tableCapacity), # show products 
   path('createOrder/',views.createOrder), # show products 
   path('singleProdMod/<str:prod>/<int:order>/',views.singleProdMod), # show products modifiers
   path('switchOrderTables/',views.switchOrderTables)
]



