from django.urls import path
from koms import views
from django.urls import path



urlpatterns = [
    path('OrderList/', views.orderList, name='orderPoints'),
    path('TestingViewSet/', views.TestingViewSet, name="TestingViewSet"),
    path('station/', views.StationsView.as_view()),
    path('stations/', views.StationsDetailView.as_view()),
    path('staff', views.StaffView.as_view()),
    path('staff/<int:staffId>/', views.StaffDetailView.as_view()),
    path('stationWiseStaff/<int:stationId>/', views.StationsStaffView.as_view()),
    path('userSettings/<int:stationId>/', views.UserSettingsView.as_view()),
    path('stationOrder/', views.stationOrder, name='stationOrder'),
    path('orderStatus/', views.orderCount, name='orderStatus'),
    path('orderSearch/', views.ticketSearch, name='orderSearch'),
    path('saveOrder/', views.saveOrder, name='saveOrder'), #not using now but keep for feature reference 
    path('updateOrderStatus/', views.updateTicketStatus, name='updateOrderStatus'),
    path('assignChef/', views.assignChef, name='assignChef'),
    path('total_order_history_bydate/<str:start>/<str:end>', views.total_order_history_bydate),
    path('total_order_history_by_stations_and_date/<str:start>/<str:end>', views.total_order_by_stations_and_date),
    path('chart_api/<str:start_date>/<str:end_date>/',views.chart_api),
    path('massages/<str:start>/<str:end>',views.massages),
    path('additem/',views.additem), # Add items in existing order
    path('edititem/',views.editContent), # Add items in existing order
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>',views.makeunique),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>/',views.makeunique),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>/<int:vendorId>',views.makeunique),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>/?vendorId=<int:vendorId>',views.makeunique),
    path('koms_login/',views.koms_login)
]
