"""megameal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import *
from django.views.generic import TemplateView

urlpatterns = [
    path('',index),
    path('lang/',selectlang),
    path('lang/<str:lang>',selectlang),
    path('login/',login,name='kiosk_login'),
    path('logout/',logout_view,name='kiosk_logout'),
    path('allCategory/vendorId=<int:vendorId>',allCategory,name="allCategory"),
    path('allCategory/vendorId=<int:vendorId>/catId=<int:id>',allCategory,name="singleCategory"),
    path('productByCategory/<int:vendorId>',productByCategory,name="productByCategory"),
    path('productByCategory/<int:vendorId>/<int:id>',productByCategory,name="singleProductByCategory"),
    path('productDetails/',productDetails,name="allProduct"),
    path('productDetails/<int:id>',productDetails,name="singleProduct"),
    path('productDetails/<str:search>',productDetails,name="searchProduct"),
    # path('addToCart/',addToCart,name="addToCart"),
    path('allDiscounts/',getDiscounts,name='allDiscounts'),
    path('allDiscounts/<int:vendorId>',getDiscounts,name='allDiscounts'),
    path('applyDiscount/<int:vendorId>',applyDiscount,name='applyDiscount'),
    path('translate/<str:txt>',translation,name='translation'),
    path('createOrder/<int:vendorId>',createOrder),
    # path('allCategoryTemp/',allCategoryTemp), # show products
    # path('productByCategoryTemp/',productByCategoryTemp), # show products by category
    # path('productByCategoryTemp/<int:id>/',productByCategoryTemp), # show products by category
]
