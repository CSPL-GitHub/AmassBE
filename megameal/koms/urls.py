from django.urls import path
from koms import views
from django.urls import path



urlpatterns = [
    path('koms_login/', views.koms_login),
    path('staff', views.StaffView.as_view()),
    path('stationWiseStaff/<int:stationId>/', views.StationsStaffView.as_view()),
    path('stationOrder/', views.stationOrder, name='stationOrder'),
    path('orderStatus/', views.orderCount, name='orderStatus'),
    path('orderSearch/', views.ticketSearch, name='orderSearch'),
    path('updateOrderStatus/', views.updateTicketStatus, name='updateOrderStatus'),
    path('assignChef/', views.assignChef, name='assignChef'),
    path('chart_api/<str:start_date>/<str:end_date>/',views.chart_api),
    path('additem/', views.additem),
    path('edititem/', views.editContent),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>', views.makeunique),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>/', views.makeunique),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>/<int:vendorId>', views.makeunique),
    path('notify/<str:msg_type>/<str:msg>/<str:desc>/<str:stn>/?vendorId=<int:vendorId>', views.makeunique),
]
