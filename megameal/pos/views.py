from rest_framework.decorators import api_view
from django.http import JsonResponse, HttpResponse
from koms.serializers.content_history_serializer import Content_history_serializer
from kiosk.models import KioskOrderData
from kiosk.serializer import KiosK_create_order_serializer
from core.models import (
    Vendor, Product, ProductCategory, ProductCategoryJoint, ProductImage,
    ProductAndModifierGroupJoint, ProductModifier, ProductModifierGroup, Platform,
    ProductModifierAndModifierGroupJoint, Product_Tax, POS_Settings
)
from order import order_helper
from woms.models import HotelTable, Waiter, Floor
from woms.views import getTableData
from order.models import (
    Order, OrderItem, OrderPayment, Customer, Address, LoyaltyProgramSettings,
    LoyaltyPointsCreditHistory, LoyaltyPointsRedeemHistory, Order_Discount,
)
from django.core.paginator import Paginator
from django.contrib import messages
from core.utils import OrderStatus, OrderType, CorePlatform, API_Messages, PaymentType
from rest_framework.response import Response
from collections import defaultdict
from django.db.models.functions import Coalesce, ExtractWeekDay, ExtractHour, ExtractMonth
from django.db.models import Sum, Q, IntegerField, ExpressionWrapper, Count
from rest_framework.parsers import JSONParser 
from django.shortcuts import get_object_or_404
from koms.models import (
    Order_tables, Order_content, Order as KOMSOrder, KOMSOrderStatus, Order_modifer, Station, Staff,
)
from koms.views import allStationWiseCategory, allStationWiseRemove, allStationWiseSingle, getOrder, waiteOrderUpdate, webSocketPush
from django.utils import timezone
from datetime import datetime, timedelta, time
from rest_framework import status, viewsets, permissions, authentication
from pos.serializers import (
    WaiterSerializer, FloorSerializer, HotelTableSerializer , StoreTImingSerializer, ProductCategorySerializer,
    ProductSerializer, ProductCategoryJointSerializer, ProductImagesSerializer, ProductModGroupJointSerializer,
    ModifierGroupSerializer, ModifierSerializer, StationModelSerializer, DiscountCouponModelSerializer,
    ChefModelSerializer, BannerModelSerializer, CoreUserCategoryModelSerializer, CoreUserModelSerializer,
    DepartmentModelSerializer,
)
from pos.filters import (
    WaiterFilter, HotelTableFilter, ProductCategoryFilter, ModifierGroupFilter, DiscountCouponFilter,
    StationFilter, ChefFilter,
)
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from pos.models import POSUser ,StoreTiming, Banner, Setting, CoreUserCategory, CoreUser, Department
from pos.forms import PosUserForm
from django.conf import settings
from collections import OrderedDict
from django.core.files.storage import default_storage
from core.excel_file_upload import process_excel
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.hashers import make_password
from koms.views import notify
from static.order_status_const import WOMS
from pos.utils import order_count, get_product_data, get_modifier_data, process_product_excel
from inventory.utils import (
    single_category_sync_with_odoo, delete_category_in_odoo, single_product_sync_with_odoo, delete_product_in_odoo,
    single_modifier_group_sync_with_odoo, delete_modifier_group_in_odoo, single_modifier_sync_with_odoo,
    delete_modifier_in_odoo, sync_order_content_with_inventory,
)
from pos.language import get_key_value, check_key_exists, all_platform_locale, product_tag_locale
import pytz
import re
import openpyxl
import os
import socket
import json
import threading
from django.shortcuts import render
from operator import itemgetter
import requests
import calendar
import pgeocode



class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'total_pages': self.page.paginator.num_pages if self.page.paginator.count > 0 else 1,
            'current_page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'results': data
        })


def date_sort_top_selling_products(item):
    return item["order_date"]


def date_sort(date):
    year, month, day = date.split('-')
    return (int(year), int(month), int(day))


def date_sort_dashboard(item):
    return item["date"]


def date_sort_order_status_type_summary(item):
    return item["order_date"]


def get_order_id(order_data):
    return order_data["orderId"]


@api_view(["GET"])
def get_tax(request):
    vendor_id = request.GET.get("vendorId")

    if not vendor_id:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)

    tax_list = []

    taxes = Product_Tax.objects.filter(isDeleted=False, vendorId=vendor_id)

    for tax in taxes:
        tax_list.append({
            "id": tax.pk,
            "type": tax.name,
            "rate": tax.percentage,
            "value": round((tax.percentage / 100), 3),
            "is_active": tax.enabled,
        })

    return JsonResponse({"taxes":tax_list})


@api_view(["POST"])
def create_tax(request):
    tax_type = request.data.get("type")
    rate = request.data.get("rate")
    is_active = request.data.get("is_active")
    vendor_id = request.data.get("vendor_id")
    
    try:
        if not all([tax_type, rate, vendor_id]):
            raise ValueError
    
        vendor_id = int(vendor_id)
        rate = float(rate)
        is_active = bool(is_active)

        if tax_type not in ("SGST", "CGST"):
            raise ValueError
    
    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)

    existing_tax = Product_Tax.objects.filter(name=tax_type, isDeleted=False, vendorId=vendor_id).first()

    if existing_tax:
        return Response("Entry already created", status=status.HTTP_409_CONFLICT)

    tax = Product_Tax.objects.create(
        name=tax_type,
        percentage=rate,
        enabled=is_active,
        isDeleted=False,
        vendorId=vendor_instance
    )

    tax_info = {
        "type": tax.name,
        "rate": tax.percentage,
        "value": round((tax.percentage / 100), 3),
        "is_active": tax.enabled,
    }

    return JsonResponse(tax_info, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
def update_tax(request):
    tax_id = request.data.get("id")
    tax_type = request.data.get("type")
    rate = request.data.get("rate")
    is_active = request.data.get("is_active")
    vendor_id = request.data.get("vendor_id")
    
    try:
        if not all((tax_id, tax_type, rate, vendor_id)):
            raise ValueError
    
        tax_id = int(tax_id)
        vendor_id = int(vendor_id)
        rate = float(rate)
        is_active = bool(is_active)

        if tax_type not in ("SGST", "CGST"):
            raise ValueError
    
    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)

    tax = Product_Tax.objects.filter(pk=tax_id, vendorId=vendor_id).first()

    if not tax:
        return Response("No record found", status=status.HTTP_404_NOT_FOUND)
    
    tax.name = tax_type
    tax.percentage = rate
    tax.enabled = is_active

    tax.save()

    tax_info = {
        "type": tax.name,
        "rate": tax.percentage,
        "value": round((tax.percentage / 100), 3),
        "is_active": tax.enabled,
    }

    return JsonResponse(tax_info)


@api_view(["DELETE"])
def delete_tax(request):
    tax_id = request.data.get("id")
    vendor_id = request.data.get("vendor_id")
    
    try:
        if not all((tax_id, vendor_id)):
            raise ValueError
    
        tax_id = int(tax_id)
        vendor_id = int(vendor_id)
    
    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)

    tax = Product_Tax.objects.filter(pk=tax_id, vendorId=vendor_id).first()

    if not tax:
        return Response("No record found", status=status.HTTP_404_NOT_FOUND)
    
    tax.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def login(request):
    try:
        username = request.data.get("name")
        password = request.data.get("password")

        user = POSUser.objects.filter(username=username, password=password, is_active=True).first()

        if not user:
            return JsonResponse({
                "message": "User not found",
                "user_id": 0,
                "token": "",
                "name": "",
                "email": "",
                "primary_language": "",
                "secondary_language": "",
                "selected_language": "",
                "currency": "",
                "currency_symbol": "",
                "vendor_id": 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        vendor_id = user.vendor.pk

        vendor_instance = Vendor.objects.filter(pk=user.vendor.pk).first()

        if not vendor_instance:
            return JsonResponse({
                "message": "Invalid Vendor",
                "user_id": 0,
                "token": "",
                "name": "",
                "email": "",
                "primary_language": "",
                "secondary_language": "",
                "selected_language": "",
                "currency": "",
                "currency_symbol": "",
                "vendor_id": 0
            }, status=status.HTTP_400_BAD_REQUEST)

        platform = Platform.objects.filter(Name="POS", isActive=True, VendorId=vendor_id).first()

        if (not platform) or (platform.expiryDate.date() < timezone.now().date()):
            return JsonResponse({
                "message": "User not found",
                "user_id": 0,
                "token": "",
                "name": "",
                "email": "",
                "primary_language": "",
                "secondary_language": "",
                "selected_language": "",
                "currency": "",
                "currency_symbol": "",
                "vendor_id": 0
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({
            "message": "",
            "user_id": user.pk,
            "token": "",
            "name": user.name,
            "email": user.email,
            "primary_language": vendor_instance.primary_language,
            "secondary_language": vendor_instance.secondary_language if vendor_instance.secondary_language else "",
            "selected_language": vendor_instance.selected_language,
            "currency": vendor_instance.currency,
            "currency_symbol": vendor_instance.currency_symbol,
            "vendor_id": vendor_id,
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse({
            "message": str(e),
            "user_id": 0,
            "token": "",
            "name": "",
            "email": "",
            "primary_language": "",
            "secondary_language": "",
            "currency": "",
            "currency_symbol": "",
            "vendor_id": 0
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 


@api_view(['GET', 'POST'])
def pos_lanuage_setting(request):
    vendor_id = request.GET.get("vendor")

    if not vendor_id:
        return JsonResponse({"message": "Invalid Vendor ID", "langauge": ""}, status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return JsonResponse({"message": "Vendor not found", "langauge": ""}, status=status.HTTP_400_BAD_REQUEST)
    
    if request.method == "GET":
        return JsonResponse({"message": "", "language": vendor_instance.selected_language}, status=status.HTTP_200_OK)
    
    else:
        language = request.GET.get("language")

        if not language:
            return JsonResponse({"message": "Language not specified", "langauge": ""}, status=status.HTTP_400_BAD_REQUEST)

        vendor_instance.selected_language = language
        vendor_instance.save()

        return JsonResponse({"message": "", "language": vendor_instance.selected_language}, status=status.HTTP_200_OK)


@api_view(['GET'])
def allCategory(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language", "English")

        if not vendor_id:
            return JsonResponse({"message": "Invalid Vendor ID", "categories": []}, status=status.HTTP_400_BAD_REQUEST)

        categories = ProductCategory.objects.filter(categoryIsDeleted=False, vendorId=vendor_id)
        
        category_list = []

        if language == "English":
            for single_category in categories:
                category_list.append({
                    "categoryId": single_category.pk,
                    "categoryPlu": single_category.categoryPLU,
                    "name": single_category.categoryName,
                    "description": single_category.categoryDescription,
                    "image": single_category.categoryImageUrl if single_category.categoryImageUrl else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
                    "is_active": single_category.is_active
                })

        else:
            for single_category in categories:
                category_list.append({
                    "categoryId": single_category.pk,
                    "categoryPlu": single_category.categoryPLU,
                    "name": single_category.categoryName_locale,
                    "description": single_category.categoryDescription_locale,
                    "image": single_category.categoryImageUrl if single_category.categoryImageUrl else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
                    "is_active": single_category.is_active
                })

        return JsonResponse({"message": "", "categories": category_list}, status=status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse({"message": str(e), "categories": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def productByCategory(request, id=0):
    try:
        vendor_id=request.GET.get("vendorId")
        language = request.GET.get("language", "English")
        search_text = request.GET.get("search")

        if not vendor_id:
            return JsonResponse({"message": "Invalid Vendor ID", "products": {}}, status=status.HTTP_400_BAD_REQUEST)

        if id != 0:
            data = ProductCategory.objects.filter(pk=id)

        else:
            data = ProductCategory.objects.filter(categoryIsDeleted=False, vendorId=vendor_id)
        
        products = {}

        for category in data:
            product_list = []

            filtered_products = Product.objects.filter(pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product')), isDeleted=False, vendorId=vendor_id)
            
            if search_text:
                if language == "English":
                    filtered_products = filtered_products.filter(productName__icontains=search_text)

                else:
                    filtered_products = filtered_products.filter(productName_locale__icontains=search_text)
            
            for product in filtered_products:
                # product_variants = []

                # if product.productType == "Variant":
                #     for variant in Product.objects.filter(productParentId=product.pk, vendorId=vendor_id, isDeleted=False):
                #         images = []

                #         for instance in ProductImage.objects.filter(product=variant.pk):
                #             if instance is not None:
                #                 images.append(str(instance.image))
                        
                #         options = []

                #         for varinatJoint in Product_Option_Joint.objects.filter(productId=variant.pk, vendorId=vendor_id):
                #             options.append(
                #                 {
                #                     "optionId":varinatJoint.optionId.optionId, 
                #                     "optionValueId":varinatJoint.optionValueId.itemOptionId 
                #                 }
                #             )

                #         product_variants.append({
                #             "text":variant.productName,
                #             # "imagePath": HOST+variant.productThumb.name if variant.productThumb !="" else images[0] if len(images)!=0 else HOST+DEFAULTIMG,
                #             # "images":images if len(images)  else [HOST+DEFAULTIMG],
                #             "quantity": 0,
                #             "cost": variant.productPrice,
                #             "description":variant.productDesc,
                #             "allowCustomerNotes": True,
                #             "plu":variant.PLU,
                #             "type":variant.productType,
                #             "options":options
                #         })

                images = []

                product_images = ProductImage.objects.filter(product=product.pk, vendorId=vendor_id)

                for instance in product_images:
                    if instance is not None:
                        images.append(str(instance.url))
                
                modifier_group_list = []

                product_and_modifier_group_joint = ProductAndModifierGroupJoint.objects.filter(product=product.pk, vendorId=vendor_id)
                
                if product_and_modifier_group_joint:
                    for product_and_modifier_group_instance in product_and_modifier_group_joint:
                        modifier_list = []

                        modifier_and_group_joint = ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=product_and_modifier_group_instance.modifierGroup.pk, modifierGroup__isDeleted=False, vendor=vendor_id)
                        
                        if modifier_and_group_joint:
                            for modifier_and_group_instance in modifier_and_group_joint:
                                modifier_name = ""
                                modifier_description = ""

                                if language == "English":
                                    modifier_name = modifier_and_group_instance.modifier.modifierName
                                    modifier_description = modifier_and_group_instance.modifier.modifierDesc

                                else:
                                    modifier_name = modifier_and_group_instance.modifier.modifierName_locale
                                    modifier_description = modifier_and_group_instance.modifier.modifierDesc_locale
                                
                                modifier_list.append(
                                    {
                                        "cost": modifier_and_group_instance.modifier.modifierPrice,
                                        "modifierId": modifier_and_group_instance.modifier.pk,
                                        "name": modifier_name,
                                        "description": modifier_description,
                                        "quantity": 0,
                                        "plu": modifier_and_group_instance.modifier.modifierPLU,
                                        "image": modifier_and_group_instance.modifier.modifierImg if modifier_and_group_instance.modifier.modifierImg else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                                        # "image":modifier_and_group_instance.modifier.modifierImg,
                                        "active": modifier_and_group_instance.modifier.active
                                    }                    
                                )

                        if product_and_modifier_group_instance.modifierGroup.isDeleted == False: 
                            modifier_group_name = ""
                            modifier_group_description = ""

                            if language == "English":
                                modifier_group_name = product_and_modifier_group_instance.modifierGroup.name
                                modifier_group_description = product_and_modifier_group_instance.modifierGroup.modifier_group_description
                            
                            else:
                                modifier_group_name = product_and_modifier_group_instance.modifierGroup.name_locale
                                modifier_group_description = product_and_modifier_group_instance.modifierGroup.modifier_group_description_locale

                            modifier_group_list.append(
                            {
                                "id": product_and_modifier_group_instance.modifierGroup.pk,
                                "name": modifier_group_name,
                                "plu": product_and_modifier_group_instance.modifierGroup.PLU,
                                "description": modifier_group_description,
                                # "min": product_and_modifier_group_instance.min,
                                # "max": product_and_modifier_group_instance.max,
                                "min": product_and_modifier_group_instance.modifierGroup.min,
                                "max": product_and_modifier_group_instance.modifierGroup.max,
                                # "type": product_and_modifier_group_instance.modifierGroup.modGrptype,
                                "active": product_and_modifier_group_instance.modifierGroup.active,
                                "modifiers": modifier_list
                            }
                        )
                    
                category_name = ""
                product_name = ""
                product_description = ""
                product_tag = ""

                if language == "English":
                    category_name = category.categoryName
                    product_name = product.productName
                    product_description = product.productDesc if product.productDesc else ""
                    product_tag = product.tag if product.tag else ""
                
                else:
                    category_name = category.categoryName_locale
                    product_name = product.productName_locale
                    product_description = product.productDesc_locale if product.productDesc_locale else ""
                    product_tag = product_tag_locale[product.tag] if product.tag else ""
                
                product_list.append({
                    "categoryId": category.pk,
                    "categoryName": category_name,
                    "productId": product.pk,
                    "plu": product.PLU,
                    "name": product_name,
                    "description": product_description,
                    "cost": product.productPrice,
                    "tag":  product_tag,
                    "imagePath": images[0] if len(images)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                    "images": images if len(images)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
                    "isTaxable": product.taxable,
                    "type": product.productType,
                    "variant": [],
                    "quantity": 0, # Required for Flutter model
                    "active": product.active,
                    "modifiersGroup": modifier_group_list,
                })
                
            products[category.pk] = product_list

        return JsonResponse({"message": "", "products": products}, status=status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse({"message": str(e), "products": {}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def dashboard(request):
    vendor_id = request.GET.get("vendor")
    language = request.GET.get("language", "English")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)

    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    completed_status_code = OrderStatus.get_order_status_value('COMPLETED')
    canceled_status_code = OrderStatus.get_order_status_value('CANCELED')
    inprogress_status_code = OrderStatus.get_order_status_value('INPROGRESS')
    open_status_code = OrderStatus.get_order_status_value('OPEN')
    prepared_status_code = OrderStatus.get_order_status_value('PREPARED')
    
    sales_order_list = []
    new_sales_order_list = []
    new_orders_count = 0
    
    orders = Order.objects.filter(
        OrderDate__date__range=(start_date, end_date),
        vendorId=vendor_id
    )

    new_orders_count = KOMSOrder.objects.filter(
        order_status=1,
        arrival_time__date__range=(start_date, end_date),
        vendorId=vendor_id
    ).count()
    
    subtotal_sum, discount_sum = orders.filter(
        orderpayment__status=True
    ).exclude(Status=canceled_status_code).aggregate(subtotal_sum=Sum('subtotal'), discount_sum=Sum('discount')).values()

    subtotal_sum = subtotal_sum or 0.0
    discount_sum = discount_sum or 0.0
    
    total_sale = "{:.2f}".format(subtotal_sum - discount_sum)

    active_product_count = Product.objects.filter(isDeleted=False, vendorId=vendor_id).count()

    online_order_platform = Platform.objects.filter(Name__in=('Mobile App', 'Website'), VendorId=vendor_id).first()

    online_order_platform_id = ""
    
    if online_order_platform:
        online_order_platform_id = str(online_order_platform.pk)

    total_orders_canceled = orders.filter(Status=canceled_status_code).count()
    
    orders = orders.exclude(Status=canceled_status_code)

    all_orders = orders
    
    total_orders = orders.count()
    total_orders_completed = orders.filter(Status=completed_status_code, orderpayment__status=True).count()
    total_orders_inprogress = orders.filter(Status__in=[inprogress_status_code, open_status_code, prepared_status_code]).count()
    total_orders_inprogress = total_orders_inprogress - new_orders_count
    total_orders_pickedup = orders.filter(orderType=OrderType.get_order_type_value('PICKUP')).count()
    total_orders_delivered = orders.filter(orderType=OrderType.get_order_type_value('DELIVERY')).count()
    total_orders_dined = orders.filter(orderType=OrderType.get_order_type_value('DINEIN')).count()
    online_orders_count = orders.filter(platform__Name__in=('Mobile App', 'Website')).count()

    orders = orders.filter(orderpayment__status=True).exclude(Status=canceled_status_code)

    current_start_date = current_end_date = datetime.now().date()
    
    if ((start_date == end_date) and (start_date == current_start_date and end_date == current_end_date)) or \
    ((start_date != end_date) and (start_date != current_start_date and end_date == current_end_date)):
        start_datetime = datetime.strptime(str(start_date) + " 00:00:00.000000", '%Y-%m-%d %H:%M:%S.%f')
        current_datetime = datetime.now()
        end_datetime = current_datetime.replace(minute=0, second=0, microsecond=0)

        current_datetime = start_datetime
    
    elif (start_date == end_date) and (start_date != current_start_date and end_date != current_end_date):
        store_timing = StoreTiming.objects.filter(day=start_date.strftime("%A"), vendor=vendor_id).first()

        start_datetime = datetime.combine(start_date, store_timing.open_time)

        if end_date == datetime.now().date():
            end_datetime = datetime.combine(start_date, time(datetime.now().time().hour, 0, 0))
        else:
            end_datetime = datetime.combine(start_date, store_timing.close_time)

        current_datetime = start_datetime

    else:
        start_datetime = datetime.strptime(str(start_date) + " 00:00:00.000000", '%Y-%m-%d %H:%M:%S.%f')
        end_datetime = datetime.strptime(str(end_date) + " 23:59:59.000000", '%Y-%m-%d %H:%M:%S.%f')
        
        current_datetime = start_datetime
    
    if orders.exists():
        while current_datetime <= end_datetime:
            current_hour_start = current_datetime
            current_hour_end = current_datetime + timedelta(hours=1)

            filtered_orders = orders.filter(
                OrderDate__range=(current_hour_start, current_hour_end)
            )

            subtotal_sum, discount_sum = filtered_orders.aggregate(subtotal_sum=Sum('subtotal'), discount_sum=Sum('discount')).values()
            
            subtotal_sum = subtotal_sum or 0.0
            discount_sum = discount_sum or 0.0

            total_sale_hourly = "{:.2f}".format(subtotal_sum - discount_sum)

            sales_order_list.append({
                "date": current_hour_start.astimezone(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M'),
                "total_sale": total_sale_hourly,
                "completed_orders_count": filtered_orders.count(),
                "total_orders_count": all_orders.filter(OrderDate__range=(current_hour_start, current_hour_end)).count()
            })

            current_datetime += timedelta(hours=1)

        running_total_sales = 0.0
        running_completed_orders = 0
        running_total_orders = 0
        
        for data in sales_order_list:
            running_total_sales = running_total_sales + float(data["total_sale"])
            running_completed_orders = running_completed_orders + data["completed_orders_count"]
            running_total_orders = running_total_orders + data["total_orders_count"]

            new_sales_order_list.append({
                "date": data["date"],
                "total_sale": "{:.2f}".format(running_total_sales),
                "completed_orders_count": running_completed_orders,
                "total_orders_count": running_total_orders,
            })

        if len(new_sales_order_list) == 1:
            first_item = new_sales_order_list[0]
            date_value = first_item["date"]

            date_obj = datetime.strptime(date_value, '%Y-%m-%d')

            date_obj = date_obj - timedelta(days=1)

            date_value = date_obj.strftime('%Y-%m-%d')

            new_sales_order_list.append({
                "date": date_value,
                "total_sale": "0.0",
                "completed_orders_count": 0,
                "total_orders_count": 0
            })
    
    order_items = Order_content.objects.filter(
        orderId__order_status=10,
        orderId__master_order__Status=completed_status_code,
        orderId__master_order__orderpayment__status=True,
        orderId__master_order__OrderDate__date__range=(start_date, end_date),
        orderId__master_order__vendorId=vendor_id,
        orderId__vendorId=vendor_id
    )
    
    total_items_sold = order_items.values('SKU').distinct().count()
    
    top_selling_items = order_items.values('SKU').annotate(quantity_sold=Sum('quantity')).order_by('-quantity_sold')[:6]

    list_of_items = []

    for item in top_selling_items:
        product = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()
        
        product_image = ProductImage.objects.filter(
            product=product.pk,
            vendorId=vendor_id
        ).first()

        image_url = 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
        
        if product_image:    
            image_url = product_image.url

        product_name = ""

        if language == "English":
            product_name = product.productName
        
        else:
            product_name = product.productName_locale
        
        item['id'] = product.pk
        item['product_name'] = product_name
        item['image'] = image_url
        item['price'] = product.productPrice
        item['sale'] = item['quantity_sold'] * product.productPrice

        list_of_items.append(item)

    order_details = {
        "online_order_platform_id": online_order_platform_id,
        "active_products": active_product_count,
        "total_sale": total_sale,
        "total_orders": total_orders,
        "items_sold": total_items_sold,
        "orders_completed": total_orders_completed,
        "orders_canceled": total_orders_canceled,
        "orders_inprogress": total_orders_inprogress,
        "orders_pickedup": total_orders_pickedup,
        "orders_delivered": total_orders_delivered,
        "orders_dined": total_orders_dined,
        "online_orders": online_orders_count,
        "new_orders": new_orders_count,
        "sales_order": new_sales_order_list,
        "top_selling": list_of_items
    }

    return Response(order_details)


@api_view(["POST"])
def modifier_update(request):
    if request.method == "POST":
        modifier_id = request.data['id']

        modifier = get_object_or_404(ProductModifier, pk=modifier_id)

        modifier.active = request.data['active']

        ProductModifier.objects.filter(modifierSKU=modifier.modifierSKU).update(active=request.data['active'])

        # try:
        #     id=WooCommerce.getModifierUsingSKU(sku=modifier.modifierSKU,vendorId=modifier.vendorId)
        #     platform = Platform.objects.get(VendorId=modifier.vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
        #     catlogHeaders = {
        #         "Content-Type": "application/json"
        #     }
        #     payload = {
        #         "hide":0 if modifier.active else 1
        #     }
        #     url = platform.baseUrl + "wp-json/v1/custom/updateModifierStatus/"+str(id['response']['id'])
        #     wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
        #     print(json.dumps(wooResponse.json()))
        # except Exception as err:
        #     print(err)

        return JsonResponse({"message": "Modifier status updated successfully"}, content_type="application/json")
    
    else:
        return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")


@api_view(["POST"])
def order_status_type_summary(request):
    required_fields = {
        "vendor_id", "order_status_code", "order_type_code", "start_date", "end_date", "page_number", "page_limit"
    }
    
    missing_fields = required_fields - set(request.data.keys())

    if missing_fields:
        return Response(f"Missing required fields: {', '.join(missing_fields)}", status=status.HTTP_400_BAD_REQUEST)

    try:
        vendor_id = int(request.data.get('vendor_id'))
        order_status_code = int(request.data.get('order_status_code'))
        order_type_code = int(request.data.get('order_type_code'))
        page_number = int(request.data.get('page_number'))
        page_limit = int(request.data.get('page_limit'))

        if any(value < 0 for value in (vendor_id, order_status_code, page_number, page_limit)):
            raise ValueError
        
        start_date = datetime.strptime(request.data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.data.get('end_date'), '%Y-%m-%d').date()

    except Exception:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    if start_date > end_date:
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    orders = KOMSOrder.objects.filter(
        master_order__OrderDate__date__range=(start_date, end_date),
        master_order__vendorId=vendor_id,
        vendorId=vendor_id
    )
        
    if not orders.exists():
        return JsonResponse({
            "page_number": 1,
            "total_pages": 1,
            "orders": [],
        })
    
    if order_type_code != 0:
        orders = orders.filter(order_type=order_type_code)
    
    if order_status_code in [2, 3, 4, 6, 7, 8, 9]:
        orders = orders.filter(order_status__in=[2, 3, 4, 6, 7, 8, 9])
            
    else:
        orders = orders.filter(order_status=order_status_code)
    
    if not orders.exists():
        return JsonResponse({
            "page_number": 1,
            "total_pages": 1,
            "orders": [],
        })
    
    order_list = []
    
    current_start_date = current_end_date = datetime.now().date()
    
    if start_date == end_date:
        store_timing = StoreTiming.objects.filter(day=start_date.strftime("%A"), vendor=vendor_id).first()

        start_datetime = datetime.combine(start_date, store_timing.open_time)
        end_datetime = datetime.combine(end_date, store_timing.close_time)
        
        if (start_date == current_start_date) and (end_date == current_end_date):
            end_datetime = datetime.now() + timedelta(minutes=59, seconds=59)

        current_time = start_datetime
        
        while current_time <= end_datetime:
            next_time = current_time + timedelta(hours=1)
            
            filtered_orders =  orders.filter(arrival_time__range=(current_time, next_time))

            order_list.append({
                "order_date": current_time.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M"),
                "total_order": filtered_orders.count(),
            })

            current_time = next_time
    
        if len(order_list) == 1:
            first_item = order_list[0]
            date_value = first_item["order_date"]

            date_obj = datetime.strptime(date_value, '%Y-%m-%d')

            date_obj = date_obj - timedelta(hours=1)

            date_value = date_obj.strftime('%Y-%m-%d')

            order_list.append({
                "order_date": date_value,
                "total_order": 0
            })
    
    else:
        unique_order_dates = sorted(set(orders.values_list('arrival_time__date', flat=True)), reverse=True)

        for unique_date in unique_order_dates:
            filtered_orders = orders.filter(arrival_time__icontains=unique_date)
            
            total_order = filtered_orders.count()

            order_list.append({
                    "order_date": unique_date,
                    "total_order": total_order,
                })
                
        if len(order_list) == 1:
            first_item = order_list[0]
            date_value = first_item["order_date"].strftime('%Y-%m-%d')

            date_obj = datetime.strptime(date_value, '%Y-%m-%d')

            date_obj = date_obj - timedelta(days=1)

            date_value = date_obj.strftime('%Y-%m-%d')

            order_list.append({
                "order_date": date_value,
                "total_order": 0
            })

    paginated_data = []
    
    paginator = Paginator(order_list, page_limit)
    page = paginator.get_page(page_number) 

    for order in page:
        paginated_data.append({
            "order_date": order['order_date'],
            "total_order": order['total_order'],
        })

    return JsonResponse({
        "page_number": page.number,
        "total_pages": paginator.num_pages,
        "orders": paginated_data,
    })


@api_view(["GET"])
def showtabledetails(request):
    try:
        data=HotelTable.objects.filter(vendorId=request.GET.get('vendorId'))
        data=data.order_by('tableNumber')
        return Response([ getTableData(i,request.GET.get('vendorId')) for i in data ]) 
    except Exception as e :
            print(e)
            return []
        
@api_view(['GET'])
def show_tableCapacity(request):
    vendorId=request.GET.get("vendorId")
    try:
        data=HotelTable.objects.filter(vendorId=vendorId)
        tableCapacity =list(set([ i.tableCapacity for i in data]))
        table = [str(i) for i in tableCapacity]
        return JsonResponse({ "tableCapacity": table}, safe=False)
    except Exception as e:
        return JsonResponse({"error":str(e)})

@api_view(["POST", "GET"])
def productStatusChange(request):
    try:
        data = JSONParser().parse(request)

        product = Product.objects.filter(pk=data["productId"])
        vendor_id = data["vendorId"]

        if product:
            product.update(active=data["status"])

            res = Product.objects.get(pk=data["productId"], vendorId=vendor_id)

            # prod=WooCommerce.disalbeProductUsingId(sku=res.SKU,active=res.active,vendorId=res.vendorId)
            
            return JsonResponse({'productId': res.pk, 'status':res.active})
        
        else:
            return JsonResponse({'error': 'Product not found'}, status=400)
    
    except Exception as e:
            return JsonResponse({'error': e}, status=400)


def order_data_start_thread(vendor_id, page_number, search, order_status, order_type, platform, is_dashboard=0, s_date=None, e_date=None, language="English"):
        print("Starting koms thread...")
        thr = threading.Thread(
                target=order_data, args=(), kwargs={
                    "vendor_id":vendor_id,
                    "page_number":page_number,
                    "search":search,
                    "order_status":order_status,
                    'order_type':order_type,
                    "platform":platform,
                    "search":search,
                    "platform":platform,
                    "s_date":s_date,
                    "e_date":e_date,
                    "is_dashboard":is_dashboard,
                    "language": language
                }
            )
        
        thr.setDaemon(True)
        thr.start()

        return {"connecting":False}


def order_data(vendor_id, page_number, search, order_status, order_type, platform, is_dashboard=0, s_date=None, e_date=None, language="English"):
    if vendor_id == None:
        error_message = "Vendor ID cannot be empty"
        return error_message
        
    order_details = {}

    sd=s_date if s_date is not  None else ""
    ed=e_date if e_date is not None else ""
    se=search if search != 'All' else ""
    pl=platform if platform!="All" else ''
    pn=page_number if page_number!="All" else ""
    os=order_status if order_status!="All" else ''
    oe=order_type if order_type!="All" else ''
    current_date = datetime.today().strftime("%Y-%m-%d")
    
    if e_date is not None and s_date is not None:
        s_date = str(s_date).replace("T","-")+" 00:00:00.000000"
        e_date = str(e_date).replace("T","-") + " 23:59:59.000000"

        order_data = KOMSOrder.objects.filter(arrival_time__range=(s_date, e_date), vendorId=vendor_id)
    
    else:
        order_data = KOMSOrder.objects.filter(arrival_time__date=current_date, vendorId=vendor_id)
    
    if order_status != "All":
        if is_dashboard == 0:
            order_data = order_data.filter(order_status=order_status)
        elif is_dashboard == 1:
            if order_status == 10 :
                order_data = order_data.filter(order_status__in=[5,10])
            else:
                order_data = order_data.filter(order_status=order_status)

    else:
        if is_dashboard == 1:
            order_data = order_data.filter(order_status__in=[2, 3, 4, 6, 7, 8, 9])

    if order_type != "All":
        order_data = order_data.filter(order_type=order_type)

    if platform != "All":
        external_order_ids = list(order_data.values_list('externalOrderId', flat=True))
        platformData = Platform.objects.get(pk=platform)

        if str(platformData.Name).lower() == "woocommerce":
            order_data = Order.objects.filter(pk__in=external_order_ids)
            order_data = order_data.filter(platform=platform)
            external_order_ids = list(order_data.values_list('pk', flat=True))
        
        else:
            order_data = Order.objects.filter(externalOrderld__in=external_order_ids)
            order_data = order_data.filter(platform=platform)
            external_order_ids = list(order_data.values_list('externalOrderld', flat=True))

        order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)

    if search != 'All':
        expression = r'\d+'
        output = re.search(expression, search)

        if output:
            master_order_id = output.group()

            order_data = order_data.filter(master_order__pk__icontains=master_order_id)
            
            if order_data:    
                if order_status != "All":
                    order_data = order_data.filter(order_status=order_status)

                if order_type != "All":
                    order_data = order_data.filter(order_type=order_type)

                if platform != "All":
                    external_order_ids = list(order_data.values_list('externalOrderId', flat=True))

                    order_data = Order.objects.filter(externalOrderld__in=external_order_ids)

                    order_data = order_data.filter(platform=platform)

                    external_order_ids = list(order_data.values_list('externalOrderld', flat=True))

                    order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)
            
            else:
                response_data = {
                    'page_number': 0,
                    'total_pages': 0,
                    'data_count': 0,
                    'order_details': {},
                }
                
                return response_data

        else:
            expression = r'[A-Za-z ]+'

            output = re.search(expression, search)

            if output:
                customer_name = output.group()

                order_data = order_data.filter(
                    Q(master_order__customerId__FirstName__icontains=customer_name) | \
                    Q(master_order__customerId__LastName__icontains=customer_name)
                )
                
                external_order_ids = list(order_data.values_list('externalOrderId', flat=True))

                order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)
                
                if order_data:    
                    if order_status != "All":
                        order_data = order_data.filter(order_status=order_status)

                    if order_type != "All":
                        order_data = order_data.filter(order_type=order_type)

                    if platform != "All":
                        external_order_ids = list(order_data.values_list('externalOrderId', flat=True))

                        order_data = Order.objects.filter(externalOrderld__in=external_order_ids)

                        order_data = order_data.filter(platform=platform)

                        external_order_ids = list(order_data.values_list('externalOrderld', flat=True))

                        order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)

                else:
                    response_data = {
                        'page_number': 0,
                        'total_pages': 0,
                        'data_count': 0,
                        'order_details': {},
                    }
                    
                    return response_data
    
    order_data = order_data.order_by("-master_order__OrderDate")
    
    paginator = Paginator(order_data, 10)

    page_obj = paginator.get_page(page_number)

    orders_for_page = page_obj.object_list

    for order in orders_for_page:
        single_order = getOrder(ticketId=order.pk, language=language, vendorId=vendor_id)
        
        try:
            payment_details_order = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId))| Q(pk=str(order.externalOrderId))).last()
            
            payment_type = OrderPayment.objects.filter(orderId=payment_details_order.pk)
            
            payment_mode = get_key_value(language, "payment_type", payment_type)
            
            payment_details ={
                "total": payment_details_order.TotalAmount,
                "subtotal": payment_details_order.subtotal,
                "tax": payment_details_order.tax,
                "delivery_charge": payment_details_order.delivery_charge,
                "discount": payment_details_order.discount,
                "tip": payment_details_order.tip,
                "paymentKey": payment_type.last().paymentKey,
                "platform": payment_type.last().platform,
                "status": payment_type.last().status,
                "mode": payment_mode
            }
            
        except Exception as e:
            print("Error", e)

            payment_mode = get_key_value(language, "payment_type", 1)

            payment_details ={
                "total":0.0,
                "subtotal":0.0,
                "tax":0.0,
                "delivery_charge":0.0,
                "discount":0.0,
                "tip":0.0,
                "paymentKey":"",
                "platform":"",
                "status":False,
                "mode": payment_mode
            }
            
        single_order['payment'] = payment_details

        try:
            platform = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId))| Q(pk=str(order.externalOrderId))).last()

            platform_name = ""
            
            if language == "English":
                platform_name = platform.platform.Name

            else:
                platform_name = platform.platform.Name_locale
            
            platform_details = {
                "id": platform.platform.pk,
                "name": platform_name
            }

        except Exception as e:
            print(e)
            platform_details = {
                "id" : 0,
                "name" :""
            }

        single_order["platform_details"] = platform_details

        try:
            customer = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId)) | Q(pk=str(order.externalOrderId))).last()
            
            if customer:
                first_name = customer.customerId.FirstName
                last_name = customer.customerId.LastName

                customer_name = first_name
                
                if last_name:
                    customer_name = first_name + " " + last_name
            
            else:
                customer_name = ""

            address = Address.objects.filter(customer=customer.customerId.pk, is_selected=True, type="shipping_address").first()

            if address:
                if address.address_line2:
                    shipping_address = address.address_line1 + " " + address.address_line2 + " " + address.city + " " + address.state + " " + address.country + " " + address.zipcode

                else:
                    shipping_address = address.address_line1 + " " + address.city + " " + address.state + " " + address.country + " " + address.zipcode
            
            else:
                shipping_address = ""

            customer_details = {
                "id" : customer.customerId.pk,
                "name" : customer_name,
                "mobile" : customer.customerId.Phone_Number,
                "email" : customer.customerId.Email if customer.customerId.Email else "",
                "shipping_address" : shipping_address
            }

        except Exception as e:
            print(e)
            customer_details = {
                "id" : 0,
                "name" :"",
                "mobile" : "",
                "email" : "",
                "shipping_address" : ""
            }

        single_order["customer_details"] = customer_details

        loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=customer.customerId.pk, order=order.master_order.pk)

        if loyalty_points_redeem_history.exists():
            total_points_redeemed = loyalty_points_redeem_history.aggregate(Sum('points_redeemed'))['points_redeemed__sum']

            if not total_points_redeemed:
                total_points_redeemed = 0

        else:
            total_points_redeemed = 0

        single_order["total_points_redeemed"] = total_points_redeemed

        order_details[order.pk]=single_order

    response_data = {
        'page_number': page_obj.number,
        'total_pages': paginator.num_pages,
        'data_count': paginator.count,
        'order_details': order_details,
    }
    
    webSocketPush(message=response_data,room_name=f"POS{os}-{se}-{pl}-{oe}-{pn}-{sd}-{ed}-{is_dashboard}-{language}-{str(vendor_id)}", username="CORE",)
    webSocketPush(message=response_data,room_name=f"POS{os}-{se}-{pl}-{oe}--{sd}-{ed}-{is_dashboard}-{language}-{str(vendor_id)}", username="CORE",)
    
    return response_data


# for order_data socket testing purpose
@api_view(["POST"])
def order_data_socket(request):
    body_data = json.loads(request.body)

    vendor_id = body_data.get("vendor_id")
    page_number = body_data.get("page_number")
    search = body_data.get("search")
    order_status = body_data.get("order_status")
    order_type = body_data.get("order_type")
    platform = body_data.get("platform")
    is_dashboard = body_data.get("is_dashboard")
    s_date = body_data.get("start_date")
    e_date = body_data.get("end_date")

    if vendor_id == None:
        error_message = "Vendor ID cannot be empty"
        return Response(error_message, status=status.HTTP_200_OK)
        
    order_details = {}

    current_date = datetime.today().strftime("%Y-%m-%d")
    
    if e_date is not None and s_date is not None:
        s_date = str(s_date).replace("T","-")+" 00:00:00.000000"
        e_date = str(e_date).replace("T","-") + " 23:59:59.000000"

        order_data = KOMSOrder.objects.filter(arrival_time__range=(s_date, e_date), vendorId=vendor_id)
    
    else:
        order_data = KOMSOrder.objects.filter(arrival_time__date=current_date, vendorId=vendor_id)
    
    if order_status != "All":
        if is_dashboard == 0:
            order_data = order_data.filter(order_status=order_status)
        elif is_dashboard == 1:
            if order_status == 10 :
                order_data = order_data.filter(order_status__in=[5,10])
            else:
                order_data = order_data.filter(order_status=order_status)

    else:
        if is_dashboard == 1:
            order_data = order_data.filter(order_status__in=[2, 3, 4, 6, 7, 8, 9])

    if order_type != "All":
        order_data = order_data.filter(order_type=order_type)

    if platform != "All":
        external_order_ids = list(order_data.values_list('externalOrderId', flat=True))
        platformData = Platform.objects.get(pk=platform)

        if str(platformData.Name).lower() == "woocommerce":
            order_data = Order.objects.filter(pk__in=external_order_ids)
            order_data = order_data.filter(platform=platform)
            external_order_ids = list(order_data.values_list('pk', flat=True))
        
        else:
            order_data = Order.objects.filter(externalOrderld__in=external_order_ids)
            order_data = order_data.filter(platform=platform)
            external_order_ids = list(order_data.values_list('externalOrderld', flat=True))

        order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)

    if search != 'All':
        expression = r'\d+'
        output = re.search(expression, search)

        if output:
            master_order_id = output.group()

            order_data = order_data.filter(master_order__pk__icontains=master_order_id)
            
            if order_data:    
                if order_status != "All":
                    order_data = order_data.filter(order_status=order_status)

                if order_type != "All":
                    order_data = order_data.filter(order_type=order_type)

                if platform != "All":
                    external_order_ids = list(order_data.values_list('externalOrderId', flat=True))

                    order_data = Order.objects.filter(externalOrderld__in=external_order_ids)

                    order_data = order_data.filter(platform=platform)

                    external_order_ids = list(order_data.values_list('externalOrderld', flat=True))

                    order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)
            
            else:
                response_data = {
                    'page_number': 0,
                    'total_pages': 0,
                    'data_count': 0,
                    'order_details': {},
                }
                
                return Response(response_data, status=status.HTTP_200_OK)

        else:
            expression = r'[A-Za-z ]+'

            output = re.search(expression, search)

            if output:
                customer_name = output.group()

                order_data = order_data.filter(
                    Q(master_order__customerId__FirstName__icontains=customer_name) | \
                    Q(master_order__customerId__LastName__icontains=customer_name)
                )
                
                external_order_ids = list(order_data.values_list('externalOrderId', flat=True))

                order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)
                
                if order_data:    
                    if order_status != "All":
                        order_data = order_data.filter(order_status=order_status)

                    if order_type != "All":
                        order_data = order_data.filter(order_type=order_type)

                    if platform != "All":
                        external_order_ids = list(order_data.values_list('externalOrderId', flat=True))

                        order_data = Order.objects.filter(externalOrderld__in=external_order_ids)

                        order_data = order_data.filter(platform=platform)

                        external_order_ids = list(order_data.values_list('externalOrderld', flat=True))

                        order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)

                else:
                    response_data = {
                        'page_number': 0,
                        'total_pages': 0,
                        'data_count': 0,
                        'order_details': {},
                    }
                    
                    return Response(response_data, status=status.HTTP_200_OK)
    
    order_data = order_data.order_by("-master_order__OrderDate")
    
    paginator = Paginator(order_data, 10)

    page_obj = paginator.get_page(page_number)

    orders_for_page = page_obj.object_list

    for order in orders_for_page:
        single_order = getOrder(ticketId=order.pk, vendorId=vendor_id)

        try:
            payment_details_order = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId))| Q(pk=str(order.externalOrderId))).last()
            payment_type = OrderPayment.objects.filter(orderId=payment_details_order.pk)
            
            payment_details ={
                "total":payment_details_order.TotalAmount,
                "subtotal":payment_details_order.subtotal,
                "tax":payment_details_order.tax,
                "delivery_charge":payment_details_order.delivery_charge,
                "discount":payment_details_order.discount,
                "tip":payment_details_order.tip,
                "paymentKey":payment_type.last().paymentKey,
                "platform":payment_type.last().platform,
                "status":payment_type.last().status,
                "mode":PaymentType.get_payment_str(payment_type.last().type) if payment_type else PaymentType.get_payment_str(PaymentType.CASH)
            }
            
        except Exception as e:
            print("Error", e)
            payment_details ={
                "total":0.0,
                "subtotal":0.0,
                "tax":0.0,
                "delivery_charge":0.0,
                "discount":0.0,
                "tip":0.0,
                "paymentKey":"",
                "platform":"",
                "status":False,
                "mode": PaymentType.get_payment_str(PaymentType.CASH)
            }
        
        single_order['payment']=payment_details

        try:
            platform = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId))| Q(pk=str(order.externalOrderId))).last()

            platform_details = {
                "id" : platform.platform.pk,
                "name" :"order online" if platform.platform.Name == "WooCommerce" else platform.platform.Name
            }

        except Exception as e:
            print(e)
            platform_details = {
                "id" : 0,
                "name" :""
            }

        single_order["platform_details"] = platform_details

        try:
            customer = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId)) | Q(pk=str(order.externalOrderId))).last()
            
            if customer:
                first_name = customer.customerId.FirstName
                last_name = customer.customerId.LastName

                customer_name = first_name
                
                if last_name:
                    customer_name = first_name + " " + last_name
            
            else:
                customer_name = ""

            address = Address.objects.filter(customer=customer.customerId.pk, is_selected=True, type="shipping_address").first()

            if address:
                if address.address_line2:
                    shipping_address = address.address_line1 + " " + address.address_line2 + " " + address.city + " " + address.state + " " + address.country + " " + address.zipcode

                else:
                    shipping_address = address.address_line1 + " " + address.city + " " + address.state + " " + address.country + " " + address.zipcode
            
            else:
                shipping_address = ""

            customer_details = {
                "id" : customer.customerId.pk,
                "name" : customer_name,
                "mobile" : customer.customerId.Phone_Number,
                "email" : customer.customerId.Email if customer.customerId.Email else "",
                "shipping_address" : shipping_address
            }

        except Exception as e:
            print(e)
            customer_details = {
                "id" : 0,
                "name" :"",
                "mobile" : "",
                "email" : "",
                "shipping_address" : ""
            }

        single_order["customer_details"] = customer_details

        loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=customer.customerId.pk, order=order.master_order.pk)

        if loyalty_points_redeem_history.exists():
            total_points_redeemed = loyalty_points_redeem_history.aggregate(Sum('points_redeemed'))['points_redeemed__sum']

            if not total_points_redeemed:
                total_points_redeemed = 0

        else:
            total_points_redeemed = 0

        single_order["total_points_redeemed"] = total_points_redeemed

        order_details[order.pk]=single_order

    response_data = {
        'page_number': page_obj.number,
        'total_pages': paginator.num_pages,
        'data_count': paginator.count,
        'order_details': order_details,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


class WaiterViewSet(viewsets.ModelViewSet):
    queryset = Waiter.objects.all()
    serializer_class = WaiterSerializer
    filter_class = WaiterFilter
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            queryset = Waiter.objects.filter(vendorId=vendor_id)

            return queryset
        
        else:
            return Waiter.objects.none()

    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # name_query = request.query_params.get('name', None)
        name_query = request.GET.get('name', None)
        
        if name_query:
            queryset = queryset.filter(name__icontains=name_query)

        serializer = self.get_serializer(queryset, many=True)
        data = {"waiters": serializer.data}
        
        return Response(data, status=status.HTTP_200_OK)


class FloorViewSet(viewsets.ModelViewSet):
    queryset = Floor.objects.all().order_by('id')
    serializer_class = FloorSerializer

    def get_queryset(self):
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            queryset = Floor.objects.filter(vendorId=vendor_id).order_by('id')

            return queryset
        
        else:
            return Floor.objects.none()
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        data = {"floors": serializer.data}
        
        return Response(data, status=status.HTTP_200_OK)
    

class HotelTableViewSet(viewsets.ModelViewSet):
    queryset = HotelTable.objects.all()
    serializer_class = HotelTableSerializer
    filter_class = HotelTableFilter
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            queryset = HotelTable.objects.filter(vendorId=vendor_id).order_by('tableNumber')

            return queryset
        
        else:
            return HotelTable.objects.none()
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        floor_id_query = request.GET.get('floor', None)

        if floor_id_query:
            queryset = queryset.filter(floor__id = floor_id_query).order_by('tableNumber')

        serializer = self.get_serializer(queryset, many=True)
        data = {"tables": serializer.data}
        
        return Response(data, status=status.HTTP_200_OK)
    
    def perform_create(self, serializer):
        instance = serializer.save()

        notify(
            type=3,
            msg='0',
            desc=f"Table no.{instance.tableNumber} created on {instance.floor.name}",
            stn=['POS'],
            vendorId=instance.vendorId.pk
        )

        response = getTableData(hotelTable=instance,vendorId=instance.vendorId.pk)
        
        webSocketPush(
            message={"result":response, "UPDATE": "UPDATE"},
            room_name=WOMS + "POS------" + str(instance.vendorId.pk),
            username="CORE",
        )

        waiter_heads = Waiter.objects.filter(is_waiter_head=True, vendorId=instance.vendorId.pk)

        if waiter_heads:
            for head in waiter_heads:
                notify(
                    type=3,
                    msg='0',
                    desc=f"Table no.{instance.tableNumber} created on {instance.floor.name}",
                    stn=[f'WOMS{head.pk}'],
                    vendorId=instance.vendorId.pk
                )
        
                webSocketPush(
                    message={"result":response, "UPDATE": "UPDATE"},
                    room_name=WOMS + str(head.pk) + "------" + str(instance.vendorId.pk),
                    username="CORE",
                )

    def perform_destroy(self, instance):
        instance.delete()

        notify(
            type=3,
            msg='0',
            desc=f"Table no.{instance.tableNumber} deleted on {instance.floor.name}",
            stn=['POS'],
            vendorId=instance.vendorId.pk
        )

        waiter_heads = Waiter.objects.filter(is_waiter_head=True, vendorId=instance.vendorId.pk)

        if waiter_heads:
            for head in waiter_heads:
                notify(
                    type=3,
                    msg='0',
                    desc=f"Table no.{instance.tableNumber} deleted on {instance.floor.name}",
                    stn=[f'WOMS{head.pk}'],
                    vendorId=instance.vendorId.pk
                )
    

@api_view(['POST'])
def createOrder(request):
    vendorId = request.GET.get('vendorId', None)
    language = request.GET.get("language", "English")

    if vendorId == None:
        return JsonResponse({"error": "Vendor Id cannot be empty"}, status=400, safe=False)
    
    try:
        print(request.data)

        orderid = vendorId + str(CorePlatform.POS) + datetime.now().strftime("%H%M%S")

        result = {
                "language": language,
                "internalOrderId": orderid,
                "vendorId": vendorId,
                "externalOrderId":orderid,
                "orderType": request.data.get("type"),
                "pickupTime": '',
                "arrivalTime": '',
                "deliveryIsAsap": 'true',
                "note": request.data.get('customerNote'),
                "tables": request.data.get('tables'),
                "items": [],
                "remake": False,
                "customerName": request.data.get('name') if request.data.get('name') else "",
                "status": "pending",
                "orderPointId": CorePlatform.POS,
                "orderPointName": CorePlatform.POS.label,
                "className":"POS",
                "customer": {
                    # "internalId": "1",
                    "fname": request.data.get('FirstName') if request.data.get('FirstName') else "Guest",
                    "lname": request.data.get('LastName') if request.data.get('LastName') else "",
                    "email": request.data.get('Email') if request.data.get('Email') else "",
                    "phno": request.data.get('Phone_Number') if request.data.get('Phone_Number') else "0",
                    "address1": request.data.get('address_line_1') if request.data.get('address_line_1') else "",
                    "address2": request.data.get('address_line_2') if request.data.get('address_line_2') else "",
                    "city": request.data.get('city') if request.data.get('city') else "",
                    "state": request.data.get('state') if request.data.get('state') else "",
                    "country": request.data.get('country') if request.data.get('country') else "",
                    "zip": request.data.get('zipcode') if request.data.get('zipcode') else "",
                    "vendorId": vendorId
                },
                "discount":{
                    "value":request.data.get('discount'),
                    "calType":2
                    },
                "payment": {
                    "tipAmount": request.data.get('tip',0.0),
                    "payConfirmation": request.data.get("payment_details").get("paymentKey") if request.data.get("payment_details").get("paymentKey") else "",
                    "payAmount": request.data.get("finalTotal",0.0),
                    "payType":PaymentType.get_payment_number(request.data.get("payment_details").get("paymentType")) if request.data.get("payment_details").get("paymentType") else 1,
                    "mode":PaymentType.get_payment_number(request.data.get("payment_details").get("paymentType")) if request.data.get("payment_details").get("paymentType") else 1,
                    "default": request.data.get("payment_details").get("paymentStatus") if request.data.get("payment_details").get("paymentStatus") else  False,
                    "platform": request.data.get("payment_details").get("platform") if request.data.get("payment_details").get("platform") else "N/A",
                    "custProfileId":"",
                    "custPayProfileId":"",
                    "payData": "",
                    "CardId":"NA",
                    "expDate":"",
                    "transcationId":request.data.get("payment_details").get("paymentKey"),
                    "lastDigits":"",
                    "billingZip":""
                },
                "tax": request.data.get("tax"),
                "subtotal": request.data.get("subtotal"),
                "finalTotal": request.data.get("finalTotal"),
                "is_wordpress": request.data.get("is_wordpress"),
                "points_redeemed": request.data.get("points_redeemed"),
                "points_redeemed_by": request.data.get("points_redeemed_by"),
            }
        
        # if request.data.get('promocodes'):
        #     discount=Order_Discount.objects.get(pk=request.data.get('promocodes')[0]['id'])
        #     result['discount']={
        #                     "discountCode": discount.discountCode,
        #                     "discountId": discount.plu,
        #                     "status": True,
        #                     "discountName": discount.discountName,
        #                     "discountCost": discount.value
        #                 }
        
        # +++++++++++ Item In order
        items = []

        for item in request.data["products"]:
                try:
                    corePrd = Product.objects.get(
                        pk=item['productId']
                        # , vendorId=vendorId
                        )
                    
                except Product.DoesNotExist:
                    return {API_Messages.ERROR:" Not found"}
                
                itemData = {
                    "plu": corePrd.productParentId.PLU if corePrd.productParentId != None else corePrd.PLU,
                    "sku": item.get("sku"),
                    "productName": corePrd.productName,
                    # Variation Id instead of name
                    "variantName": str(item["variation_id"]) if item.get("variation_id") else "txt",
                    "quantity": item["quantity"],
                    "subItems":  [
                           {
                        "plu": ProductModifier.objects.get(pk=subItem["modifierId"]).modifierPLU,
                        "name": subItem['name'],
                        "status":subItem["status"],
                        "group": subItemGrp['id']
                    } for subItemGrp in item['modifiersGroup'] for subItem in subItemGrp['modifiers']
                ] ,
                    "itemRemark": item["note"],  # Note Unavailable
                    "unit": "qty",  # Default
                    "modifiers": [
                           {
                        "plu": ProductModifier.objects.get(pk=subItem["modifierId"]).modifierPLU,
                        "name": subItem['name'],
                        "status":subItem["status"],
                        "quantity":subItem["quantity"],
                        "group": subItemGrp['id']
                    } for subItemGrp in item['modifiersGroup'] for subItem in subItemGrp['modifiers'] if subItem["status"]
                ]  # TODO
                }
                
                if corePrd.productParentId != None:
                    itemData["variant"] = {"plu": corePrd.PLU}

                #####++++++++ Modifiers
                items.append(itemData)

        result["items"] = items

        # +++++++++++ Item In order
        result["tip"] = request.data['tip'] 

        # return JsonResponse(result)
        tokenlist=KioskOrderData.objects.filter(date=datetime.today().date()).values_list('token')

        token=1 if len(tokenlist)==0 else max(tokenlist)[0] + 1

        # res=KomsEcom().openOrder(result)
        
        res = order_helper.OrderHelper.openOrder(result, vendorId)
        
        saveData = KiosK_create_order_serializer(data={'orderdata':str(result),'date':datetime.today().date(),'token':token})
        
        if saveData.is_valid():
            saveData.save()

            if Order.objects.filter(externalOrderld=orderid).exists():
                return JsonResponse({'token':token, "external_order_id":orderid})
            
            else:
                return JsonResponse({'token':token, "external_order_id":""})
        
        return JsonResponse({"msg": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        print(e)
        return JsonResponse({"msg": e}, status=status.HTTP_400_BAD_REQUEST)        


@api_view(['GET'])
def platform_list(request):
    vendor_id = request.GET.get('vendorId')
    language = request.GET.get('language', 'en')

    if vendor_id == None:
        return JsonResponse({"error": "Vendor Id cannot be empty"}, safe=False, status=status.HTTP_400_BAD_REQUEST)

    platform_details = []

    if language == "English":
        platform_details.append({
            "id": "",
            "name": "All"
        })

    else:
        platform_details.append({
            "id": "",
            "name": all_platform_locale["All"]
        })
    
    platforms = Platform.objects.filter(isActive=True, VendorId=vendor_id).exclude(Name="Inventory")

    platform_name = ""
    
    if platforms:
        for platform in platforms:
            if language == "English":
                platform_name = platform.Name
                
            else:
                platform_name = platform.Name_locale

            platform_details.append({
                "id": platform.pk,
                "name": platform_name
            })

    return JsonResponse({'platforms': platform_details}, status=status.HTTP_200_OK)

@api_view(["GET"])
def order_details(request):
    vendor_id = request.GET['vendorId']
    external_order_id = request.GET['id']
    platform_name = request.GET.get('platform')

    if vendor_id == None or vendor_id == '""' or vendor_id == '':
        return JsonResponse({"error": "Vendor ID cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    if external_order_id == None or external_order_id == '""' or external_order_id == '':
        return JsonResponse({"error": "External Order ID cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    if platform_name == None or platform_name == '""' or platform_name == '' or len(platform_name) == 0:
        return JsonResponse({"error": "Platform name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

    koms_order_status_list = []

    koms_order_status = KOMSOrderStatus.objects.all()

    for status_value in koms_order_status:
        name = status_value.get_status_display()

        if name!="CLOSED" or name!="CANCELED":
           koms_order_status_list.append(status_value.status)

        else:
            return JsonResponse({"error": "Closed or cancelled orders cannot be edited"}, status=status.HTTP_400_BAD_REQUEST)

    order_info = {}
    payment_details = {}
    customer_details = {}
    table_details = []
    platform_details = {}
    
    koms_order = KOMSOrder.objects.get(externalOrderId=external_order_id)

    if koms_order:
        koms_order_id = koms_order.pk

        if koms_order.order_status in koms_order_status_list:
            platforms = Platform.objects.filter(VendorId=vendor_id).values_list("Name", flat=True)

            platform_list = []

            for platform in platforms:
                platform_list.append(platform.lower())
            
            if str(platform_name).lower() in platform_list:
                order = Order.objects.get(externalOrderld=external_order_id)

            else:
                return JsonResponse({"error": "Invalid platform name"}, status=400)

            if order:
                order_id = order.pk

                if order.customerId == None:
                    customer_first_name = ""
                    customer_last_name = ""
                    customer_phone = ""
                    customer_email = ""
                    customer_loyalty_points_balance = 0
                    
                else:
                    customer_first_name = order.customerId.FirstName if order.customerId.FirstName else ""
                    customer_last_name = order.customerId.LastName if order.customerId.LastName else ""
                    customer_phone = order.customerId.Phone_Number if order.customerId.Phone_Number else ""
                    customer_email = order.customerId.Email if order.customerId.Email else ""
                    customer_loyalty_points_balance = order.customerId.loyalty_points_balance

                    customer_address = Address.objects.filter(customer=order.customerId.pk, type="shipping_address", is_selected=True).first()    
                    
                    if customer_address == None:
                        shipping_address = {
                            "address_line_1": "",
                            "address_line_2": "",
                            "city": "",
                            "state": "",
                            "country": "",
                            "zipcode": "",
                            "type": "",
                            "is_selected": ""
                        }

                    else:
                        shipping_address = {
                            "address_line_1": customer_address.address_line1 if customer_address.address_line1 else "",
                            "address_line_2": customer_address.address_line2 if customer_address.address_line2 else "",
                            "city": customer_address.city if customer_address.city else "",
                            "state": customer_address.state if customer_address.state else "",
                            "country": customer_address.country if customer_address.country else "",
                            "zipcode": customer_address.zipcode if customer_address.zipcode else "",
                            "type": customer_address.type,
                            "is_selected": customer_address.is_selected
                        }

                customer_details["FirstName"] = customer_first_name
                customer_details["LastName"] = customer_last_name
                customer_details["Phone_Number"] = customer_phone
                customer_details["Email"] = customer_email
                customer_details["loyalty_points_balance"] = customer_loyalty_points_balance
                customer_details["Shipping_Address"] = shipping_address

                payment = OrderPayment.objects.filter(orderId=order_id).first()

                payment_details["paymentId"] = payment.pk if payment else 0
                payment_details["paymentBy"] = payment.paymentBy if payment else ''
                payment_details["paymentKey"] = payment.paymentKey if payment else ''
                payment_details["amount_paid"] = payment.paid if payment else 0.0
                payment_details["paymentType"] = PaymentType.get_payment_str(payment.type) if payment else PaymentType.get_payment_str(PaymentType.CASH)
                payment_details["paymentStatus"] = payment.status if payment else False

                tables = Order_tables.objects.filter(orderId__externalOrderId=external_order_id)

                if tables:
                        for table in tables:
                            table_details.append({
                                "tableId": table.tableId.pk,
                                "tableNumber": table.tableId.tableNumber,
                                "waiterId": table.tableId.waiterId.pk,
                                "waiterName": table.tableId.waiterId.name,
                                "status": table.tableId.status,
                                "tableCapacity": table.tableId.tableCapacity,
                                "guestCount": table.tableId.guestCount
                            })

                order_items = defaultdict(list)

                koms_order_details = Order_content.objects.filter(orderId=koms_order_id)

                for order in koms_order_details:
                    try:
                        item = ProductCategoryJoint.objects.get(product__vendorId=vendor_id, product__PLU=order.SKU)
                    
                        image_list = []

                        images = ProductImage.objects.filter(product=item.product.pk)

                        for image in images:
                            image_list.append(image.url)

                    except Exception as e:
                        print("Error: ", e)
                        image_list = []

                    modifier_list = defaultdict(list)
                    modifier_group_list = defaultdict(list)
                    modifier_mapping = defaultdict(list)

                    modifiers = Order_modifer.objects.filter(contentID=order.pk, status="1")

                    if modifiers:    
                        for modifier in modifiers:
                            if modifier.group == None:
                                modifier_info = ProductModifier.objects.get(modifierSKU=modifier.SKU, vendorId=vendor_id)
                                modifier_group = ProductModifierAndModifierGroupJoint.objects.filter(modifier=modifier_info.pk).first()
                                modifier_mapping[modifier_group.modifierGroup.pk].append(modifier.pk)
                            else:
                                modifier_mapping[modifier.group].append(modifier.pk)
                    
                    for key, values in modifier_mapping.items():
                        for value in values:
                            modifier = Order_modifer.objects.get(pk=value)
                            modifier_info = ProductModifier.objects.get(modifierPLU=modifier.SKU, vendorId=vendor_id)

                            modifier_list[key].append({
                                'modifierId': modifier.pk,
                                'name': modifier_info.modifierName,
                                'plu': modifier_info.modifierPLU,
                                'sku': modifier_info.modifierSKU,
                                'quantity': modifier.quantity if modifier.quantity else 0,
                                'cost': modifier_info.modifierPrice,
                                'status': True,
                                'image': modifier_info.modifierImg
                            })

                        modifier_group_info = ProductModifierGroup.objects.get(pk=key, vendorId=vendor_id)

                        modifier_group_list[order_id].append({
                            "name": modifier_group_info.name,
                            "plu": modifier_group_info.PLU,
                            "min": modifier_group_info.min,
                            "max": modifier_group_info.max,
                            "id": modifier_group_info.pk,
                            "active": modifier_group_info.active,
                            "modifiers": modifier_list[key]
                        })

                    order_items[order_id].append({
                        "order_content_id": order.pk,
                        "productId": item.product.pk,
                        "quantity": order.quantity,
                        "plu": order.SKU,
                        "text": item.product.productName,
                        "isTaxable": item.product.taxable,
                        "imagePath": image_list[0] if len(image_list)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                        "images": image_list if len(image_list)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
                        "categoryName": item.category.categoryName,
                        "note": order.note if order.note else "",
                        "cost": Product.objects.get(PLU=order.SKU, vendorId=vendor_id).productPrice,
                        "status": int(order.status),
                        "modifiersGroup": modifier_group_list[order_id],
                    })
                    
                order_detail = OrderItem.objects.filter(orderId=order_id).first()

                total_points_redeemed = 0
                
                loyalty_program = LoyaltyProgramSettings.objects.filter(is_active=True, vendor=vendor_id).first()

                if loyalty_program:
                    loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=order_detail.orderId.customerId.pk, order=order_detail.orderId.pk)

                    if loyalty_points_redeem_history.exists():
                        total_points_redeemed = loyalty_points_redeem_history.aggregate(Sum('points_redeemed'))['points_redeemed__sum']

                        if not total_points_redeemed:
                            total_points_redeemed = 0

                order_info["staging_orderId"] = int(koms_order_id)
                order_info["core_orderId"] = order_id
                order_info["orderId"] = external_order_id
                order_info["customerNote"] = koms_order.order_note if koms_order.order_note else ""
                order_info["tax"] = order_detail.orderId.tax if order_detail.orderId.tax else 0.0
                order_info["discount"] = order_detail.orderId.discount if order_detail.orderId.discount else 0.0
                order_info["delivery_charge"] = order_detail.orderId.delivery_charge
                order_info["subtotal"] = order_detail.orderId.subtotal
                order_info["total_points_redeemed"] = total_points_redeemed
                order_info["finalTotal"] = order_detail.orderId.TotalAmount
                order_info["order_datetime"] = order_detail.orderId.OrderDate
                order_info["arrival_time"] = order_detail.orderId.arrivalTime
                order_info["type"] = koms_order.order_type
                order_info["products"] = order_items[order_id]

                if order_detail.orderId.platform == None:
                    platform_id = 0
                    platform_name = ""

                else:
                    platform_id = order_detail.orderId.platform.pk
                    platform_name = order_detail.orderId.platform.Name

                platform_details["id"] = platform_id
                platform_details["name"] = platform_name

                return JsonResponse({
                    "payment_details": payment_details,
                    "customer_details": customer_details,
                    "table_details": table_details,
                    "platform_details": platform_details,
                    "order_info": order_info
                })
            
            else:
                return JsonResponse({"error": "Order details not found"}, status=400)
            
        else:
            return JsonResponse({"error": "Closed or cancelled orders cannot be edited"}, status=400)  
        
    else:
        return JsonResponse({"error": "Order details not found"}, status=400)


@api_view(['POST'])
def updatePaymentDetails(request):
    data = request.data

    vendorId = request.GET.get('vendorId', None)
    language = request.GET.get('language', 'en')

    if vendorId is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendorId = int(vendorId)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendorId).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    order = KOMSOrder.objects.get(externalOrderId=data['orderid'])

    oldStatus = order.order_status

    if str(data['platform']).lower() == 'woocommerce':
        coreOrder = Order.objects.get(pk=order.externalOrderId)
    
    else:
        coreOrder = Order.objects.filter(externalOrderld=order.externalOrderId, vendorId=vendorId).last()
        
    payment = OrderPayment.objects.filter(orderId=coreOrder.pk).last()
    
    if payment:    
        print(payment.platform)
        payment.paymentBy=data['payment']['paymentBy']
        payment.paymentKey=data['payment']['paymentKey']
        payment.type=data['payment']['type']
        payment.status=True
        payment.platform=data['payment']['platform']

        payment.save()

    else:
        OrderPayment.objects.create(
            orderId=coreOrder,
            paymentBy=data['payment']['paymentBy'],
            paymentKey=data['payment']['paymentKey'],
            paid=coreOrder.TotalAmount,
            due=0,
            tip=0,
            type=data['payment']['type'],
            status=True,
            platform=data['payment']['platform']
        )
    
    if coreOrder.orderType == 3:
        order.order_status=10 # CLOSE order
        order.save()
        
        coreOrder.Status=2                    # this is just a temporary fix to update 
        coreOrder.save()                      # core order status this needs to be changed by updateCoreOrder function

        tables=Order_tables.objects.filter(orderId=order)
        
        for table in tables:
            table.tableId.status = 1 # EMPTY TABLE
            table.tableId.guestCount = 0
            table.tableId.save()

            res=getTableData(hotelTable=table.tableId,vendorId=vendorId)

            webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name="WOMS"+str(table.tableId.waiterId.pk if table.tableId.waiterId else 0)+"------"+str(vendorId),username="CORE",)#update table for new waiter
            webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name="WOMS"+"POS------"+str(vendorId),username="CORE",)#update table for new waiter
            
            for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendorId):
                # webSocketPush({"result":res,"UPDATE": "UPDATE"},WOMS+str(i.pk)+"-"+filter+"-"+search+"--","CORE",)
                webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name="WOMS"+str(i.pk)+"------"+str(vendorId),username="CORE",)

    elif ((coreOrder.orderType == 1) or (coreOrder.orderType == 2)) and (order.order_status == 3):
        order.order_status=10
        order.save()
        
        coreOrder.Status=2
        coreOrder.save()
    
    webSocketPush(message={"id": order.pk,"orderId": order.externalOrderId,"UPDATE": "REMOVE",},room_name=str(vendorId)+'-'+str(oldStatus),username="CORE",)  # WheelMan order remove order from old status
    # processStation(oldStatus=str(oldStatus),currentStatus=str(orderStatus),orderId=content.orderId.pk,station=content.stationId,vendorId=vendorId)
    allStationWiseRemove(id=order.pk,old=str(oldStatus),current=str(oldStatus),vendorId=vendorId)
    allStationWiseSingle(id=order.pk,vendorId=vendorId)
    waiteOrderUpdate(orderid=order.pk, language=language, vendorId=vendorId)
    allStationWiseCategory(vendorId=vendorId) 

    return JsonResponse({})


@api_view(["POST"])
def update_order_koms(request):
    print(request.data)

    vendor_id = request.GET['vendorId']
    external_order_id = request.GET['id']
    language = request.GET.get("language", "English")

    if vendor_id == None or vendor_id == '""' or vendor_id == '':
        return JsonResponse({"error": "Vendor ID cannot be empty"}, status=400)
    
    if external_order_id == None or external_order_id == '""' or external_order_id == '':
        return JsonResponse({"error": "External Order ID cannot be empty"}, status=400)

    data = request.data

    if data:
        try:
            core_id = data['order_info'].get('core_orderId')

            if core_id:
                core_order = Order.objects.get(pk=core_id)

                if core_order:
                    core_order.Notes = data['order_info'].get('customerNote', "")
                    core_order.subtotal = data['order_info'].get('subtotal')
                    core_order.tax = data['order_info'].get('tax')
                    core_order.discount = data['order_info'].get('discount')
                    core_order.delivery_charge = data['order_info'].get('delivery_charge')
                    core_order.TotalAmount = data['order_info'].get('finalTotal')
                    core_order.save()
            
            new_data = []

            for product in data["order_info"]["products"]:
                if product.get("order_content_id") == None:
                    pass
                
                else:
                    order_detail = {
                        "order_content_id": product["order_content_id"],
                        "name": product["text"],
                        "quantity": product["quantity"],
                        "note": product["note"],
                        "SKU": product["plu"],
                        "categoryName": product["categoryName"],
                        "modifiers": []
                    }

                    if product.get("modifiersGroup"):
                        for modifier_group in product["modifiersGroup"]:
                            for modifier in modifier_group["modifiers"]:
                                if modifier["status"] == True:
                                    mod = {
                                        "order_modifier_id":modifier["order_modifier_id"],
                                        "name": modifier["name"],
                                        "SKU": modifier["plu"],
                                        "quantity": modifier["quantity"]
                                    }
                                
                                    order_detail["modifiers"].append(mod)

                    new_data.append(order_detail)

            modifier_details = defaultdict(list)
            old_data = []

            koms_order = KOMSOrder.objects.get(externalOrderId=external_order_id, vendorId=vendor_id)

            old_status_of_order = koms_order.order_status
            
            koms_order_id = koms_order.pk

            koms_order.order_note = data.get('order_info').get('customerNote')
            koms_order.save()

            koms_order_content = Order_content.objects.filter(orderId=koms_order_id)

            for order in koms_order_content:
                koms_order_modifiers = Order_modifer.objects.filter(contentID=order.pk)

                for modifier in koms_order_modifiers:
                    modifier_details[order.pk].append({
                        "order_modifier_id": modifier.pk,
                        "name": modifier.name,
                        "quantityStatus": modifier.quantityStatus,
                        "SKU": modifier.SKU,
                        "status": modifier.status,
                        "quantity": modifier.quantity,
                        "isEdited": modifier.isEdited
                    })

                old_data.append({
                    "order_content_id": order.pk,
                    "name": order.name,
                    "quantity": order.quantity,
                    "quantityStatus": order.quantityStatus,
                    "note": order.note,
                    "SKU": order.SKU,
                    "categoryName": order.categoryName,
                    "stationId": order.stationId.pk,
                    "status": order.status,
                    "isEdited": order.isEdited,
                    "modifiers": modifier_details[order.pk]
                })

            old_products = {}
            new_products = {}
            deleted_products = set()

            for product in old_data:
                order_content_id = product.get('order_content_id')
                sku = product.get('SKU')

                old_products[(order_content_id, sku)] = []

            for product in new_data:
                order_content_id = product.get('order_content_id')
                sku = product.get('SKU')

                new_products[(order_content_id, sku)] = []

            for key in old_products:
                    if key in new_products:
                        if old_products[key] == new_products[key]:
                            pass

                    else:
                        deleted_products.add(key)
            
            for key in deleted_products:
                product = Order_content.objects.get(pk=key[0], SKU=key[1])
                product.quantityStatus = 1
                product.status = 5

                modifiers = Order_modifer.objects.filter(contentID=product.pk).update(quantityStatus=0, status=5) # quantityStatus=0 is deleted

                product.save()

            for item1 in old_data:
                for item2 in new_data:
                    if item1["SKU"] == item2["SKU"]:
                        if item1["quantity"] != item2["quantity"]:
                            product = Order_content.objects.get(pk=item2["order_content_id"], SKU=item2["SKU"])
                            product.quantity = item2["quantity"]
                            contdata={
                                "contentID":product.pk,
                                    "update_time":datetime.today().strftime("20%y-%m-%d"),
                                    "quantity":item1["quantity"],
                                    "unit":"qty"}
                            cont=Content_history_serializer(data=contdata, partial=True)
                            if cont.is_valid():
                                cont.save()
                                print("history noted")
                            print(cont.errors)
                            product.isEdited = True
                            product.save()

                        if item1["note"] != item2["note"]:
                            product = Order_content.objects.get(pk=item2["order_content_id"], SKU=item2["SKU"])
                            product.note = item2["note"]
                            product.isEdited = True
                            product.save()

            for product in data["order_info"]["products"]:
                if product.get("order_content_id") == None:
                    koms_order_details = KOMSOrder.objects.get(pk=data["order_info"].get("staging_orderId"))

                    if koms_order_details.order_status == 1:
                        order_status = 1
                    else:
                        order_status = 8

                    product_category_joint = ProductCategoryJoint.objects.filter(
                        product__PLU=product["plu"], product__vendorId=vendor_id, vendorId=vendor_id
                    ).first()
                    
                    item = Order_content.objects.create(
                        orderId = koms_order_details,
                        name = product["text"],
                        quantity = product["quantity"],
                        quantityStatus = 0,
                        unit = "qty",
                        note = product["note"],
                        SKU = product["plu"],
                        tag = 1,
                        categoryName = product["categoryName"],
                        stationId = product_category_joint.category.categoryStation.pk if product_category_joint else Station.objects.filter(vendorId=vendor_id).first(),
                        status = order_status,
                        isrecall = False,
                        isEdited = 0,
                    )

                    if koms_order_details.order_status != 1:
                        koms_order_details.order_status = 8
                        koms_order_details.save()

                    modifiers_group = product.get('modifiersGroup', [])

                    if modifiers_group:
                        for mod_group in modifiers_group:
                            modifiers = mod_group.get('modifiers', [])

                            for modifier in modifiers:
                                if modifier["status"] == True:
                                    item_modifier = Order_modifer.objects.create(
                                        contentID = Order_content.objects.get(pk=item.pk),
                                        name = modifier.get('name', ""),
                                        quantityStatus = 1, # not deleted
                                        unit = "qty",
                                        note = modifier.get('note', ""),
                                        SKU = modifier.get('plu'),
                                        status = 1,
                                        quantity = modifier.get('quantity', 0),
                                        isEdited = 0,
                                        group = mod_group.get('id')
                                    )

                                    item_modifier.save()

            platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
            
            if platform:
                sync_order_content_with_inventory(core_id, vendor_id)
            
            koms_order = KOMSOrder.objects.get(externalOrderId=external_order_id, vendorId=vendor_id)

            new_status_of_order = koms_order.order_status
            
            webSocketPush(message={"id": koms_order_id,"orderId": koms_order.externalOrderId,"UPDATE": "REMOVE",},room_name=str(vendor_id)+'-'+str(old_status_of_order),username="CORE",) 
            allStationWiseRemove(id=koms_order_id, old=str(old_status_of_order), current=str(new_status_of_order), vendorId=vendor_id)
            allStationWiseSingle(id=koms_order_id,vendorId=vendor_id)
            waiteOrderUpdate(orderid=koms_order_id, language=language, vendorId=vendor_id)
            allStationWiseCategory(vendorId=vendor_id)
            
            return JsonResponse({"message": "Success"}, status=200)

        except Exception as e:
            print("POS-update_order_koms_api: ", e)
            return JsonResponse({"error": e}, status=400)

    else:
        return JsonResponse({"error": "JSON data cannot be empty"}, status=400)


@api_view(["POST"])
def  orderList(request):
    data=request.data

    data=order_data(
        vendor_id=data.get("vendor_id"),
        page_number=data.get("page_number"),
        search=data.get("search"),
        order_status=data.get("order_status"),
        order_type=data.get("order_type"),
        platform=data.get("platform"),
        s_date=data.get("s_date"),
        e_date=data.get("e_date"),
        is_dashboard = data.get("is_dashboard"),
    )

    return JsonResponse(data)


@api_view(["POST"])
def storetime(request):
    vendor_id = request.GET.get("vendorId")
    pos_set = POS_Settings.objects.filter(VendorId=vendor_id)
    if request.data.get("store") == "":
        return Response(data={"store_status":pos_set.first().store_status},status=status.HTTP_200_OK)
    pos_set.update(store_status=request.data.get("store"))
    woocommerce_platform = Platform.objects.filter(
        VendorId=vendor_id,
        corePlatformType=CorePlatform.WOOCOMMERCE,
        isActive=True
    ).first()

    if woocommerce_platform:
        payload = {
                    "data": 
                    {   
                        "store_toggle":"1" if request.data.get("store") else "0"
                    }
                }
        
        url = woocommerce_platform.baseUrl + "?rest_route=/storetime/v1/slot/update"

        wooResponse = requests.request(
            "POST",
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )

        if wooResponse.status_code == 200:
           return Response(data={"store_status":request.data.get("store")},status=status.HTTP_200_OK)
        
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
    return Response(data={"store_status":request.data.get("store")},status=status.HTTP_200_OK)



@api_view(["POST"])
def order_payment(request):
    body_data = json.loads(request.body)

    externalRefNumber = body_data.get('order_id')
    amount = body_data.get('amount')
    customerMobileNumber = body_data.get('customer_mobile', "")
    customerEmail = body_data.get('customer_email', "")
    customerName = body_data.get('customer_name', "")
    vendor_id = body_data.get('vendor_id')

    if vendor_id == 1:
        data = {
            "appKey": "b5655725-b020-45b5-91e1-4f95965c0496",
            "username": "1212100119",
            "amount": amount,
            "externalRefNumber": externalRefNumber,
            "description": f"payment for OrderID: {externalRefNumber}",
            "customerMobileNumber": customerMobileNumber,
            "customerEmail": customerEmail,
            "customerName": customerName,
            "pushTo": {
                "deviceId": "1491961756|ezetap_android"
            },
            "mode": "ALL",
            "orgCode": "CONSOCIATESOLUTIONS"
        }

        ezetap_url = "https://demo.ezetap.com/api/3.0/p2padapter/pay"

        response = requests.post(ezetap_url, json=data)
        # response = request('POST', ezetap_url, params=data)

        if response.status_code == 200:
            ezetap_response = response.json()
            return JsonResponse({'data': ezetap_response}, status=200)
        else:
            ezetap_response = response.json()
            return JsonResponse({'data': ezetap_response}, status=400)
        
    else:
        return JsonResponse({'data': 'Not a valid vendor ID'}, status=400)
   


def excel_upload(request):
    if request.method == "POST":
        if 'excel_file' not in request.FILES:
            messages.error(request, "No file uploaded")
            return JsonResponse({"error": "No file uploaded"}, status=400)
    
        vendor_id = request.POST.get("vendor")

        if vendor_id == None:
            messages.error(request, "Vendor ID empty")
            return JsonResponse({"error": "Vendor ID cannot be empty"}, status=400)
        
        vendor = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor:
            messages.error(request, "Vendor does not exist")
            return JsonResponse({"error": "Vendor does not exist"}, status=400)

        uploaded_file = request.FILES['excel_file']

        directory = os.path.join(settings.MEDIA_ROOT, 'Product Details Excel')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"{uploaded_file.name.split('.')[0]}_Vendor{vendor_id}.{uploaded_file.name.split('.')[-1]}"

        relative_file_path = os.path.join('Product Details Excel', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        print(file_path)

        with default_storage.open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        file_status, response = process_excel(file_path, 'Sheet1', vendor_id)

        # print(file_status, failed_file_path)

        vendors = Vendor.objects.all()
        
        if (file_status == 1) and (response == None):
            messages.success(request, "Excel file uploaded successfully")
            return render(request, "adminlte/upload_products.html", {"vendors":vendors})

        elif (file_status == 1) and (response != None):
            # uploaded_file_path = os.path.join(request.build_absolute_uri('/'), f'media/{relative_file_path}')
            error_file_path = response

            messages.success(request, "Excel file uploaded successfully")
            messages.warning(request, "Check the Error file")

            return render(request, "adminlte/upload_products.html", {"vendors":vendors, "failed_file_path": error_file_path, "host": request.build_absolute_uri('/')})
        
        else:
            messages.error(request, "Excel file upload failed")
            messages.warning(request, f"{response}")
            return render( request, "adminlte/upload_products.html", {"vendors":vendors})
    else:
        vendors = Vendor.objects.all()
        return render( request, "adminlte/upload_products.html", {"vendors":vendors})
        


@api_view(["POST"])
def excel_download_for_dashboard(request):
    json_data = json.loads(request.body)

    vendor_id = json_data.get("vendor_id")
    start_date = json_data.get("start_date")
    end_date = json_data.get("end_date")
    platform_id = json_data.get("platform_id", "All")
    order_type = json_data.get("order_type", "All")
    order_status = json_data.get("order_status", "All")
    language = json_data.get("language", "English")

    if (vendor_id == None) or (vendor_id == ""):
        return JsonResponse({"error": "Vendor ID cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    if (start_date == None) or (start_date == ""):
        return JsonResponse({"error": "Start date cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    if (end_date == None) or (end_date == ""):
        return JsonResponse({"error": "End date cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    if platform_id == "":
        platform_id = "All"

    if order_type == "":
        order_type = "All"

    if order_status == "":
        order_status = "All"

    if language == "":
        language = "English"
    
    if check_key_exists(language, "order_type", order_type) == False:
        return JsonResponse({"error": "Order Type does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    
    if check_key_exists(language, "koms_order_status", order_status) == False:
        return JsonResponse({"error": "Order Status does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    
    order_type_parameter = get_key_value(language, "order_type", order_type)
    order_status_parameter = get_key_value(language, "koms_order_status", order_status)

    if platform_id == "All":
        platform_parameter = "All"
        
    else:
        platform_parameter = Platform.objects.filter(pk=platform_id, VendorId=vendor_id).first()
        
        if platform_parameter:
            platform_parameter = platform_parameter.Name

        else:
            return JsonResponse({"error": "Platform does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    
    start_date_parameter = datetime.strptime(str(start_date), '%Y-%m-%d').date()
    end_date_parameter = datetime.strptime(str(end_date), '%Y-%m-%d').date()

    start_date_parameter = start_date_parameter.strftime('%d-%m-%Y')
    end_date_parameter = end_date_parameter.strftime('%d-%m-%Y')
    
    vendor_id = int(vendor_id)

    start_date = datetime.strptime(str(start_date) + " 00:00:00.000000", '%Y-%m-%d %H:%M:%S.%f')
    end_date = datetime.strptime(str(end_date) + " 23:59:59.000000", '%Y-%m-%d %H:%M:%S.%f')
    
    order_details = {}

    koms_order_data = KOMSOrder.objects.filter(arrival_time__range=(start_date, end_date), vendorId=vendor_id)

    if (platform_id == "All") or (platform_id == ""):
        pass

    else:
        platform_id = int(platform_id)

        platform_info = Platform.objects.filter(pk=platform_id, VendorId=vendor_id).first()

        if platform_info:
            external_order_ids = list(koms_order_data.values_list('externalOrderId', flat=True))

            order_data = Order.objects.filter(externalOrderld__in=external_order_ids)
            order_data = order_data.filter(platform=platform_id)
            external_order_ids = list(order_data.values_list('externalOrderld', flat=True))
            
            koms_order_data = KOMSOrder.objects.filter(externalOrderId__in=external_order_ids)
        
        else:
            return JsonResponse({"error": "Platform not found"}, status=status.HTTP_400_BAD_REQUEST)
        
    if (order_type == "All") or (order_type == ""):
        pass
    
    else:
        order_type = int(order_type)
        koms_order_data = koms_order_data.filter(order_type=order_type)

    if (order_status == "All") or (order_status == ""):
        pass
    
    else:
        order_status = int(order_status)
        koms_order_data = koms_order_data.filter(order_status=order_status)

    external_order_ids = list(koms_order_data.values_list('externalOrderId', flat=True))

    order_ids = list(KOMSOrder.objects.filter(externalOrderId__in=external_order_ids).values_list('pk', flat=True))

    order_content = Order_content.objects.filter(orderId__in = order_ids)

    try:
        with transaction.atomic():    
            for content in order_content:
                koms_orders = KOMSOrder.objects.filter(pk=content.orderId.pk, vendorId=vendor_id)

                for order in koms_orders:
                    order_id = order.externalOrderId
                    
                    order_detail = Order.objects.filter(Q(externalOrderld=str(order.externalOrderId))| Q(pk=str(order.externalOrderId))).last()
                    
                    payment_detail = OrderPayment.objects.filter(orderId=order_detail.pk).last()

                    if order_detail:
                        order_time = order_detail.arrivalTime.astimezone(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)

                        order_type = get_key_value(language, "order_type", order_detail.orderType)

                        order_status = get_key_value(language, "koms_order_status", order.order_status)
                        
                        if payment_detail:
                            if payment_detail.status == True:
                                payment_status = get_key_value(language, "payment_status", "True")
                            
                            else:
                                payment_status = get_key_value(language, "payment_status", "False")
                            
                            amount_paid = payment_detail.paid
                            transaction_id = payment_detail.paymentKey
                            payment_type = get_key_value(language, "payment_type", payment_detail.type)
                            
                        else:
                            transaction_id = ""
                            payment_status = get_key_value(language, "payment_status", "Unknown")
                            payment_type = ""
                            
                        platform_name = order_detail.platform.Name

                        order_details[order_id] = {
                            "order_id": order_id,
                            "platform_name": platform_name,
                            "amount_paid": amount_paid,
                            "order_type": order_type,
                            "order_status": order_status,
                            "order_time": order_time,
                            "payment_type": payment_type,
                            "payment_status": payment_status,
                            "transaction_id": transaction_id,
                        }
                        
                    else:
                        response_data = {"error": f"Order details not found for external order ID {order_id}"}
                        print(f"Order details not found for external order ID {order_id}")
                        return JsonResponse(response_data, status=500)

    except Exception as e:
        print(e)
        return JsonResponse({"error": str(e)}, status=500)

    # order_details = OrderedDict(sorted(order_details.items(), key=lambda x: (x[1]["order_time"], int(x[0])) if x[1]["order_time"] else ("", int(x[0]))))

    new_order_details = OrderedDict()
    sorted_items = []

    for key, value in order_details.items():
        order_time = value.get("order_time", "")
        sorted_items.append((order_time, int(key)))

    sorted_items.sort()

    for order_time, order_id in sorted_items:
        new_order_details[order_id] = order_details[order_id]

    order_details = new_order_details
    
    order_count = len(order_details)
    
    total_amount_paid = 0.0

    subtotal_sum, discount_sum = Order.objects.filter(
        OrderDate__date__range=(start_date, end_date),
        orderpayment__status=True,
        vendorId=vendor_id
    ).exclude(Status=OrderStatus.get_order_status_value('CANCELED')).aggregate(subtotal_sum=Sum('subtotal'), discount_sum=Sum('discount')).values()

    subtotal_sum = subtotal_sum or 0.0
    discount_sum = discount_sum or 0.0
    
    total_amount_paid = "{:.2f}".format(subtotal_sum - discount_sum)

    # Create a new Excel workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    
    sheet.append(['Start Date', f'{start_date_parameter}', '', '', '', '', '', '', ''])
    sheet.append(['End Date', f'{end_date_parameter}', '', '', '', '', '', '', ''])
    sheet.append(['Platform', f'{platform_parameter}', '', '', '', '', '', '', ''])
    sheet.append(['Order Type', f'{order_type_parameter}', '', '', '', '', '', '', ''])
    sheet.append(['Order Status', f'{order_status_parameter}', '', '', '', '', '', '', ''])
    sheet.append(['', '', '', '', '', '', '', '', ''])

    # Write headers
    sheet.append(['Order ID', 'Platform', 'Amount', 'Order Type', 'Order Status', 'Order Time', 'Payment Type', 'Payment Status', 'Transaction ID'])

    for order_id, details in order_details.items():
        sheet.append([
            details["order_id"],
            details["platform_name"],
            details["amount_paid"],
            details["order_type"],
            details["order_status"],
            details["order_time"].strftime('%d-%m-%Y %I:%M:%S %p') if details["order_time"] else "",
            details["payment_type"],
            details["payment_status"],
            details["transaction_id"],
        ])
    
    sheet.append([f'Total orders = {order_count}', '', f'Total revenue = {total_amount_paid}', '', '', '', '', '', ''])
    
    directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
    os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

    file_name = f"Order_data_Vendor{vendor_id}.xlsx"

    relative_file_path = os.path.join('Excel Downloads', file_name)

    file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

    workbook.save(file_path)

    print(f"Excel file '{file_name}' has been created.")
    
    response = "/media/" + relative_file_path
    
    return HttpResponse(response, status=200)


@api_view(["POST"])
def delete_excel(request):
    json_data = json.loads(request.body)

    path = json_data.get("path")

    if not path:
        return JsonResponse({"error": "File path empty"}, status=400)

    absolute_file_path = os.path.join(settings.MEDIA_ROOT, path.lstrip("/media/"))

    try:
        if os.path.exists(absolute_file_path):
            os.remove(absolute_file_path)
            return JsonResponse({"message": "File deleted"}, status=200)
        else:
            return JsonResponse({"error": "File not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": f"Failed to delete file: {str(e)}"}, status=500)


def get_pos_user(request):
    page = int(request.GET.get('pageIndex', 1)) # pageIndex variable should not be renamed as it is required for jsGrid plugin
    page_size = int(request.GET.get('pageSize', 10)) # pageSize variable should not be renamed as it is required for jsGrid plugin

    vendors = POSUser.objects.all().order_by('pk')

    paginated_data = []
    
    paginator = Paginator(vendors, page_size)
    page = paginator.get_page(page)

    for data in page:
        paginated_data.append({
            "id": data.pk,
            "username": data.username,
            "password": data.password,
            "name": data.name,
            "email": data.email,
            "vendor": data.vendor.pk,
            "is_active": data.is_active
        })

    return JsonResponse({
        "data": paginated_data, # data key should not be renamed as it is required for jsGrid plugin
        "itemsCount": paginator.count # itemsCount key should not be renamed as it is required for jsGrid plugin
    })

def create_pos_user(request):
    vendors = Vendor.objects.all()

    if request.method == "POST":
        form = PosUserForm(request.POST or None)

        if form.is_valid():
            form.save()

            messages.success(request, "POS User Created!")

            return redirect("/pos/pos_user/")
        else:
            messages.warning(request, "Please fill all the fields!")

            form = PosUserForm()

            return render( request, "adminlte/pos_user.html", {"form": form, "vendors":vendors})

    form = PosUserForm(None)

    return render(request, "adminlte/pos_user.html", {"form": form, "vendors":vendors})


def update_pos_user(request, pos_user_id):
    pos_user = get_object_or_404(POSUser, id=pos_user_id)

    if request.method == "POST":
        form = PosUserForm(request.POST, instance=pos_user)

        if form.is_valid():
            pos_user.save()

            serialized_data = {}

            serialized_data["id"] = pos_user.pk
            serialized_data["username"] = pos_user.username
            serialized_data["password"] = pos_user.password
            serialized_data["name"] = pos_user.name
            serialized_data["email"] = pos_user.email
            serialized_data["vendor"] = pos_user.vendor.pk
            serialized_data["is_active"] = pos_user.is_active

            messages.success(request, "POS User updated successfully")
            return JsonResponse(serialized_data, content_type="application/json", safe=False)
        
        else:
            print(form.errors)
            messages.error(request, "Please fill the details correctly!")

            return JsonResponse({'error': 'Please fill the details correctly'}, status=400, content_type="application/json")

    else:
        messages.error(request, "Invalid request method!")

        return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")


def delete_pos_user(request, pos_user_id):
    try:
        if request.method == "POST":
            pos_user = POSUser.objects.filter(pk=pos_user_id)

            pos_user.delete()

            return JsonResponse({"message": "POS User deleted successfully"}, content_type="application/json", status=204)

        else:
            messages.error(request, "Invalid request method!")
            return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")
    except Exception as e:
        print(e)
        return JsonResponse({"message": "Something went wrong!"}, content_type="application/json")

@api_view(['GET'])
def get_store_timings(request):
    vendor = request.GET.get("vendorId")

    data = StoreTiming.objects.filter(vendor=vendor)

    slot = data.filter(is_active=True , day=datetime.now().strftime("%A")).first()

    serialized = StoreTImingSerializer(data, many=True)


    store_status = POS_Settings.objects.filter(VendorId=vendor).first()

    store_status_value = store_status.store_status

    if store_status_value == False:
        store_status_final = False

    if not serialized.data:
        return Response({
            "store_status": store_status_value,
            "store_timing": []
        })
    else:
        if store_status.store_status==False:
            store_status_final =  False 
        elif slot==None:
            store_status_final = True 
        elif  (slot.open_time < datetime.now().time() < slot.close_time) and not slot.is_holiday:
            store_status_final = True  
        else:
            store_status_final =  False

    return Response({
        "store_status": store_status_final,
        "store_timing": serialized.data
    })

@api_view(['POST'])
def set_store_timings(request):
    vendor = request.GET.get("vendorId")

    body_data = request.data

    body_data['platform'] = None

    woocommerce_platform = Platform.objects.filter(
        VendorId=vendor,
        corePlatformType=CorePlatform.WOOCOMMERCE,
        isActive=True
    ).first()

    if woocommerce_platform:
        body_data['platform'] = woocommerce_platform.pk

    serialized = StoreTImingSerializer(data=body_data)

    # update store_timings
    if request.GET.get("id"):
        data = StoreTiming.objects.get(pk=request.GET.get("id"))
        serialized = StoreTImingSerializer(instance=data, data=body_data)

    if serialized.is_valid():
        slot=serialized.save()

        # if woocommerce_platform:
        #     wooResponse = WooCommerce.set_store_timings(vendorId=vendor, day=slot)
        #     print(wooResponse)

        return Response(serialized.data, status=status.HTTP_200_OK)
    
    print("error :", serialized._errors)
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST','GET','DELETE'])
def delete_store_timings(request):
    try:
        data = StoreTiming.objects.get(pk=request.GET.get("id"))
        # wooResponse = WooCommerce.delete_store_timings(vendorId=data.vendor,day=data)
        data.delete()
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_200_OK)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_class = ProductCategoryFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    pagination_class = CustomPagination 

    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            queryset = ProductCategory.objects.filter(vendorId=vendor_id)
        
        else:
            queryset = ProductCategory.objects.none()
        
        queryset = queryset.order_by('-pk')

        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # name_query = request.query_params.get('name', None)
        name_query = request.GET.get('categoryName', None)
        
        if name_query:
            queryset = queryset.filter(categoryName__icontains=name_query)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        try:
            plu = request.data.get('categoryPLU')
            vendor_id = request.data.get('vendorId')

            existing_category = ProductCategory.objects.filter(categoryPLU=plu, vendorId=vendor_id).first()

            if existing_category:
                return Response({'error': 'Category with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                if inventory_platform:
                    sync_status = single_category_sync_with_odoo(serializer.instance)
                        
                    if sync_status == 0:
                        notify(type=3, msg='0', desc='Category did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Category synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                headers = self.get_success_headers(serializer.data)

                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                partial = kwargs.pop('partial', False)
                instance = self.get_object()

                new_plu = request.data.get('categoryPLU')

                if new_plu != instance.categoryPLU:
                    existing_category = ProductCategory.objects.filter(categoryPLU=new_plu, vendorId=instance.vendorId).first()

                    if existing_category:
                        return Response({'error': 'Category with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)

                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)

                vendor_id = serializer.instance.vendorId.pk
                
                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                if inventory_platform:
                    sync_status = single_category_sync_with_odoo(serializer.instance)
                        
                    if sync_status == 0:
                        notify(type=3, msg='0', desc='Category did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Category synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                instance = self.get_object()

                vendor_id = instance.vendorId.pk
                
                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

                if inventory_platform:
                    delete_status, error_message, request_data = delete_category_in_odoo(inventory_platform.baseUrl, instance.categoryPLU, vendor_id)
                
                    if delete_status == 0:
                        notify(type=3, msg='0', desc='Category did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Category synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                self.perform_destroy(instance)
                return Response(status=status.HTTP_204_NO_CONTENT)
                    
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET",])
def get_products(request):
    vendor_id = request.GET.get("vendorId", None)
    product_name = request.GET.get("productName", None)
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)
    language = request.GET.get("language", "English")

    if vendor_id is None:
        return Response("Vendor ID empty", status=404)
    
    vendor_id = int(vendor_id)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_404_NOT_FOUND)

    if product_name:
        if language == "English":
            products = Product.objects.filter(productName__icontains=product_name, vendorId=vendor_id).order_by('-pk')

        else:
            products = Product.objects.filter(productName_locale__icontains=product_name, vendorId=vendor_id).order_by('-pk')
    
    else:
        products = Product.objects.filter(vendorId=vendor_id).order_by('-pk')

    if products:
        paginator = Paginator(products, page_size)

        try:
            paginated_products = paginator.page(page_number)
        
        except PageNotAnInteger:
            paginated_products = paginator.page(1)
        
        except EmptyPage:
            paginated_products = paginator.page(paginator.num_pages)

        response_data = []
        current_page = paginated_products.number
        total_pages = paginator.num_pages

        for single_product in paginated_products:
            product_info = get_product_data(single_product, vendor_id)

            response_data.append(product_info)

        response = {
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": int(page_size),
            "results": response_data,
        }

        return JsonResponse(response, status=200)

    else:
        response = {
            "total_pages": 0,
            "current_page": 0,
            "page_size": 0,
            "results": [],
        }

        return JsonResponse(response, status=200)   


@api_view(["POST"])
def create_product(request):
    plu = request.data.get('PLU')
    vendor_id = request.data.get('vendorId')

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    existing_product = Product.objects.filter(PLU=plu, vendorId=vendor_id).first()

    if existing_product:
        return Response({'error': 'Product with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    product_serializer = ProductSerializer(data=request.data)

    if product_serializer.is_valid():
        categories_data = []
        images_data = []
        modifier_groups_data = []

        image_path_keys = []
        is_image_selected_keys = []

        with transaction.atomic():
            product = product_serializer.save()

            vendor_id = int(request.data.get('vendorId'))

            for key, value in request.data.items():
                if key.startswith('categories-'):
                    categories_data.append({'category': int(value), 'product': product.pk, 'vendorId': vendor_id})
                
                elif key.startswith('modifier_groups-'):
                    modifier_groups_data.append({'modifierGroup': int(value), 'product': product.pk, 'vendorId': vendor_id})

            for key in request.data.keys():
                if key.startswith('images-'):
                    if key.endswith('-image'):
                        image_path_keys.append(key)
                    
                    if key.endswith('-is_image_selected'):
                        is_image_selected_keys.append(key)

            if len(image_path_keys) == len(is_image_selected_keys):
                for iterator in range(len(image_path_keys)):
                    image_path = request.data.get(image_path_keys[iterator], None)
                    is_image_selected = request.data.get(is_image_selected_keys[iterator], None)

                    if (image_path == None):
                        pass

                    else:
                        images_data.append({'url': image_path, 'is_url_selected':is_image_selected, 'product': product.pk, 'vendorId': vendor_id})
            
            else:
                transaction.set_rollback(True)
                return Response("Image keys do not match", status=status.HTTP_400_BAD_REQUEST)
            
            for category_data in categories_data:
                product_category_joint_serializer = ProductCategoryJointSerializer(data=category_data)
                
                if product_category_joint_serializer.is_valid():
                    product_category_joint = product_category_joint_serializer.save()

                else:
                    print(product_category_joint_serializer.errors)

            for image_data in images_data:
                image_serializer = ProductImagesSerializer(data=image_data)

                if image_serializer.is_valid():
                    images = image_serializer.save()
                    
                else:
                    print("image save error :: ", image_serializer.errors)
                    transaction.set_rollback(True)
                    return Response("Not a valid image", status=status.HTTP_400_BAD_REQUEST)
            
            for modifier_group_data in modifier_groups_data:
                product_modGroup_joint_serializer = ProductModGroupJointSerializer(data=modifier_group_data)

                if product_modGroup_joint_serializer.is_valid():
                    product_modGroup_joint = product_modGroup_joint_serializer.save()

                else:
                    print(product_modGroup_joint_serializer.errors)
                    transaction.set_rollback(True)
                    return Response("Not a valid Modifier group", status=status.HTTP_400_BAD_REQUEST)

            inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
            if inventory_platform:
                sync_status = single_product_sync_with_odoo(product)
                    
                if sync_status == 0:
                    notify(type=3, msg='0', desc='Product did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                else:
                    notify(type=3, msg='0', desc='Product synced with Inventory', stn=['POS'], vendorId=vendor_id)
            
            product_info = get_product_data(product, vendor_id)
            
            return JsonResponse(product_info, status=status.HTTP_201_CREATED)
    
    return Response(product_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH"])
def update_product(request, product_id):
    vendor_id = request.POST.get('vendorId', None)
    
    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    if product_id:
        product = Product.objects.filter(pk=product_id, vendorId=vendor_id).first()

        if product:
            product_serializer = ProductSerializer(product, data=request.data)

            # Check if a product with the new PLU already exists while editing
            new_plu = request.data.get('PLU')
            
            existing_product_with_new_plu = Product.objects.filter(PLU=new_plu, vendorId=vendor_id).exclude(pk=product_id).first()

            if existing_product_with_new_plu:
                return Response({'error': 'Product with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if product_serializer.is_valid():
                category_ids = []
                modifier_group_ids = []
                images_data = []

                image_path_keys = []
                is_image_selected_keys = []

                with transaction.atomic():
                    updated_product = product_serializer.save()

                    for key, value in request.data.items():
                        if key.startswith('categories-'):
                            category_ids.append(int(value))
            
                        if key.startswith('modifier_groups-'):
                            modifier_group_ids.append(int(value))
                    
                        if key.startswith('images-'):
                            if key.endswith('-image'):
                                image_path_keys.append(key)
                            if key.endswith('-is_image_selected'):
                                is_image_selected_keys.append(key)

                    ProductImage.objects.filter(product=updated_product.pk, vendorId=vendor_id).delete()
                    
                    if len(image_path_keys) == len(is_image_selected_keys):
                        for iterator in range(len(image_path_keys)):
                            image_path = request.data.get(image_path_keys[iterator], None)
                            
                            is_image_selected = request.data.get(is_image_selected_keys[iterator], None)
                            
                            if ProductImage.objects.filter(product=updated_product.pk, image=image_path, is_image_selected=is_image_selected, vendorId=vendor_id).exists():
                                pass

                            else:
                                images_data.append({"product":updated_product.pk, "url":image_path, "is_url_selected":is_image_selected, "vendorId":vendor_id})

                    else:
                        transaction.set_rollback(True)
                        return Response("Image keys do not match", status=status.HTTP_400_BAD_REQUEST)
                    
                    for image_data in images_data:
                        product_image_serializer = ProductImagesSerializer(data=image_data)
                        
                        if product_image_serializer.is_valid():
                            img=product_image_serializer.save()
                            
                        else:
                            print(product_image_serializer.errors)
                    
                    product_category_joint_ids = list(ProductCategoryJoint.objects.filter(product=updated_product.pk, vendorId=vendor_id).values_list('category_id', flat=True))
                    
                    category_ids_not_in_joint = []

                    for category_id in category_ids:
                        if category_id not in product_category_joint_ids:
                            category_ids_not_in_joint.append(category_id)

                    for category_id in category_ids_not_in_joint:
                        product_instance = Product.objects.filter(pk=updated_product.pk, vendorId=vendor_id).first()
                        category_instance = ProductCategory.objects.filter(pk=category_id).first()
                        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

                        ProductCategoryJoint.objects.create(product=product_instance, category=category_instance, vendorId=vendor_instance)

                    missing_category_ids = list(set(product_category_joint_ids) - set(category_ids))

                    for category_id in missing_category_ids:
                        ProductCategoryJoint.objects.filter(product=updated_product.pk, category=category_id, vendorId=vendor_id).delete()
                    
                    product_modgroup_joint_ids = list(ProductAndModifierGroupJoint.objects.filter(product=updated_product.pk, vendorId=vendor_id).values_list('modifierGroup_id', flat=True))
                    
                    modifier_group_ids_not_in_joint = []

                    for group_id in modifier_group_ids:
                        if group_id not in product_modgroup_joint_ids:
                            modifier_group_ids_not_in_joint.append(group_id)

                    for group_id in modifier_group_ids_not_in_joint:
                        product_instance = Product.objects.filter(pk=updated_product.pk, vendorId=vendor_id).first()
                        modifier_group_instance = ProductModifierGroup.objects.filter(pk=group_id).first()
                        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

                        ProductAndModifierGroupJoint.objects.create(product=product_instance, modifierGroup=modifier_group_instance, vendorId=vendor_instance)
                    
                    missing_modifier_group_ids = list(set(product_modgroup_joint_ids) - set(modifier_group_ids))

                    for group_id in missing_modifier_group_ids:
                        ProductAndModifierGroupJoint.objects.filter(product=updated_product.pk, modifierGroup=group_id, vendorId=vendor_id).delete()
                    
                    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                    if inventory_platform:
                        sync_status = single_product_sync_with_odoo(product)
                            
                        if sync_status == 0:
                            notify(type=3, msg='0', desc='Product did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                        
                        else:
                            notify(type=3, msg='0', desc='Product synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    product = Product.objects.filter(pk=product_id, vendorId=vendor_id).first()

                    product_info = get_product_data(product, vendor_id)
                    
                    return JsonResponse(product_info, status=status.HTTP_200_OK)
                
            else:
                return Response(product_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            return Response("Product does not exist", status=status.HTTP_404_NOT_FOUND)
    
    else:
        return Response("Product ID empty", status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
def delete_product(request, product_id):
    vendor_id = request.GET.get('vendorId', None)

    if not vendor_id:
        return Response("Vendor ID cannot be empty", status=status.HTTP_400_BAD_REQUEST)

    vendor_id = int(vendor_id)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_404_NOT_FOUND)
    
    if not product_id:
        return Response("Product ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    product = Product.objects.filter(pk=product_id, vendorId=vendor_id).first()

    if product:
        try:
            with transaction.atomic():
                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

                if inventory_platform:
                    delete_status, error_message, request_data = delete_product_in_odoo(inventory_platform.baseUrl, product.PLU, vendor_id)
                
                    if delete_status == 0:
                        notify(type=3, msg='0', desc='Category did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Category synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                product.delete()

                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    else:
        return Response("Product not found", status=status.HTTP_404_NOT_FOUND)

class ModifierGroupViewSet(viewsets.ModelViewSet):
    queryset = ProductModifierGroup.objects.all()
    serializer_class = ModifierGroupSerializer
    filter_class = ModifierGroupFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    pagination_class = CustomPagination 

    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            queryset = ProductModifierGroup.objects.filter(vendorId=vendor_id)
        
        else:
            queryset = ProductModifierGroup.objects.none()
        
        queryset = queryset.order_by('-id')

        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # name_query = request.query_params.get('name', None)
        name_query = request.GET.get('name', None)
        
        if name_query:
            language = request.GET.get('language', "en")

            if language == "English":
                queryset = queryset.filter(name__icontains=name_query)
            
            else:
                queryset = queryset.filter(name_locale__icontains=name_query)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)
        
    def create(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)

            plu = data.get('PLU')
            vendor_id = data.get('vendorId')

            existing_modifier_group = ProductModifierGroup.objects.filter(PLU=plu, vendorId=vendor_id).first()

            if existing_modifier_group:
                return Response({'error': 'Modifier group with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                if inventory_platform:
                    sync_status = single_modifier_group_sync_with_odoo(serializer.instance)
                        
                    if sync_status == 0:
                        notify(type=3, msg='0', desc='Modifier group did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Modifier group synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                partial = kwargs.pop('partial', False)
                instance = self.get_object()

                new_plu = request.data.get('PLU')

                if new_plu != instance.PLU:
                    existing_category = ProductModifierGroup.objects.filter(PLU=new_plu, vendorId=instance.vendorId).first()

                    if existing_category:
                        return Response({'error': 'Modifier group with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)
                    
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)

                vendor_id = instance.vendorId.pk
                
                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                if inventory_platform:
                    sync_status = single_modifier_group_sync_with_odoo(serializer.instance)
                        
                    if sync_status == 0:
                        notify(type=3, msg='0', desc='Modifier group did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Modifier group synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                instance = self.get_object()
                
                vendor_id = instance.vendorId.pk
                
                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                if inventory_platform:
                    sync_status = delete_modifier_group_in_odoo(inventory_platform.baseUrl, instance.PLU, vendor_id)
                        
                    if sync_status == 0:
                        notify(type=3, msg='0', desc='Modifier group did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Modifier group synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                self.perform_destroy(instance)
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET",])
def get_modifiers(request):
    vendor_id = request.GET.get("vendorId", None)
    modifier_name = request.GET.get("modifierName", None)
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)
    language = request.GET.get("language", "English")

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_404_NOT_FOUND)
    
    vendor_id = int(vendor_id)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_404_NOT_FOUND)

    if modifier_name:
        if language == "English":
            modifiers = ProductModifier.objects.filter(modifierName__icontains=modifier_name, vendorId=vendor_id).order_by('-pk')

        else:
            modifiers = ProductModifier.objects.filter(modifierName_locale__icontains=modifier_name, vendorId=vendor_id).order_by('-pk')
            
    else:
        modifiers = ProductModifier.objects.filter(vendorId=vendor_id).order_by('-pk')

    if modifiers:
        paginator = Paginator(modifiers, page_size)

        try:
            paginated_modifiers = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_modifiers = paginator.page(1)
        except EmptyPage:
            paginated_modifiers = paginator.page(paginator.num_pages)

        response_data = []
        current_page = paginated_modifiers.number
        total_pages = paginator.num_pages

        for single_modifier in paginated_modifiers:
            modifier_info = get_modifier_data(single_modifier, vendor_id)

            response_data.append(modifier_info)

        response = {
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": int(page_size),
            "results": response_data,
        }

        return JsonResponse(response, status=200)
    
    else:
        response = {
            "total_pages": 0,
            "current_page": 0,
            "page_size": 0,
            "results": [],
        }

        return JsonResponse(response, status=200)

        
@api_view(["POST"])
def create_modifier(request):
    plu = request.data.get('modifierPLU')
    vendor_id = request.data.get('vendorId')

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    existing_modifier = ProductModifier.objects.filter(modifierPLU=plu, vendorId=vendor_id).first()

    if existing_modifier:
        return JsonResponse({'error':'Modifier with this PLU already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
    modifier_serializer = ModifierSerializer(data=request.data)

    if modifier_serializer.is_valid():
        modifier_groups_ids = []

        with transaction.atomic():
            modifier = modifier_serializer.save()

            vendor_id = int(request.data.get('vendorId'))

            for key, value in request.data.items():
                if key.startswith('modifier_groups-'):
                    modifier_groups_ids.append(int(value))
            
            for group_id in modifier_groups_ids:
                modifier_instance = modifier
                modifier_group_instance = ProductModifierGroup.objects.filter(pk=group_id, vendorId=vendor_id).first()
                vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

                ProductModifierAndModifierGroupJoint.objects.create(modifier=modifier_instance, modifierGroup=modifier_group_instance, vendor=vendor_instance)

            inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
            if inventory_platform:
                sync_status = single_modifier_sync_with_odoo(modifier)
                    
                if sync_status == 0:
                    notify(type=3, msg='0', desc='Modifier did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                else:
                    notify(type=3, msg='0', desc='Modifier synced with Inventory', stn=['POS'], vendorId=vendor_id)
            
            modifier_info = get_modifier_data(modifier, vendor_id)
            
            return JsonResponse(modifier_info, status=status.HTTP_201_CREATED)
    
    else:
        return Response(modifier_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH"])
def update_modifier(request, modifier_id):
    vendor_id = request.POST.get('vendorId', None)

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if not modifier_id:
        return Response("Modifier ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    modifier = ProductModifier.objects.filter(pk=modifier_id, vendorId=vendor_id).first()

    if not modifier:
        return Response("Modifier does not exist", status=status.HTTP_404_NOT_FOUND)
    
    modifier_serializer = ModifierSerializer(modifier, data=request.data)

    # Check if a modifier with the new PLU already exists while editing
    new_plu = request.data.get('modifierPLU')

    existing_modifier_with_new_plu = ProductModifier.objects.filter(modifierPLU=new_plu, vendorId=vendor_id).exclude(pk=modifier_id).first()

    if existing_modifier_with_new_plu:
        return JsonResponse({'error': 'Modifier with this PLU already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if modifier_serializer.is_valid():
        modifier_groups_ids = []
        
        with transaction.atomic():
            updated_modifier = modifier_serializer.save()

            vendor_id = int(request.data.get('vendorId'))

            for key, value in request.data.items():
                if key.startswith('modifier_groups-'):
                    if key.endswith('-group-old'):
                        ProductModifierAndModifierGroupJoint.objects.filter(modifier=updated_modifier.pk, modifierGroup=int(value), vendor=vendor_id).delete()
                    else:
                        if ProductModifierAndModifierGroupJoint.objects.filter(modifier=updated_modifier.pk, modifierGroup=int(value), vendor=vendor_id).exists():
                            pass
                        else:
                            modifier_groups_ids.append(int(value))
            
            for group_id in modifier_groups_ids:
                modifier_instance = modifier
                modifier_group_instance = ProductModifierGroup.objects.filter(pk=group_id, vendorId=vendor_id).first()
                vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

                ProductModifierAndModifierGroupJoint.objects.create(modifier=modifier_instance, modifierGroup=modifier_group_instance, vendor=vendor_instance)

            inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
            if inventory_platform:
                sync_status = single_modifier_sync_with_odoo(modifier)
                    
                if sync_status == 0:
                    notify(type=3, msg='0', desc='Modifier did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                else:
                    notify(type=3, msg='0', desc='Modifier synced with Inventory', stn=['POS'], vendorId=vendor_id)
            
            modifier_info = get_modifier_data(updated_modifier, vendor_id)
            
            return JsonResponse(modifier_info, status=status.HTTP_201_CREATED)
        
    else:
        return Response(modifier_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

@api_view(["DELETE"])
def delete_modifier(request, modifier_id):
    vendor_id = request.GET.get('vendorId', None)

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if not modifier_id:
        return Response("Modifier ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    modifier = ProductModifier.objects.filter(pk=modifier_id, vendorId=vendor_id).first()

    if modifier:
        try:
            with transaction.atomic():
                inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()
                
                if inventory_platform:
                    sync_status = delete_modifier_in_odoo(inventory_platform.baseUrl, modifier.modifierPLU, vendor_id)
                        
                    if sync_status == 0:
                        notify(type=3, msg='0', desc='Modifier did not synced with Inventory', stn=['POS'], vendorId=vendor_id)
                    
                    else:
                        notify(type=3, msg='0', desc='Modifier synced with Inventory', stn=['POS'], vendorId=vendor_id)
                
                modifier.delete()
            
                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    else:
        return Response("Modifier not found", status=status.HTTP_404_NOT_FOUND)
    

@api_view(["GET",])
def get_customers(request):
    vendor_id = request.GET.get("vendorId", None)
    search_parameter = request.GET.get("search_parameter", None)
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_id = int(vendor_id)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_404_NOT_FOUND)

    if search_parameter:
        expression = r'\d+'
        mobile_number = re.search(expression, search_parameter)
        
        if mobile_number:
            # when a match is found, group() returns the actual substring that matched the pattern specified in the regular expression
            mobile_number = mobile_number.group()

            customers = Customer.objects.filter(Phone_Number__icontains=mobile_number, VendorId=vendor_id).order_by("pk")

        else:
            expression = r'[A-Za-z ]+'
            customer_name = re.search(expression, search_parameter)

            if customer_name:
                customer_name = customer_name.group()

                customers = Customer.objects.filter(
                    Q(FirstName__icontains=customer_name) | Q(LastName__icontains=customer_name),
                    VendorId=vendor_id
                ).order_by('FirstName')

    else:
        customers = Customer.objects.filter(VendorId=vendor_id).order_by('-pk')

    if customers:
        paginator = Paginator(customers, page_size)

        try:
            paginated_customers = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_customers = paginator.page(1)
        except EmptyPage:
            paginated_customers = paginator.page(paginator.num_pages)

        response_data = []
        current_page = paginated_customers.number
        total_pages = paginator.num_pages

        for customer in paginated_customers:
            shipping_address = {}

            customer_address = Address.objects.filter(customer=customer.pk, type="shipping_address", is_selected=True).first()
            
            if customer_address:
                shipping_address = {
                    "id": customer_address.pk,
                    "address_line_1": customer_address.address_line1 if customer_address.address_line1 else "",
                    "address_line_2": customer_address.address_line2 if customer_address.address_line2 else "",
                    "city": customer_address.city if customer_address.city else "",
                    "state": customer_address.state if customer_address.state else "",
                    "country": customer_address.country if customer_address.country else "",
                    "zipcode": customer_address.zipcode if customer_address.zipcode else "",
                    "type": customer_address.type,
                    "is_selected": customer_address.is_selected
                }

            else:
                shipping_address = {
                    "id": 0,
                    "address_line_1": "",
                    "address_line_2": "",
                    "city": "",
                    "state": "",
                    "country": "",
                    "zipcode": "",
                    "type": "",
                    "is_selected": ""
                }
            
            total_revenue = 0.0

            loyalty_points_history = []

            orders = Order.objects.filter(customerId=customer.pk, vendorId=vendor_id)

            if orders:
                total_revenue = orders.aggregate(total_revenue=Sum('subtotal'))['total_revenue']

                for order in orders:
                    loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(customer=customer.pk, order=order.pk, vendor=vendor_id).order_by("-credit_datetime")

                    if loyalty_points_credit_history:
                        for credit_point in loyalty_points_credit_history:
                            credit_transactions = {}
                            # redeem_transactions = []

                            loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=customer.pk, credit_history=credit_point.pk, vendor=vendor_id)

                            if loyalty_points_redeem_history:
                                # for redeem_point in loyalty_points_redeem_history:
                                #     redeem_history = {}

                                #     redeem_history["id"] = redeem_point.pk
                                #     redeem_history["order_id"] = redeem_point.order.externalOrderld
                                #     redeem_history["points_redeemed"] = redeem_point.points_redeemed
                                #     redeem_history["redeem_datetime"] = redeem_point.redeem_datetime
                                #     redeem_history["redeemed_by"] = redeem_point.redeemed_by

                                #     redeem_transactions.append(redeem_history)

                                credit_transactions["id"] = credit_point.pk
                                credit_transactions["order_id"] = credit_point.order.externalOrderld
                                credit_transactions["points_credited"] = credit_point.points_credited
                                credit_transactions["credit_datetime"] = credit_point.credit_datetime
                                credit_transactions["expiry_date"] = credit_point.expiry_date
                                credit_transactions["is_expired"] = credit_point.is_expired
                                credit_transactions["total_points_redeemed"] = credit_point.total_points_redeemed
                                credit_transactions["balance_points"] = credit_point.balance_points
                                # credit_transactions["redeem_history"] = redeem_transactions

                                loyalty_points_history.append(credit_transactions)

            response_data.append({
                "id": customer.pk,
                "FirstName": customer.FirstName if customer.FirstName else "",
                "LastName": customer.LastName if customer.LastName else "",
                "Email": customer.Email if customer.Email else "",
                "Phone_Number": customer.Phone_Number,
                "loyalty_points_balance": customer.loyalty_points_balance,
                "Shipping_Address": shipping_address,
                "total_revenue": total_revenue,
                "loyalty_points_history": loyalty_points_history
            })

        response = {
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": int(page_size),
            "results": response_data,
        }

        return JsonResponse(response, status=status.HTTP_200_OK)
    
    else:
        response = {
            "total_pages": 0,
            "current_page": 0,
            "page_size": 0,
            "results": [],
        }

        return JsonResponse(response, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_customer(request):
    body_data = json.loads(request.body)

    vendor_id = body_data.get('vendorId', None)
    phone_number = body_data.get("Phone_Number", None)
    first_name = body_data.get("FirstName", None)
    last_name = body_data.get("LastName", None)
    email = body_data.get("Email", None)
    shipping_address = body_data.get("Shipping_Address", None)

    if not all((vendor_id, phone_number)):
        return Response("Vendor ID or Phone number is empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id= int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    existing_customer = Customer.objects.filter(Phone_Number=phone_number, VendorId=vendor_id).first()

    if existing_customer:
        return Response("Customer with this number already exist", status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            customer_instance = Customer.objects.create(
                FirstName=first_name,
                LastName=last_name,
                Email=email,
                Phone_Number=phone_number,
                loyalty_points_balance=0,
                VendorId=vendor_instance
            )

            if shipping_address:
                shipping_address_address_line1 = shipping_address.get("address_line_1", None)
                shipping_address_address_line2 = shipping_address.get("address_line_2", None)
                shipping_address_city = shipping_address.get("city", None)
                shipping_address_state = shipping_address.get("state", None)
                shipping_address_country = shipping_address.get("country", None)
                shipping_address_zipcode = shipping_address.get("zipcode", None)

                shipping_address_instance = Address.objects.create(
                    address_line1=shipping_address_address_line1,
                    address_line2=shipping_address_address_line2,
                    city=shipping_address_city,
                    state=shipping_address_state,
                    country=shipping_address_country,
                    zipcode=shipping_address_zipcode,
                    type="shipping_address",
                    is_selected=True,
                    customer=customer_instance
                )
                
            else:
                shipping_address_instance = None

            customer_data = {}
            shipping_address_data = {}

            if shipping_address_instance:
                shipping_address_data["id"] = shipping_address_instance.pk
                shipping_address_data["address_line_1"] = shipping_address_instance.address_line1 if shipping_address_instance.address_line1 else ""
                shipping_address_data["address_line_2"] = shipping_address_instance.address_line2 if shipping_address_instance.address_line2 else ""
                shipping_address_data["city"] = shipping_address_instance.city if shipping_address_instance.city else ""
                shipping_address_data["state"] = shipping_address_instance.state if shipping_address_instance.state else ""
                shipping_address_data["country"] = shipping_address_instance.country if shipping_address_instance.country else ""
                shipping_address_data["zipcode"] = shipping_address_instance.zipcode if shipping_address_instance.zipcode else ""
                shipping_address_data["type"] = shipping_address_instance.type
                shipping_address_data["is_selected"] = shipping_address_instance.is_selected
            
            else:
                shipping_address_data["id"] = 0
                shipping_address_data["address_line_1"] = ""
                shipping_address_data["address_line_2"] = ""
                shipping_address_data["city"] = ""
                shipping_address_data["state"] = ""
                shipping_address_data["country"] = ""
                shipping_address_data["zipcode"] = ""
                shipping_address_data["type"] = ""
                shipping_address_data["is_selected"] = False
            
            customer_data["id"] = customer_instance.pk
            customer_data["FirstName"] = customer_instance.FirstName if customer_instance.FirstName else ""
            customer_data["LastName"] = customer_instance.LastName if customer_instance.LastName else ""
            customer_data["Email"] = customer_instance.Email if customer_instance.Email else ""
            customer_data["Phone_Number"] = customer_instance.Phone_Number if customer_instance.Phone_Number else ""
            customer_data["loyalty_points_balance"] = customer_instance.loyalty_points_balance
            customer_data["Shipping_Address"] = shipping_address_data
            customer_data["total_revenue"] = 0.0
            customer_data["loyalty_points_history"] = []
           
            return JsonResponse(customer_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(e)
        return Response(e, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH"])
def update_customer(request):
    body_data = json.loads(request.body)

    vendor_id = body_data.get('vendorId', None)
    phone_number = body_data.get("Phone_Number", None)
    customer_id = body_data.get("id")

    if not all((vendor_id, customer_id, phone_number)):
        return Response("Vendor ID, Customer ID or Phone number is empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id, customer_id = map(int, (vendor_id, customer_id))
    except ValueError:
        return Response("Invalid Vendor ID or Customer ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()
    customer_instance = Customer.objects.filter(pk=customer_id).first()

    if not all((vendor, customer_instance)):
        return Response("Vendor or Customer does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    first_name = body_data.get("FirstName", None)
    last_name = body_data.get("LastName", None)
    email = body_data.get("Email", None)
    shipping_address = body_data.get("Shipping_Address", None)

    try:
        with transaction.atomic():
            if shipping_address:
                shipping_address_id = shipping_address.get("id", None)
                shipping_address_address_line1 = shipping_address.get("address_line_1", None)
                shipping_address_address_line2 = shipping_address.get("address_line_2", None)
                shipping_address_city = shipping_address.get("city", None)
                shipping_address_state = shipping_address.get("state", None)
                shipping_address_country = shipping_address.get("country", None)
                shipping_address_zipcode = shipping_address.get("zipcode", None)

                if not shipping_address_id:
                    shipping_address_instance = Address.objects.create(
                        address_line1=shipping_address_address_line1,
                        address_line2=shipping_address_address_line2,
                        city=shipping_address_city,
                        state=shipping_address_state,
                        country=shipping_address_country,
                        zipcode=shipping_address_zipcode,
                        type="shipping_address",
                        is_selected=True,
                        customer=customer_instance
                    )
                
                else:
                    shipping_address_instance = Address.objects.filter(customer=customer_instance.pk, type="shipping_address", is_selected=True).first()

                    if shipping_address_instance:
                        shipping_address_instance.address_line1 = shipping_address_address_line1
                        shipping_address_instance.address_line2 = shipping_address_address_line2
                        shipping_address_instance.city = shipping_address_city
                        shipping_address_instance.state = shipping_address_state
                        shipping_address_instance.country = shipping_address_country
                        shipping_address_instance.zipcode = shipping_address_zipcode

                        shipping_address_instance.save()

                    else:
                        shipping_address_instance = Address.objects.create(
                            address_line1=shipping_address_address_line1,
                            address_line2=shipping_address_address_line2,
                            city=shipping_address_city,
                            state=shipping_address_state,
                            country=shipping_address_country,
                            zipcode=shipping_address_zipcode,
                            type="shipping_address",
                            is_selected=True,
                            customer=customer_instance
                        )
            
            else:
                shipping_address_instance = None
                
            customer_instance.FirstName = first_name
            customer_instance.LastName = last_name
            customer_instance.Email = email
            customer_instance.Phone_Number = phone_number

            customer_instance.save()

            customer_data = {}
            shipping_address_data = {}

            if shipping_address_instance:
                shipping_address_data["id"] = shipping_address_instance.pk
                shipping_address_data["address_line_1"] = shipping_address_instance.address_line1 if shipping_address_instance.address_line1 else ""
                shipping_address_data["address_line_2"] = shipping_address_instance.address_line2 if shipping_address_instance.address_line2 else ""
                shipping_address_data["city"] = shipping_address_instance.city if shipping_address_instance.city else ""
                shipping_address_data["state"] = shipping_address_instance.state if shipping_address_instance.state else ""
                shipping_address_data["country"] = shipping_address_instance.country if shipping_address_instance.country else ""
                shipping_address_data["zipcode"] = shipping_address_instance.zipcode if shipping_address_instance.zipcode else ""
                shipping_address_data["type"] = shipping_address_instance.type
                shipping_address_data["is_selected"] = shipping_address_instance.is_selected
            
            else:
                shipping_address_data["id"] = 0
                shipping_address_data["address_line_1"] = ""
                shipping_address_data["address_line_2"] = ""
                shipping_address_data["city"] = ""
                shipping_address_data["state"] = ""
                shipping_address_data["country"] = ""
                shipping_address_data["zipcode"] = ""
                shipping_address_data["type"] = ""
                shipping_address_data["is_selected"] = False

            total_revenue = 0.0

            loyalty_points_history = []

            orders = Order.objects.filter(customerId=customer_instance.pk, vendorId=vendor_id)

            if orders:
                total_revenue = orders.aggregate(total_revenue=Sum('subtotal'))['total_revenue']
            
                for order in orders:
                        loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(customer=customer_instance.pk, order=order.pk, vendor=vendor_id).order_by("-credit_datetime")

                        if loyalty_points_credit_history:
                            for credit_point in loyalty_points_credit_history:
                                credit_transactions = {}
                                # redeem_transactions = []

                                loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=customer_instance.pk, credit_history=credit_point.pk, vendor=vendor_id)

                                if loyalty_points_redeem_history:
                                    # for redeem_point in loyalty_points_redeem_history:
                                    #     redeem_history = {}

                                    #     redeem_history["id"] = redeem_point.pk
                                    #     redeem_history["order_id"] = redeem_point.order.externalOrderld
                                    #     redeem_history["points_redeemed"] = redeem_point.points_redeemed
                                    #     redeem_history["redeem_datetime"] = redeem_point.redeem_datetime
                                    #     redeem_history["redeemed_by"] = redeem_point.redeemed_by

                                    #     redeem_transactions.append(redeem_history)

                                    credit_transactions["id"] = credit_point.pk
                                    credit_transactions["order_id"] = credit_point.order.externalOrderld
                                    credit_transactions["points_credited"] = credit_point.points_credited
                                    credit_transactions["credit_datetime"] = credit_point.credit_datetime
                                    credit_transactions["expiry_date"] = credit_point.expiry_date
                                    credit_transactions["is_expired"] = credit_point.is_expired
                                    credit_transactions["total_points_redeemed"] = credit_point.total_points_redeemed
                                    credit_transactions["balance_points"] = credit_point.balance_points
                                    # credit_transactions["redeem_history"] = redeem_transactions

                                    loyalty_points_history.append(credit_transactions)
            
            customer_data["id"] = customer_instance.pk
            customer_data["FirstName"] = customer_instance.FirstName if customer_instance.FirstName else ""
            customer_data["LastName"] = customer_instance.LastName if customer_instance.LastName else ""
            customer_data["Email"] = customer_instance.Email if customer_instance.Email else ""
            customer_data["Phone_Number"] = customer_instance.Phone_Number if customer_instance.Phone_Number else ""
            customer_data["loyalty_points_balance"] = customer_instance.loyalty_points_balance
            customer_data["Shipping_Address"] = shipping_address_data
            customer_data["total_revenue"] = total_revenue
            customer_data["loyalty_points_history"] = loyalty_points_history
           
            return JsonResponse(customer_data, status=status.HTTP_200_OK)
        
    except IntegrityError as e:
        error_message = str(e)

        if 'duplicate key value violates unique constraint' in error_message and 'Phone_Number' in error_message and 'VendorId_id' in error_message:
            return Response("Customer with this phone number already exists", status=status.HTTP_400_BAD_REQUEST)
        else:
            raise e
    
    except Exception as e:
        print(e)
        return Response(e, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(["DELETE"])
def delete_customer(request, customer_id):
    if not customer_id:
        return Response("Modifier ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    customer = Customer.objects.filter(pk=customer_id).first()

    if customer:
        try:
            with transaction.atomic():
                customer.delete()
            
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    else:
        return Response("Customer not found", status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def get_orders_of_customer(request):
    vendor_id = request.GET.get("vendorId", None)
    customer_id = request.GET.get("customerId", None)
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)

    if not all((vendor_id, customer_id)):
        return Response("Vendor ID or Customer ID is empty", status=status.HTTP_400_BAD_REQUEST)

    try:
        vendor_id, customer_id = map(int, (vendor_id, customer_id))
    except ValueError:
        return Response("Invalid Vendor ID or Customer ID", status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()
    customer_instance = Customer.objects.filter(pk=customer_id).first()

    if not all((vendor_instance, customer_instance)):
        return Response("Vendor or Customer does not exist", status=status.HTTP_404_NOT_FOUND)
    
    orders = Order.objects.filter(customerId=customer_id, vendorId=vendor_id).order_by("-arrivalTime")

    if orders:
        paginator = Paginator(orders, page_size)

        try:
            paginated_orders = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

        order_list = []

        current_page = paginated_orders.number
        total_pages = paginator.num_pages
        
        for order in paginated_orders:
         koms_order = KOMSOrder.objects.filter(master_order=order.pk)                       # This is a temparory    
         if koms_order:                                                                     # Fix for Broken orders between 
            koms_order = koms_order.last()                                                  # core and KOMS
            koms_order = KOMSOrder.objects.filter(master_order=order.pk).last()

            order_contents = Order_content.objects.filter(orderId=koms_order.pk)

            order_items = []
            for content in order_contents:
                product = ProductCategoryJoint.objects.get(product__vendorId=vendor_id, product__PLU=content.SKU)

                # modifier_list = defaultdict(list)
                modifier_list = []
                    
                modifiers = Order_modifer.objects.filter(contentID=content.pk)
                    
                if modifiers:
                    for modifier in modifiers:
                        product_modifier = ProductModifier.objects.filter(modifierPLU=modifier.SKU, vendorId=vendor_id).first()
                        
                        modifier_list.append({
                            'modifier_name': modifier.name,
                            'modifier_plu': modifier.SKU,
                            'modifier_quantity': modifier.quantity,
                            'modifier_price': product_modifier.modifierPrice if product_modifier else 0.0,
                            'modifier_img': product_modifier.modifierImg if product_modifier else ""
                        })

                product_image = ProductImage.objects.filter(product=product.product.pk).first()

                if product_image:
                    image_url = product_image.url
                else:
                    image_url = 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
                
                order_items.append({
                    'quantity': content.quantity,
                    'product_plu': content.SKU,
                    'product_name': product.product.productName,
                    'tag': product.product.tag,
                    'is_unlimited': product.product.is_unlimited,
                    'preparation_time': product.product.preparationTime,
                    'is_taxable': product.product.taxable,
                    'product_image': image_url,
                    'category': product.category.categoryName,
                    "product_note": content.note if content.note else "",
                    "unit_price": product.product.productPrice,
                    'modifiers': modifier_list
                })
            
            payment_data = {}
            
            payment_details = OrderPayment.objects.filter(orderId=order.pk).last()
            
            if payment_details:
                if PaymentType.get_payment_str(payment_details.type) == 'CASH':
                    payment_data['paymentKey'] = ''
                    payment_data['platform'] = ''
                    payment_data["mode"] = PaymentType.get_payment_str(PaymentType.CASH)

                else:
                    payment_data["paymentKey"] = payment_details.paymentKey if payment_details.paymentKey else ''
                    payment_data["platform"] = payment_details.platform if payment_details.platform else ''
                    payment_data["mode"] = PaymentType.get_payment_str(payment_details.type)
                
                payment_data["status"] = payment_details.status

            else:
                payment_data = {
                    "paymentKey": "",
                    "platform": "",
                    "status": False,
                    "mode": PaymentType.get_payment_str(PaymentType.CASH)
                }

            # table_ids = []
            table_numbers_list = ""

            table_details = Order_tables.objects.filter(orderId_id=koms_order.pk)

            if table_details:
                for table in table_details:
                    table_numbers_list = table_numbers_list + str(table.tableId.tableNumber) + ","
                    # table_ids.append(table.tableId.pk)

                table_numbers_list = table_numbers_list[:-1]

            loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=customer_id, order=order.pk)

            if loyalty_points_redeem_history:
                total_points_redeemed = loyalty_points_redeem_history.aggregate(Sum('points_redeemed'))['points_redeemed__sum']

                if not total_points_redeemed:
                    total_points_redeemed = 0

            else:
                total_points_redeemed = 0
            
            order_data = {
                "orderId": order.pk,
                "staging_order_id": koms_order.pk,
                "external_order_id": order.externalOrderld,
                "status": koms_order.order_status,
                "order_note": order.Notes if order.Notes else "",
                "total_tax": order.tax,
                "total_discount": order.discount,
                "delivery_charge": order.delivery_charge,
                "subtotal": order.subtotal,
                "total_amount": order.TotalAmount,
                "pickup_time": koms_order.pickupTime.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%dT%H:%M:%S"),
                "order_datetime": order.OrderDate.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%dT%H:%M:%S"),
                "arrival_time": order.arrivalTime.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%dT%H:%M:%S"),
                "order_type": order.orderType,
                "platform_name": order.platform.Name,
                "table_numbers": table_numbers_list,
                "items": order_items,
                "payment": payment_data,
                "total_points_redeemed": total_points_redeemed
            }

            order_list.append(order_data)
        
        response = {
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": int(page_size),
            "results": order_list
        }

        return JsonResponse(response, status=status.HTTP_200_OK)
    
    else:
        response = {
            "total_pages": 0,
            "current_page": 0,
            "page_size": 0,
            "results": [],
        }

        return JsonResponse(response, status=status.HTTP_200_OK)
    

@api_view(["GET"])
def get_loyalty_point_transactions_of_customer(request):
    vendor_id = request.GET.get("vendorId", None)
    customer_id = request.GET.get("customerId", None)
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)

    if not all((vendor_id, customer_id)):
        return Response("Vendor ID or Customer ID is empty", status=status.HTTP_400_BAD_REQUEST)

    try:
        vendor_id, customer_id = map(int, (vendor_id, customer_id))
    except ValueError:
        return Response("Invalid Vendor ID or Customer ID", status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()
    customer_instance = Customer.objects.filter(pk=customer_id).first()

    if not all((vendor_instance, customer_instance)):
        return Response("Vendor or Customer does not exist", status=status.HTTP_404_NOT_FOUND)
    
    orders = Order.objects.filter(customerId=customer_id, vendorId=vendor_id).order_by("-OrderDate")

    if orders:
        paginator = Paginator(orders, page_size)

        try:
            paginated_orders = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

        transaction_list = []

        current_page = paginated_orders.number
        total_pages = paginator.num_pages

        loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(customer=customer_id)

        sum_of_points_credited = loyalty_points_credit_history.aggregate(Sum('points_credited'))['points_credited__sum']
        sum_of_balance_points = loyalty_points_credit_history.aggregate(Sum('balance_points'))['balance_points__sum']
        sum_of_points_redeemed = loyalty_points_credit_history.aggregate(Sum('total_points_redeemed'))['total_points_redeemed__sum']

        if not sum_of_points_credited:
            sum_of_points_credited = 0

        if not sum_of_balance_points:
            sum_of_balance_points = 0

        if not sum_of_points_redeemed:
            sum_of_points_redeemed = 0
        
        loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(customer=customer_id)
        
        for order in paginated_orders:
            credit_transaction = {}
            redeem_transaction = []

            credit_history = loyalty_points_credit_history.filter(order=order.pk).first()

            if credit_history:
                credit_transaction["points_credited"] = credit_history.points_credited
                credit_transaction["credit_datetime"] = credit_history.credit_datetime
                credit_transaction["expiry_date"] = credit_history.expiry_date
                credit_transaction["is_expired"] = credit_history.is_expired
            
            else:
                credit_transaction["points_credited"] = 0
                credit_transaction["credit_datetime"] = ""
                credit_transaction["expiry_date"] = ""
                credit_transaction["is_expired"] = False

            redeem_history = loyalty_points_redeem_history.filter(order=order.pk)

            if redeem_history:
                redeemed_points = redeem_history.aggregate(Sum('points_redeemed'))['points_redeemed__sum']

                for history in redeem_history:
                    redeem_transaction.append({
                        "credit_history_id": history.credit_history.pk,
                        "points_redeemed": history.points_redeemed,
                        "redeem_datetime": history.redeem_datetime,
                        "redeemed_by": history.redeemed_by
                    })    
            
            else:
                redeemed_points = 0
            
            order_data = {
                "order_id": order.pk,
                "external_order_id": order.externalOrderld,
                "order_datetime": order.OrderDate.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%dT%H:%M:%S"),
                "credit_history": credit_transaction,
                "redeemed_points": redeemed_points,
                "redeem_history": redeem_transaction
            }

            transaction_list.append(order_data)
        
        response = {
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": int(page_size),
            "current_points_balance": customer_instance.loyalty_points_balance,
            "sum_of_points_credited": sum_of_points_credited,
            "sum_of_balance_points": sum_of_balance_points,
            "sum_of_points_redeemed": sum_of_points_redeemed,
            "results": transaction_list
        }

        return JsonResponse(response, status=status.HTTP_200_OK)
    
    else:
        response = {
            "total_pages": 0,
            "current_page": 0,
            "page_size": 0,
            "current_points_balance": 0,
            "sum_of_points_credited": 0,
            "sum_of_balance_points": 0,
            "sum_of_points_redeemed": 0,
            "results": [],
        }

        return JsonResponse(response, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_loyalty_points_settings(request):
    vendor_id = request.GET.get("vendorId", None)

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_404_NOT_FOUND)
    
    settings_data = {}
    
    settings = LoyaltyProgramSettings.objects.filter(vendor=vendor_id).first()

    if settings:
        settings_data["id"] = settings.pk
        settings_data["is_active"] = settings.is_active
        settings_data["amount_spent"] = settings.amount_spent_in_rupees_to_earn_unit_point
        settings_data["unit_point_value"] = settings.unit_point_value_in_rupees
        settings_data["expiry_days"] = settings.points_expiry_days
        settings_data["applied_on"] = settings.redeem_limit_applied_on
        settings_data["redeem_limit"] = settings.redeem_limit_in_percentage

        return JsonResponse(settings_data, status=status.HTTP_200_OK)
    
    else:
        settings_data["id"] = 0
        settings_data["is_active"] = False
        settings_data["amount_spent"] = 0
        settings_data["unit_point_value"] = 0
        settings_data["expiry_days"] = 0
        settings_data["applied_on"] = ""
        settings_data["redeem_limit"] = 0

        return JsonResponse(settings_data, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_loyalty_points_settings(request):
    body_data = json.loads(request.body)

    if body_data:
        vendor_id = body_data.get('vendorId', None)

        if vendor_id is None:
            return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
        except ValueError:
            return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

        vendor = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor:
            return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
        
        is_active = body_data.get('is_active')
        amount_spent = body_data.get('amount_spent')
        unit_point_value = body_data.get('unit_point_value')
        expiry_days = body_data.get('expiry_days')
        applied_on = body_data.get('applied_on')
        redeem_limit = body_data.get('redeem_limit')

        if (is_active == None) or (amount_spent == None) or (unit_point_value == None) or \
        (expiry_days == None) or (applied_on == None) or (redeem_limit == None):
            return Response("Invalid data sent", status=status.HTTP_400_BAD_REQUEST)

        settings_count = LoyaltyProgramSettings.objects.filter(vendor=vendor_id).count()

        if settings_count > 0:
            return Response("Loyalty program settings already created", status=status.HTTP_200_OK)
        
        with transaction.atomic():
            settings = LoyaltyProgramSettings.objects.create(
                is_active = is_active,
                amount_spent_in_rupees_to_earn_unit_point = amount_spent,
                unit_point_value_in_rupees = unit_point_value,
                points_expiry_days = expiry_days,
                redeem_limit_applied_on = applied_on,
                redeem_limit_in_percentage = redeem_limit,
                vendor = vendor
            )

            # woocommerce_platform = Platform.objects.filter(VendorId=vendor_id, Name="WooCommerce", isActive=True).first()

            # WooCommerce syncing as entry in wordpress will already be created
            # if woocommerce_platform:
            #     woocommerce_response = WooCommerce.update_loyalty_program_settings(vendor_id, settings)

            #     if woocommerce_response == True:
            #         notify(type=3, msg='0', desc='Loyalty program settings synced', stn=['POS'], vendorId=settings.vendor.pk)

            #     else:
            #         transaction.set_rollback(True)
            #         return Response("WooCommerce syncing error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            settings_data = {}

            settings_data["id"] = settings.pk
            settings_data["is_active"] = settings.is_active
            settings_data["amount_spent"] = settings.amount_spent_in_rupees_to_earn_unit_point
            settings_data["unit_point_value"] = settings.unit_point_value_in_rupees
            settings_data["expiry_days"] = settings.points_expiry_days
            settings_data["applied_on"] = settings.redeem_limit_applied_on
            settings_data["redeem_limit"] = settings.redeem_limit_in_percentage

            return JsonResponse(settings_data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "PATCH"])
def update_loyalty_points_settings(request):
    body_data = json.loads(request.body)

    vendor_id = body_data.get('vendorId', None)

    if vendor_id is None:
        return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid Vendor ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    setting_id = body_data.get('id')
    is_active = body_data.get('is_active')
    amount_spent = body_data.get('amount_spent')
    unit_point_value = body_data.get('unit_point_value')
    expiry_days = body_data.get('expiry_days')
    applied_on = body_data.get('applied_on')
    redeem_limit = body_data.get('redeem_limit')

    settings = LoyaltyProgramSettings.objects.filter(pk=setting_id, vendor=vendor_id).first()

    if not settings:
        return Response("Settings not found", status=status.HTTP_400_BAD_REQUEST)
    
    with transaction.atomic():    
        settings.is_active = is_active
        settings.amount_spent_in_rupees_to_earn_unit_point = amount_spent
        settings.unit_point_value_in_rupees = unit_point_value
        settings.points_expiry_days = expiry_days
        settings.redeem_limit_applied_on = applied_on
        settings.redeem_limit_in_percentage = redeem_limit

        settings.save()

        # woocommerce_platform = Platform.objects.filter(VendorId=vendor_id, Name="WooCommerce", isActive=True).first()

        # WooCommerce syncing
        # if woocommerce_platform:
        #     woocommerce_response = WooCommerce.update_loyalty_program_settings(vendor_id, settings)

        #     if woocommerce_response == True:
        #         notify(type=3, msg='0', desc='Loyalty program settings synced', stn=['POS'], vendorId=settings.vendor.pk)

        #     else:
        #         transaction.set_rollback(True)
        #         return Response("WooCommerce syncing error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        settings_data = {}

        settings_data["id"] = settings.pk
        settings_data["is_active"] = settings.is_active
        settings_data["amount_spent"] = settings.amount_spent_in_rupees_to_earn_unit_point
        settings_data["unit_point_value"] = settings.unit_point_value_in_rupees
        settings_data["expiry_days"] = settings.points_expiry_days
        settings_data["applied_on"] = settings.redeem_limit_applied_on
        settings_data["redeem_limit"] = settings.redeem_limit_in_percentage

        return JsonResponse(settings_data, status=status.HTTP_200_OK)


@api_view(["POST"])
def redeem_loyalty_points(request):
    body_data = request.data

    vendor_id = body_data.get('vendor_id')
    customer_id = body_data.get('customer_id')
    external_order_id = body_data.get('external_order_id')
    is_wordpress = body_data.get('is_wordpress')
    language = body_data.get('language')

    if not all((vendor_id, customer_id, external_order_id)):
        return Response("Vendor ID, Customer ID, Order ID or is_wordpress is empty", status=status.HTTP_400_BAD_REQUEST)

    if is_wordpress is None:
        return Response("is_wordpress is empty", status=status.HTTP_400_BAD_REQUEST)

    try:
        vendor_id, customer_id = map(int, (vendor_id, customer_id))
    except ValueError:
        return Response("Invalid Vendor ID, Customer ID", status=status.HTTP_400_BAD_REQUEST)

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()
    customer_instance = Customer.objects.filter(pk=customer_id, VendorId=vendor_id).first()
    master_order_instance = Order.objects.filter(externalOrderld=external_order_id, vendorId=vendor_id).first()

    if not all((vendor_instance, customer_instance, master_order_instance)):
        return Response("Vendor, Customer, or Order does not exist", status=status.HTTP_400_BAD_REQUEST)

    subtotal = body_data.get('subtotal')
    tax = body_data.get('tax')
    discount = body_data.get('discount')
    delivery_charge = body_data.get('delivery_charge')
    total_amount = body_data.get('total_amount')
    
    with transaction.atomic():    
        master_order_instance.subtotal = subtotal
        master_order_instance.tax = tax
        master_order_instance.discount = discount
        master_order_instance.delivery_charge = delivery_charge
        master_order_instance.TotalAmount = total_amount

        master_order_instance.save()

        print(master_order_instance.customerId.FirstName, master_order_instance.customerId.Phone_Number)

        if (master_order_instance.customerId.FirstName != "Guest") and (master_order_instance.customerId.Phone_Number != "0"):
            loyalty_program_settings = LoyaltyProgramSettings.objects.filter(vendor=vendor_id).first()

            if not loyalty_program_settings:
                return Response("Loyalty Program Settings not found for the vendor", status=status.HTTP_400_BAD_REQUEST)
            
            points_utilized = body_data.get('points_redeemed', 0)
            points_redeemed_by = body_data.get('redeemed_by')

            loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(
                customer=master_order_instance.customerId.pk,
                is_expired=False,
                balance_points__gt=0,
                vendor=vendor_id
            ).order_by("expiry_date")

            points_total = 0
            points_to_redeem = 0
            transactions = []

            customer_instance = Customer.objects.get(pk=master_order_instance.customerId.pk)

            if points_utilized == 0:
                return Response(status=status.HTTP_200_OK)
            
            elif points_utilized < 0:
                return Response("Points redeemed cannot be negative", status=status.HTTP_400_BAD_REQUEST)

            elif customer_instance.loyalty_points_balance == 0:
                if points_utilized == 0:
                    return Response(status=status.HTTP_200_OK)
            
                elif points_utilized > 0:
                    return Response("0 points in account", status=status.HTTP_400_BAD_REQUEST)
            
            elif (customer_instance.loyalty_points_balance > 0):
                if points_utilized > customer_instance.loyalty_points_balance:
                    return Response("Points balance is low", status=status.HTTP_400_BAD_REQUEST)
                
                elif points_utilized > 0:
                    for credit_history_instance in loyalty_points_credit_history:
                        if (points_total != points_utilized) and (points_to_redeem >= 0):
                            points_to_redeem = points_utilized - points_total

                            if (credit_history_instance.balance_points < points_to_redeem) or \
                            (credit_history_instance.balance_points == points_to_redeem):
                                points_total = points_total + credit_history_instance.balance_points
                                
                                transactions.append({
                                    "credit_history_id": credit_history_instance.pk,
                                    "utilized_points": credit_history_instance.balance_points
                                })

                            elif (credit_history_instance.balance_points > points_to_redeem):
                                points_total = points_total + points_to_redeem
                                
                                transactions.append({
                                    "credit_history_id": credit_history_instance.pk,
                                    "utilized_points": points_to_redeem
                                })

                    for record in transactions:
                        loyalty_points_credit_history_instance = LoyaltyPointsCreditHistory.objects.filter(
                            pk=record["credit_history_id"]
                        ).first()
                        
                        loyalty_points_redeem_history_instance = LoyaltyPointsRedeemHistory(
                            customer = customer_instance,
                            order = master_order_instance,
                            credit_history = loyalty_points_credit_history_instance,
                            points_redeemed = record["utilized_points"],
                            redeem_datetime = timezone.now(), # timezone.localtime(timezone.now(), timezone='Asia/Kolkata')
                            redeemed_by = points_redeemed_by,
                            vendor = vendor_instance
                        )

                        loyalty_points_redeem_history_instance.save()

                        loyalty_points_credit_history_instance.total_points_redeemed = loyalty_points_credit_history_instance.total_points_redeemed + record["utilized_points"]
                        loyalty_points_credit_history_instance.balance_points = loyalty_points_credit_history_instance.balance_points - record["utilized_points"]
                        loyalty_points_credit_history_instance.save()

                        customer_instance.loyalty_points_balance = customer_instance.loyalty_points_balance - record["utilized_points"]
                        customer_instance.save()

                    # WooCommerce syncing
                    # if is_wordpress == False:
                    #     woocommerce_platform = Platform.objects.filter(VendorId=vendor_id, Name="WooCommerce", isActive=True).first()

                    #     if woocommerce_platform:
                    #         woocommerce_customer_details = WooCommerce.get_customer_by_phone_number(customer_instance.Phone_Number, vendor_id)

                    #         if woocommerce_customer_details.status_code == 404:
                    #             pass

                    #         elif woocommerce_customer_details and woocommerce_customer_details.status_code == 200:
                    #             woocommerce_customer_details = woocommerce_customer_details.json()

                    #             if woocommerce_customer_details.get('id'):
                    #                 balance_update_response = WooCommerce.update_loyalty_points_balance_of_customer(
                    #                     woocommerce_customer_details.get('id'),
                    #                     customer_instance.loyalty_points_balance,
                    #                     vendor_id
                    #                 )

                    #                 if balance_update_response == True:
                    #                     notify(type=3, msg='0', desc='Loyalty points synced', stn=['POS'], vendorId=vendor_id)

                    #                 else:
                    #                     transaction.set_rollback(True)
                    #                     return Response("WooCommerce syncing error", status=status.HTTP_400_BAD_REQUEST)

                    #         else:
                    #             transaction.set_rollback(True)
                        #             return Response("WooCommerce syncing error", status=status.HTTP_400_BAD_REQUEST)

                    koms_order = KOMSOrder.objects.filter(master_order=master_order_instance.pk).first()
            
                    waiteOrderUpdate(orderid=koms_order.pk, language=language, vendorId=vendor_id) # call socket
                    
                    return Response("Points redeemed", status=status.HTTP_200_OK)

        else:
            return Response("Cannot redeemed point of Guest", status=status.HTTP_400_BAD_REQUEST)
        

def loyalty_points_redeem(vendor_id, customer_id, master_order_id, is_wordpress, points_utilized, points_redeemed_by):
    is_redeemed = False

    if not all((vendor_id, customer_id, master_order_id)):
        return is_redeemed

    if is_wordpress is None:
        return is_redeemed

    try:
        vendor_id, customer_id = map(int, (vendor_id, customer_id))
    except ValueError:
        return is_redeemed

    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()
    customer_instance = Customer.objects.filter(pk=customer_id, VendorId=vendor_id).first()
    master_order_instance = Order.objects.filter(pk=master_order_id, vendorId=vendor_id).first()

    if not all((vendor_instance, customer_instance, master_order_instance)):
        return is_redeemed
    
    with transaction.atomic():
        if (master_order_instance.customerId.FirstName != "Guest") and (master_order_instance.customerId.Phone_Number != "0"):
            loyalty_program_settings = LoyaltyProgramSettings.objects.filter(vendor=vendor_id).first()

            if not loyalty_program_settings:
                return is_redeemed

            loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(
                customer=master_order_instance.customerId.pk,
                is_expired=False,
                balance_points__gt=0,
                vendor=vendor_id
            ).order_by("expiry_date")

            points_total = 0
            points_to_redeem = 0
            transactions = []

            if customer_instance.loyalty_points_balance > 0:
                for credit_history_instance in loyalty_points_credit_history:
                    if (credit_history_instance.balance_points == points_utilized):
                        if (credit_history_instance.points_credited == points_utilized):
                            LoyaltyPointsRedeemHistory.objects.create(
                                customer = customer_instance,
                                order = master_order_instance,
                                credit_history = credit_history_instance,
                                points_redeemed = points_utilized,
                                redeem_datetime = timezone.now(), # timezone.localtime(timezone.now(), timezone='Asia/Kolkata')
                                redeemed_by = points_redeemed_by,
                                vendor = vendor_instance
                            )

                            credit_history_instance.total_points_redeemed = points_utilized
                            credit_history_instance.balance_points = 0
                            credit_history_instance.save()

                            customer_instance.loyalty_points_balance = customer_instance.loyalty_points_balance - points_utilized
                            customer_instance.save()

                            break
                    
                        else:
                            LoyaltyPointsRedeemHistory.objects.create(
                                customer = customer_instance,
                                order = master_order_instance,
                                credit_history = credit_history_instance,
                                points_redeemed = points_utilized,
                                redeem_datetime = timezone.now(), # timezone.localtime(timezone.now(), timezone='Asia/Kolkata')
                                redeemed_by = points_redeemed_by,
                                vendor = vendor_instance
                            )

                            credit_history_instance.total_points_redeemed = credit_history_instance.total_points_redeemed + points_utilized
                            credit_history_instance.balance_points = 0
                            credit_history_instance.save()

                            customer_instance.loyalty_points_balance = customer_instance.loyalty_points_balance - points_utilized
                            customer_instance.save()
                            
                            break

                    elif (credit_history_instance.balance_points > points_utilized):
                        LoyaltyPointsRedeemHistory.objects.create(
                            customer = customer_instance,
                            order = master_order_instance,
                            credit_history = credit_history_instance,
                            points_redeemed = points_utilized,
                            redeem_datetime = timezone.now(), # timezone.localtime(timezone.now(), timezone='Asia/Kolkata')
                            redeemed_by = points_redeemed_by,
                            vendor = vendor_instance
                        )

                        credit_history_instance.total_points_redeemed = credit_history_instance.total_points_redeemed + points_utilized
                        credit_history_instance.balance_points = credit_history_instance.balance_points - points_utilized
                        credit_history_instance.save()

                        customer_instance.loyalty_points_balance = customer_instance.loyalty_points_balance - points_utilized
                        customer_instance.save()
                        
                        break

                    else:
                        if (points_total != points_utilized) and (points_to_redeem >= 0):
                            points_to_redeem = points_utilized - points_total

                            if (credit_history_instance.balance_points < points_to_redeem) or \
                            (credit_history_instance.balance_points == points_to_redeem):
                                points_total = points_total + credit_history_instance.balance_points
                                
                                transactions.append({
                                    "credit_history_id": credit_history_instance.pk,
                                    "utilized_points": credit_history_instance.balance_points
                                })

                            elif (credit_history_instance.balance_points > points_to_redeem):
                                points_total = points_total + points_to_redeem
                                
                                transactions.append({
                                    "credit_history_id": credit_history_instance.pk,
                                    "utilized_points": points_to_redeem
                                })
                        
                        else:
                            for record in transactions:
                                loyalty_points_credit_history_instance = LoyaltyPointsCreditHistory.objects.filter(
                                    pk=record["credit_history_id"]
                                ).first()

                                loyalty_points_redeem_history_instance = LoyaltyPointsRedeemHistory(
                                    customer = customer_instance,
                                    order = master_order_instance,
                                    credit_history = loyalty_points_credit_history_instance,
                                    points_redeemed = record["utilized_points"],
                                    redeem_datetime = timezone.now(), # timezone.localtime(timezone.now(), timezone='Asia/Kolkata')
                                    redeemed_by = points_redeemed_by,
                                    vendor = vendor_instance
                                )

                                loyalty_points_redeem_history_instance.save()

                                loyalty_points_credit_history_instance.total_points_redeemed = loyalty_points_credit_history_instance.total_points_redeemed + record["utilized_points"]
                                loyalty_points_credit_history_instance.balance_points = loyalty_points_credit_history_instance.balance_points - record["utilized_points"]
                                loyalty_points_credit_history_instance.save()

                                customer_instance.loyalty_points_balance = customer_instance.loyalty_points_balance - record["utilized_points"]
                                customer_instance.save()

                                # WooCommerce syncing
                                # if is_wordpress == False:
                                #     woocommerce_platform = Platform.objects.filter(VendorId=vendor_id, Name="WooCommerce", isActive=True).first()

                                #     if woocommerce_platform:
                                #         woocommerce_customer_details = WooCommerce.get_customer_by_phone_number(customer_instance.Phone_Number, vendor_id)

                                #         if woocommerce_customer_details.status_code == 404:
                                #             pass

                                #         elif woocommerce_customer_details and woocommerce_customer_details.status_code == 200:
                                #             woocommerce_customer_details = woocommerce_customer_details.json()

                                #             if woocommerce_customer_details.get('id'):
                                #                 balance_update_response = WooCommerce.update_loyalty_points_balance_of_customer(
                                #                     woocommerce_customer_details.get('id'),
                                #                     customer_instance.loyalty_points_balance,
                                #                     vendor_id
                                #                 )

                                #                 if balance_update_response == True:
                                #                     pass

                                #                 else:
                                #                     transaction.set_rollback(True)
                                #                     return is_redeemed

                                #         else:
                                #             transaction.set_rollback(True)
                                #             return is_redeemed
                            break

                is_redeemed = True
                return is_redeemed
            
            return is_redeemed


class DiscountCouponModelViewSet(viewsets.ModelViewSet):
    queryset = Order_Discount.objects.all().order_by('-pk')
    serializer_class = DiscountCouponModelSerializer
    filter_class = DiscountCouponFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    search_fields = ("discountName", "discountCode", "value")
    pagination_class = CustomPagination
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]

    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            return Order_Discount.objects.filter(vendorId=vendor_id).order_by("-pk")
        
        return Order_Discount.objects.none()

    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class StationModelViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all().order_by('-pk')
    serializer_class = StationModelSerializer
    filter_class = StationFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    search_fields = ('station_name',)
    pagination_class = CustomPagination
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]

    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            return Station.objects.filter(vendorId=vendor_id).order_by("-pk")
        
        return Station.objects.none()

    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ChefModelViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by('-pk')
    serializer_class = ChefModelSerializer
    filter_class = ChefFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    search_fields = ('first_name', 'last_name',)
    pagination_class = CustomPagination
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]

    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId', None)

        if vendor_id:
            return Staff.objects.filter(vendorId=vendor_id).order_by("-pk")
        
        return Staff.objects.none()

    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class BannerModelViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all().order_by('-pk')
    serializer_class = BannerModelSerializer
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]
    
    def get_queryset(self):
        # vendor_id = self.request.query_params.get('vendorId', None)
        vendor_id = self.request.GET.get('vendorId')

        if vendor_id:
            platform_type = self.request.GET.get('platform_type')
            
            if platform_type:
                return Banner.objects.filter(platform_type=platform_type, vendor=vendor_id).order_by("-pk")
            
            return Banner.objects.filter(vendor=vendor_id).order_by("-pk")
        
        return Banner.objects.none()
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        data = {"banners": serializer.data}
        
        return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
def top_selling_products_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    order_type = request.GET.get('type')
    is_download = request.GET.get('download')
    top_number = request.GET.get('top')
    sort_by = request.GET.get('sort')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)

    if is_download not in ("false", "true"):
        return Response("Invalid download parameter", status=status.HTTP_400_BAD_REQUEST)

    try:
        top_number = int(top_number)
    except ValueError:
        return Response("Invalid top parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if sort_by not in ("ascending", "descending"):
        return Response("Invalid sort parameter", status=status.HTTP_400_BAD_REQUEST)
    
    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    if order_type == "all":
        order_items = Order_content.objects.filter(
            orderId__order_status=10,
            orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
            orderId__master_order__OrderDate__date__range=(start_date, end_date),
            orderId__master_order__vendorId=vendor_id,
            orderId__vendorId=vendor_id,
        ).exclude(status=5)
    
    elif order_type == "delivery":
        order_items = Order_content.objects.filter(
            orderId__order_status=10,
            orderId__master_order__orderType=OrderType.get_order_type_value('DELIVERY'),
            orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
            orderId__master_order__OrderDate__date__range=(start_date, end_date),
            orderId__master_order__vendorId=vendor_id,
            orderId__vendorId=vendor_id,
        ).exclude(status=5)

    elif order_type == "pickup":
        order_items = Order_content.objects.filter(
            orderId__order_status=10,
            orderId__master_order__orderType=OrderType.get_order_type_value('PICKUP'),
            orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
            orderId__master_order__OrderDate__date__range=(start_date, end_date),
            orderId__master_order__vendorId=vendor_id,
            orderId__vendorId=vendor_id,
        ).exclude(status=5)

    elif order_type == "dinein":
        order_items = Order_content.objects.filter(
            orderId__order_status=10,
            orderId__master_order__orderType=OrderType.get_order_type_value('DINEIN'),
            orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
            orderId__master_order__OrderDate__date__range=(start_date, end_date),
            orderId__master_order__vendorId=vendor_id,
            orderId__vendorId=vendor_id,
        ).exclude(status=5)

    elif order_type == "online":
        if platform:
            order_items = Order_content.objects.filter(
                orderId__order_status=10,
                orderId__master_order__platform=platform.pk,
                orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                orderId__master_order__OrderDate__date__range=(start_date, end_date),
                orderId__master_order__vendorId=vendor_id,
                orderId__vendorId=vendor_id,
            ).exclude(status=5)

        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)
        
    elif order_type == "offline":
        if platform:
            order_items = Order_content.objects.filter(
                orderId__order_status=10,
                orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                orderId__master_order__OrderDate__date__range=(start_date, end_date),
                orderId__master_order__vendorId=vendor_id,
                orderId__vendorId=vendor_id,
            ).exclude(status=5, orderId__master_order__platform=platform.pk)

        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)

    else:
        return Response("Invalid type parameter", status=status.HTTP_400_BAD_REQUEST)

    top_selling_items = order_items.values('SKU').distinct() \
        .annotate(quantity_sold=ExpressionWrapper(Sum('quantity'),output_field=IntegerField())) \
        .filter(quantity_sold__gt=0).order_by('-quantity_sold')[:top_number]
    
    if sort_by == "descending":
        pass

    elif sort_by == "ascending":
        top_selling_items = sorted(top_selling_items, key=itemgetter('quantity_sold'))

    else:
        return Response("Invalid sort parameter", status=status.HTTP_400_BAD_REQUEST)
    
    list_of_items = []

    if is_download.lower() == "false":
        if order_items.exists():
            for item in top_selling_items:
                image_list = []

                products = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()
                
                images = ProductImage.objects.filter(product=products.pk)

                for image in images:
                    if image.url:
                        image_list.append(image.url)

                item['product_id'] = products.pk
                item['product_name'] = products.productName
                item['image'] = image_list[0] if len(image_list)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
                item['price'] = products.productPrice
                item['total_sale'] = item['quantity_sold'] * products.productPrice

                list_of_items.append(item)

        return JsonResponse({
            "top_selling_products": list_of_items
        })
    
    elif is_download.lower() == "true":
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        # Create a new Excel workbook and select the active sheet
        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.append(['Start Date', f'{formatted_start_date}'])
        sheet.append(['End Date', f'{formatted_end_date}'])
        sheet.append(['Order Type', f'{order_type}'])
        sheet.append(['Top', f'{top_number}'])
        sheet.append(['Sorted by', f'{sort_by}'])
        sheet.append(['Total records', f'{len(top_selling_items)}'])
        sheet.append([''])

        # Write headers
        sheet.append(['Product Name', 'Quantity Sold', 'Unit Price (Rs.)', 'Total Sale (Rs.)'])

        if order_items.exists():    
            for item in top_selling_items:
                products = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()

                sheet.append([
                    products.productName,
                    item['quantity_sold'],
                    products.productPrice,
                    item['quantity_sold'] * products.productPrice
                ])
        
        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Top_selling_products_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)

    else:
        return Response("Invalid 'download' key", status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def most_repeating_customers_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    order_type = request.GET.get('type')
    is_download = request.GET.get('download')
    top_number = request.GET.get('top')
    sort_by = request.GET.get('sort')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if not is_download:
        is_download = "false"
    
    else:
        is_download = str(is_download)

    try:
        top_number = int(top_number)
    except ValueError:
        return Response("Invalid top parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if not sort_by:
        sort_by = "descending "

    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    if order_type == "all":
        orders = Order.objects.filter(
            Status=OrderStatus.get_order_status_value('COMPLETED'),
            OrderDate__date__range=(start_date, end_date),
            vendorId=vendor_id
        )
    
    elif order_type == "delivery":
        orders = Order.objects.filter(
            orderType=OrderType.get_order_type_value('DELIVERY'),
            Status=OrderStatus.get_order_status_value('COMPLETED'),
            OrderDate__date__range=(start_date, end_date),
            vendorId=vendor_id,
        )
    
    elif order_type == "pickup":
        orders = Order.objects.filter(
            orderType=OrderType.get_order_type_value('PICKUP'),
            Status=OrderStatus.get_order_status_value('COMPLETED'),
            OrderDate__date__range=(start_date, end_date),
            vendorId=vendor_id
        )

    elif order_type == "dinein":
        orders = Order.objects.filter(
            orderType=OrderType.get_order_type_value('DINEIN'),
            Status=OrderStatus.get_order_status_value('COMPLETED'),
            OrderDate__date__range=(start_date, end_date),
            vendorId=vendor_id
        )

    elif order_type == "online":
        if platform:
            orders = Order.objects.filter(
                platform=platform.pk,
                Status=OrderStatus.get_order_status_value('COMPLETED'),
                OrderDate__date__range=(start_date, end_date),
                vendorId=vendor_id
            )
        
        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)
        
    elif order_type == "offline":
        if platform:
            orders = Order.objects.filter(
                Status=OrderStatus.get_order_status_value('COMPLETED'),
                OrderDate__date__range=(start_date, end_date),
                vendorId=vendor_id
            ).exclude(platform=platform.pk)
        
        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)
    
    else:
        return Response("Invalid type parameter", status=status.HTTP_400_BAD_REQUEST)
    
    top_customers = orders.values('customerId').distinct() \
        .annotate(customer_count=Count('customerId')) \
        .filter(customer_count__gt=0) \
        .order_by('-customer_count')[:top_number]

    if sort_by == "descending":
        pass

    elif sort_by == "ascending":
        top_customers = sorted(top_customers, key=itemgetter('customer_count'))

    else:
        return Response("Invalid sort parameter", status=status.HTTP_400_BAD_REQUEST)

    customer_details = []
    
    if is_download.lower() == "false":
        for customer in top_customers:
            if order_type == "all":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)
            
            elif order_type == "delivery":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__orderType=OrderType.get_order_type_value('DELIVERY'),
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "pickup":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__orderType=OrderType.get_order_type_value('PICKUP'),
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "dinein":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__orderType=OrderType.get_order_type_value('DINEIN'),
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "online":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__platform=platform.pk,
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "offline":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5, orderId__master_order__platform=platform.pk)

            list_of_items = []
            
            if order_items.exists():
                top_selling_items = order_items.values('SKU').distinct() \
                    .annotate(quantity_sold=ExpressionWrapper(Sum('quantity'), output_field=IntegerField())) \
                    .filter(quantity_sold__gt=0) \
                    .order_by('-quantity_sold')[:10]
                
                for item in top_selling_items:
                    image_list = []

                    products = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()
                    
                    images = ProductImage.objects.filter(product=products.pk)

                    for image in images:
                        if image.url:
                            image_list.append(image.url)

                    item['product_id'] = products.pk
                    item['product_name'] = products.productName
                    item['image'] = image_list[0] if len(image_list)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
                    item['price'] = products.productPrice
                    item['total_sale'] = item['quantity_sold'] * products.productPrice

                    list_of_items.append(item)
        
            customer_orders = Order.objects.filter(
                customerId=customer["customerId"],
                Status=OrderStatus.get_order_status_value('COMPLETED'),
                OrderDate__date__range=(start_date, end_date),
                vendorId=vendor_id
            )

            total_orders_count = customer_orders.count()
            delivery_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DELIVERY')).count()
            pickup_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('PICKUP')).count()
            dinein_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DINEIN')).count()

            if platform:
                online_orders_count = customer_orders.filter(platform=platform.pk).count()
                offline_orders_count = customer_orders.exclude(platform=platform.pk).count()
            
            customer_info = Customer.objects.filter(pk=customer["customerId"]).first()

            customer_address = Address.objects.filter(customer=customer["customerId"], type='shipping_address', is_selected=True).first()

            loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(customer=customer["customerId"])

            sum_of_points_credited = loyalty_points_credit_history.aggregate(Sum('points_credited'))['points_credited__sum']
            sum_of_points_redeemed = loyalty_points_credit_history.aggregate(Sum('total_points_redeemed'))['total_points_redeemed__sum']

            if not sum_of_points_credited:
                sum_of_points_credited = 0

            if not sum_of_points_redeemed:
                sum_of_points_redeemed = 0
            
            if customer_address:    
                customer_details.append({
                    "customer_id": customer["customerId"],
                    "first_name": customer_info.FirstName,
                    "last_name": customer_info.LastName if customer_info.LastName else "",
                    "phone_number": customer_info.Phone_Number,
                    "email": customer_info.Email if customer_info.Email else "",
                    "address_line_1": customer_address.address_line1 if customer_address.address_line1 else "",
                    "address_line_2": customer_address.address_line2 if customer_address.address_line2 else "",
                    "city": customer_address.city if customer_address.city else "",
                    "state": customer_address.state if customer_address.state else "",
                    "pincode": customer_address.zipcode if customer_address.zipcode else "",
                    "loyalty_points_balance": customer_info.loyalty_points_balance,
                    "total_points_credited": sum_of_points_credited,
                    "total_points_redeemed": sum_of_points_redeemed,
                    "total_orders_count": total_orders_count,
                    "online_orders_count": online_orders_count if platform else 0,
                    "offline_orders_count": offline_orders_count if platform else 0,
                    "delivery_orders_count": delivery_orders_count,
                    "pickup_orders_count": pickup_orders_count,
                    "dinein_orders_count": dinein_orders_count,
                    "most_ordered_items": list_of_items,
                })

            else:
                customer_details.append({
                "customer_id": customer["customerId"],
                "first_name": customer_info.FirstName,
                "last_name": customer_info.LastName if customer_info.LastName else "",
                "phone_number": customer_info.Phone_Number,
                "email": customer_info.Email if customer_info.Email else "",
                "address_line_1": "",
                "address_line_2": "",
                "city": "",
                "state": "",
                "pincode": "",
                "loyalty_points_balance": customer_info.loyalty_points_balance,
                "total_points_credited": sum_of_points_credited,
                "total_points_redeemed": sum_of_points_redeemed,
                "total_orders_count": total_orders_count,
                "online_orders_count": online_orders_count if platform else 0,
                "offline_orders_count": offline_orders_count if platform else 0,
                "delivery_orders_count": delivery_orders_count,
                "pickup_orders_count": pickup_orders_count,
                "dinein_orders_count": dinein_orders_count,
                "most_ordered_items": list_of_items,
            })

        return JsonResponse({
            "most_repeating_customers": customer_details
        })
    
    elif is_download.lower() == "true":
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        # Create a new Excel workbook and select the active sheet
        workbook = openpyxl.Workbook()
        sheet = workbook.active

        if platform:
            sheet.append(['Start Date', f'{formatted_start_date}'])
            sheet.append(['End Date', f'{formatted_end_date}'])
            sheet.append(['Order Type', f'{order_type}'])
            sheet.append(['Top', f'{top_number}'])
            sheet.append(['Sorted by', f'{sort_by}'])
            sheet.append(['Total records', f'{len(top_customers)}'])
            sheet.append([''])

            sheet.append([
                'Customer Name',
                'Phone Number',
                'Email ID',
                'Address',
                'Total Points Credited',
                'Total Points Redeemed',
                'Total Orders',
                'Total Online Orders',
                'Total Offline Orders',
                'Total Delivery Orders',
                'Total Pickup Orders',
                'Total DineIn Orders',
                'Most Ordered Items'
            ])

        else:    
            sheet.append(['Start Date', f'{formatted_start_date}'])
            sheet.append(['End Date', f'{formatted_end_date}'])
            sheet.append(['Order Type', f'{order_type}'])
            sheet.append(['Top', f'{top_number}'])
            sheet.append(['Sorted by', f'{sort_by}'])
            sheet.append(['Total records', f'{len(top_customers)}'])
            sheet.append([''])

            sheet.append([
                'Customer Name',
                'Phone Number',
                'Email ID',
                'Address',
                'Total Points Credited',
                'Total Points Redeemed',
                'Total Orders',
                'Total Delivery Orders',
                'Total Pickup Orders',
                'Total DineIn Orders',
                'Most Ordered Items'
            ])

        for customer in top_customers:
            if order_type == "all":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)
            
            elif order_type == "delivery":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__orderType=OrderType.get_order_type_value('DELIVERY'),
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "pickup":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__orderType=OrderType.get_order_type_value('PICKUP'),
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "dinein":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__orderType=OrderType.get_order_type_value('DINEIN'),
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "online":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__platform=platform.pk,
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5)

            elif order_type == "offline":
                order_items = Order_content.objects.filter(
                    orderId__order_status=10,
                    orderId__master_order__customerId=customer["customerId"],
                    orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                    orderId__master_order__OrderDate__date__range=(start_date, end_date),
                    orderId__master_order__vendorId=vendor_id,
                    orderId__vendorId=vendor_id,
                ).exclude(status=5, orderId__master_order__platform=platform.pk)

            top_selling_items = order_items.values('SKU').distinct() \
                .annotate(quantity_sold=ExpressionWrapper(Sum('quantity'), output_field=IntegerField())) \
                .filter(quantity_sold__gt=0) \
                .order_by('-quantity_sold')[:10]
            
            list_of_items = ''
            
            if order_items.exists():
                for item in top_selling_items:
                    product = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()

                    if list_of_items:
                        list_of_items = list_of_items + ", " + product.productName
                    else:
                        list_of_items = product.productName
        
            customer_orders = Order.objects.filter(
                customerId=customer["customerId"],
                Status=OrderStatus.get_order_status_value('COMPLETED'),
                OrderDate__date__range=(start_date, end_date),
                vendorId=vendor_id
            )
            total_orders_count = customer_orders.count()
            delivery_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DELIVERY')).count()
            pickup_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('PICKUP')).count()
            dinein_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DINEIN')).count()

            if platform:
                online_orders_count = customer_orders.filter(platform=platform.pk).count()
                offline_orders_count = customer_orders.exclude(platform=platform.pk).count()
            
            customer_info = Customer.objects.filter(pk=customer["customerId"]).first()

            customer_address = Address.objects.filter(customer=customer["customerId"], type='shipping_address', is_selected=True).first()

            loyalty_points_credit_history = LoyaltyPointsCreditHistory.objects.filter(customer=customer["customerId"])

            sum_of_points_credited = loyalty_points_credit_history.aggregate(Sum('points_credited'))['points_credited__sum']
            sum_of_points_redeemed = loyalty_points_credit_history.aggregate(Sum('total_points_redeemed'))['total_points_redeemed__sum']

            if not sum_of_points_credited:
                sum_of_points_credited = 0

            if not sum_of_points_redeemed:
                sum_of_points_redeemed = 0

            if customer_info.FirstName and customer_info.LastName:
                customer_name = customer_info.FirstName + " " + customer_info.LastName
            elif customer_info.FirstName and not customer_info.LastName:
                customer_name = customer_info.FirstName

            if customer_address:
                address_line_1 = customer_address.address_line1 if customer_address.address_line1 else ""
                address_line_2 = customer_address.address_line2 if customer_address.address_line2 else ""
                city = customer_address.city if customer_address.city else ""
                state = customer_address.state if customer_address.state else ""
                country = customer_address.country if customer_address.country else ""
                zipcode = customer_address.zipcode if customer_address.zipcode else ""
                
                address = address_line_1 + ", " + address_line_2 + ", " + city + ", " + state + ", " + country + ", " + zipcode
            
            else:
                address = ""
            
            if platform:
                sheet.append([
                    customer_name,
                    customer_info.Phone_Number,
                    customer_info.Email if customer_info.Email else "",
                    address,
                    sum_of_points_credited,
                    sum_of_points_redeemed,
                    total_orders_count,
                    online_orders_count,
                    offline_orders_count,
                    delivery_orders_count,
                    pickup_orders_count,
                    dinein_orders_count,
                    list_of_items
                ])

            else:
                sheet.append([
                    customer_name,
                    customer_info.Phone_Number,
                    customer_info.Email if customer_info.Email else "",
                    address,
                    sum_of_points_credited,
                    sum_of_points_redeemed,
                    total_orders_count,
                    delivery_orders_count,
                    pickup_orders_count,
                    dinein_orders_count,
                    list_of_items
                ])
        
        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Most_repeating_customers_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)
    
    else:
        return Response("Invalid 'download' key", status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def customers_redeemed_most_points_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    # order_type = request.GET.get('type')
    is_download = request.GET.get('download')
    top_number = request.GET.get('top')
    sort_by = request.GET.get('sort')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if not is_download:
        is_download = "false"
    
    else:
        is_download = str(is_download)

    try:
        top_number = int(top_number)
    except ValueError:
        return Response("Invalid top parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if not sort_by:
        sort_by = "descending "
    
    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    orders = Order.objects.filter(
        Status=OrderStatus.get_order_status_value('COMPLETED'),
        OrderDate__date__range=(start_date, end_date),
        vendorId=vendor_id,
    )
    
    top_customers = LoyaltyPointsRedeemHistory.objects.filter(
        vendor=vendor_id,
        redeem_datetime__date__range=(start_date, end_date)
    ).values('customer').distinct() \
        .annotate(total_points_redeemed=Sum('points_redeemed')) \
        .filter(total_points_redeemed__gt=0) \
        .order_by('-total_points_redeemed')[:top_number]

    if sort_by == "descending":
        pass

    elif sort_by == "ascending":
        top_customers = sorted(top_customers, key=itemgetter('total_points_redeemed'))

    else:
        return Response("Invalid sort parameter", status=status.HTTP_400_BAD_REQUEST)

    customer_details = []
    
    if is_download.lower() == "false":
        for customer in top_customers:
            order_items = Order_content.objects.filter(
                orderId__order_status=10,
                orderId__master_order__customerId=customer["customer"],
                orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                orderId__master_order__OrderDate__date__range=(start_date, end_date),
                orderId__master_order__vendorId=vendor_id,
                orderId__vendorId=vendor_id,
            ).exclude(status=5)
            
            list_of_items = []

            if order_items.exists():
                top_selling_items = order_items.values('SKU').distinct() \
                    .annotate(quantity_sold=ExpressionWrapper(Sum('quantity'), output_field=IntegerField())) \
                    .filter(quantity_sold__gt=0) \
                    .order_by('-quantity_sold')[:10]
                
                for item in top_selling_items:
                    image_list = []

                    products = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()
                    
                    images = ProductImage.objects.filter(product=products.pk)

                    for image in images:
                        if image.url:
                            image_list.append(image.url)

                    item['product_id'] = products.pk
                    item['product_name'] = products.productName
                    item['image'] = image_list[0] if len(image_list)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
                    item['price'] = products.productPrice
                    item['total_sale'] = item['quantity_sold'] * products.productPrice

                    list_of_items.append(item)
        
            customer_orders = orders.filter(customerId=customer["customer"])

            total_orders_count = customer_orders.count()
            delivery_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DELIVERY')).count()
            pickup_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('PICKUP')).count()
            dinein_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DINEIN')).count()
            
            online_orders_count = 0
            offline_orders_count = 0
            
            if platform:
                online_orders_count = customer_orders.filter(platform=platform.pk).count()
                offline_orders_count = customer_orders.exclude(platform=platform.pk).count()

            customer_info = Customer.objects.filter(pk=customer["customer"]).first()

            customer_address = Address.objects.filter(customer=customer["customer"], type='shipping_address', is_selected=True).first()
            
            sum_of_points_credited = LoyaltyPointsCreditHistory.objects.filter(
                customer=customer["customer"],
                credit_datetime__date__range=(start_date, end_date)
            ).aggregate(total_points_credited=Sum('points_credited'))['total_points_credited'] or 0

            # sum_of_points_unclaimed = LoyaltyPointsCreditHistory.objects.filter(
            #     customer_id=customer_id,
            #     credit_datetime__range=(start_date, end_date)
            # ).aggregate(total_balance_points=Sum('balance_points'))['total_balance_points'] or 0
            
            if customer_address:    
                customer_details.append({
                    "customer_id": customer["customer"],
                    "first_name": customer_info.FirstName,
                    "last_name": customer_info.LastName if customer_info.LastName else "",
                    "phone_number": customer_info.Phone_Number,
                    "email": customer_info.Email if customer_info.Email else "",
                    "address_line_1": customer_address.address_line1 if customer_address.address_line1 else "",
                    "address_line_2": customer_address.address_line2 if customer_address.address_line2 else "",
                    "city": customer_address.city if customer_address.city else "",
                    "state": customer_address.state if customer_address.state else "",
                    "pincode": customer_address.zipcode if customer_address.zipcode else "",
                    "loyalty_points_balance": customer_info.loyalty_points_balance,
                    "total_points_redeemed": customer['total_points_redeemed'],
                    "total_points_credited": sum_of_points_credited,
                    # "total_points_unclaimed": sum_of_points_unclaimed,
                    "total_orders_count": total_orders_count,
                    "online_orders_count": online_orders_count,
                    "offline_orders_count": offline_orders_count,
                    "delivery_orders_count": delivery_orders_count,
                    "pickup_orders_count": pickup_orders_count,
                    "dinein_orders_count": dinein_orders_count,
                    "most_ordered_items": list_of_items,
                })

            else:
                customer_details.append({
                "customer_id": customer["customer"],
                "first_name": customer_info.FirstName,
                "last_name": customer_info.LastName if customer_info.LastName else "",
                "phone_number": customer_info.Phone_Number,
                "email": customer_info.Email if customer_info.Email else "",
                "address_line_1": "",
                "address_line_2": "",
                "city": "",
                "state": "",
                "pincode": "",
                "loyalty_points_balance": customer_info.loyalty_points_balance,
                "total_points_redeemed": customer['total_points_redeemed'],
                # "total_points_credited": sum_of_points_credited,
                # "total_points_unclaimed": sum_of_points_unclaimed,
                "total_orders_count": total_orders_count,
                "online_orders_count": online_orders_count,
                "offline_orders_count": offline_orders_count,
                "delivery_orders_count": delivery_orders_count,
                "pickup_orders_count": pickup_orders_count,
                "dinein_orders_count": dinein_orders_count,
                "most_ordered_items": list_of_items,
            })

        return JsonResponse({
            "customers_redeemed_most_points": customer_details
        })
    
    elif is_download.lower() == "true":
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        # Create a new Excel workbook and select the active sheet
        workbook = openpyxl.Workbook()
        sheet = workbook.active

        if platform:
            sheet.append(['Start Date', f'{formatted_start_date}'])
            sheet.append(['End Date', f'{formatted_end_date}'])
            # sheet.append(['Order Type', f'{order_type}'])
            sheet.append(['Top', f'{top_number}'])
            sheet.append(['Sorted by', f'{sort_by}'])
            sheet.append(['Total records', f'{len(top_customers)}'])
            sheet.append([''])

            sheet.append([
                'Customer Name',
                'Phone Number',
                'Email ID',
                'Address',
                # 'Total Points Credited',
                'Total Points Redeemed',
                'Total Orders',
                'Total Online Orders',
                'Total Offline Orders',
                'Total Delivery Orders',
                'Total Pickup Orders',
                'Total DineIn Orders',
                'Most Ordered Items'
            ])

        else:    
            sheet.append(['Start Date', f'{formatted_start_date}'])
            sheet.append(['End Date', f'{formatted_end_date}'])
            # sheet.append(['Order Type', f'{order_type}'])
            sheet.append(['Top', f'{top_number}'])
            sheet.append(['Sorted by', f'{sort_by}'])
            sheet.append(['Total records', f'{len(top_customers)}'])
            sheet.append([''])

            sheet.append([
                'Customer Name',
                'Phone Number',
                'Email ID',
                'Address',
                # 'Total Points Credited',
                'Total Points Redeemed',
                'Total Orders',
                'Total Delivery Orders',
                'Total Pickup Orders',
                'Total DineIn Orders',
                'Most Ordered Items'
            ])

        for customer in top_customers:
            order_items = Order_content.objects.filter(
                orderId__order_status=10,
                orderId__master_order__customerId=customer["customer"],
                orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
                orderId__master_order__OrderDate__date__range=(start_date, end_date),
                orderId__master_order__vendorId=vendor_id,
                orderId__vendorId=vendor_id,
            ).exclude(status=5)

            top_selling_items = order_items.values('SKU').distinct() \
                                .annotate(quantity_sold=ExpressionWrapper(Sum('quantity'), output_field=IntegerField())) \
                                .filter(quantity_sold__gt=0) \
                                .order_by('-quantity_sold')[:10]

            list_of_items = ''
              
            if order_items.exists():    
                for item in top_selling_items:
                    product = Product.objects.filter(PLU=item['SKU'], vendorId=vendor_id).first()

                    if list_of_items:
                        list_of_items = list_of_items + ", " + product.productName
                    else:
                        list_of_items = product.productName
    
            customer_orders = orders.filter(customerId=customer["customer"])

            total_orders_count = customer_orders.count()
            delivery_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DELIVERY')).count()
            pickup_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('PICKUP')).count()
            dinein_orders_count = customer_orders.filter(orderType=OrderType.get_order_type_value('DINEIN')).count()

            if platform:
                online_orders_count = customer_orders.filter(platform=platform.pk).count()
                offline_orders_count = customer_orders.exclude(platform=platform.pk).count()
            
            customer_info = Customer.objects.filter(pk=customer["customer"]).first()

            customer_address = Address.objects.filter(customer=customer["customer"], type='shipping_address', is_selected=True).first()

            # sum_of_points_credited = LoyaltyPointsCreditHistory.objects.filter(
            #     customer=customer_id,
            #     credit_datetime__date__range=(start_date, end_date)
            # ).aggregate(total_points_credited=Sum('points_credited'))['total_points_credited'] or 0

            # sum_of_points_unclaimed = LoyaltyPointsCreditHistory.objects.filter(
            #     customer_id=customer_id,
            #     credit_datetime__range=(start_date, end_date)
            # ).aggregate(total_balance_points=Sum('balance_points'))['total_balance_points'] or 0

            if customer_info.FirstName and customer_info.LastName:
                customer_name = customer_info.FirstName + " " + customer_info.LastName
            elif customer_info.FirstName and not customer_info.LastName:
                customer_name = customer_info.FirstName

            if customer_address:
                address_line_1 = customer_address.address_line1 if customer_address.address_line1 else ""
                address_line_2 = customer_address.address_line2 if customer_address.address_line2 else ""
                city = customer_address.city if customer_address.city else ""
                state = customer_address.state if customer_address.state else ""
                country = customer_address.country if customer_address.country else ""
                zipcode = customer_address.zipcode if customer_address.zipcode else ""
                
                address = address_line_1 + ", " + address_line_2 + ", " + city + ", " + state + ", " + country + ", " + zipcode
            
            else:
                address = ""
            
            if platform:
                sheet.append([
                customer_name,
                customer_info.Phone_Number,
                customer_info.Email if customer_info.Email else "",
                address,
                customer["total_points_redeemed"],
                # sum_of_points_credited,
                total_orders_count,
                online_orders_count,
                offline_orders_count,
                delivery_orders_count,
                pickup_orders_count,
                dinein_orders_count,
                list_of_items
            ])

            else:    
                sheet.append([
                    customer_name,
                    customer_info.Phone_Number,
                    customer_info.Email if customer_info.Email else "",
                    address,
                    customer["total_points_redeemed"],
                    # sum_of_points_credited,
                    total_orders_count,
                    delivery_orders_count,
                    pickup_orders_count,
                    dinein_orders_count,
                    list_of_items
                ])
        
        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Customers_redeemed_most_points_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)
    
    else:
        return Response("Invalid 'download' key", status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def finance_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    is_download = request.GET.get('download')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if not is_download:
        is_download = "false"
    
    else:
        is_download = str(is_download)

    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    orders = OrderPayment.objects.filter(
        status=True,
        orderId__OrderDate__date__range=(start_date, end_date),
        orderId__vendorId=vendor_id
    ).exclude(orderId__Status=OrderStatus.get_order_status_value('CANCELED'))

    delivery_orders = orders.filter(orderId__orderType=OrderType.get_order_type_value('DELIVERY'))
    pickup_orders = orders.filter(orderId__orderType=OrderType.get_order_type_value('PICKUP'))
    dinein_orders = orders.filter(orderId__orderType=OrderType.get_order_type_value('DINEIN'))
    cash_payment_orders = orders.filter(type=PaymentType.get_payment_number('CASH'))
    online_payment_orders = orders.filter(type=PaymentType.get_payment_number('ONLINE'))
    card_payment_orders = orders.filter(type=PaymentType.get_payment_number('CARD'))
    
    total_orders = orders.count()
    delivery_orders_count = delivery_orders.count()
    pickup_orders_count = pickup_orders.count()
    dinein_orders_count = dinein_orders.count()
    cash_payment_orders_count = cash_payment_orders.count()
    online_payment_orders_count = online_payment_orders.count()
    card_payment_orders_count = card_payment_orders.count()
    
    total_tax_collected = orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
    tax_collected_from_delivery = delivery_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
    tax_collected_from_pickup = pickup_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
    tax_collected_from_dinein = dinein_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
    tax_collected_from_cash_payment = cash_payment_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
    tax_collected_from_online_payment = online_payment_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
    tax_collected_from_card_payment = card_payment_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0

    total_orders_aggregation = orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )

    delivery_orders_aggregation = delivery_orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )

    pickup_orders_aggregation = pickup_orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )

    dinein_orders_aggregation = dinein_orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )

    cash_payment_orders_aggregation = cash_payment_orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )

    online_payment_orders_aggregation = online_payment_orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )

    card_payment_orders_aggregation = card_payment_orders.aggregate(
        subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
        discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
    )
    
    total_revenue = total_orders_aggregation['subtotal_sum'] - total_orders_aggregation['discount_sum']
    revenue_from_delivery = delivery_orders_aggregation['subtotal_sum'] - delivery_orders_aggregation['discount_sum']
    revenue_from_pickup = pickup_orders_aggregation['subtotal_sum'] - pickup_orders_aggregation['discount_sum']
    revenue_from_dinein = dinein_orders_aggregation['subtotal_sum'] - dinein_orders_aggregation['discount_sum']
    revenue_from_cash_payment = cash_payment_orders_aggregation['subtotal_sum'] - cash_payment_orders_aggregation['discount_sum']
    revenue_from_online_payment = online_payment_orders_aggregation['subtotal_sum'] - online_payment_orders_aggregation['discount_sum']
    revenue_from_card_payment = card_payment_orders_aggregation['subtotal_sum'] - card_payment_orders_aggregation['discount_sum']
    
    online_orders_count = 0
    offline_orders_count = 0
        
    tax_collected_from_online = 0.0
    tax_collected_from_offline = 0.0

    revenue_from_online = 0.0
    revenue_from_offline = 0.0
    
    if platform:
        online_orders = orders.filter(orderId__platform=platform.pk)
        offline_orders = orders.exclude(orderId__platform=platform.pk)

        online_orders_count = online_orders.count()
        offline_orders_count = offline_orders.count()

        tax_collected_from_online = online_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_offline = offline_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0

        online_orders_aggregation = online_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        offline_orders_aggregation = offline_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )
        
        revenue_from_online = online_orders_aggregation['subtotal_sum'] - online_orders_aggregation['discount_sum']
        revenue_from_offline = offline_orders_aggregation['subtotal_sum'] - offline_orders_aggregation['discount_sum']
    
    if is_download.lower() == "false":
        return JsonResponse({
            "total_orders": total_orders,
            "delivery_orders_count": delivery_orders_count,
            "pickup_orders_count": pickup_orders_count,
            "dinein_orders_count": dinein_orders_count,
            "online_orders_count": online_orders_count,
            "offline_orders_count": offline_orders_count,
            "cash_payment_orders_count": cash_payment_orders_count,
            "online_payment_orders_count": online_payment_orders_count,
            "card_payment_orders_count": card_payment_orders_count,
            "total_tax_collected": round(total_tax_collected, 2),
            "tax_collected_from_delivery": round(tax_collected_from_delivery, 2),
            "tax_collected_from_pickup": round(tax_collected_from_pickup, 2),
            "tax_collected_from_dinein": round(tax_collected_from_dinein, 2),
            "tax_collected_from_online": round(tax_collected_from_online, 2),
            "tax_collected_from_offline": round(tax_collected_from_offline, 2),
            "tax_collected_from_cash_payment": round(tax_collected_from_cash_payment, 2),
            "tax_collected_from_online_payment": round(tax_collected_from_online_payment, 2),
            "tax_collected_from_card_payment": round(tax_collected_from_card_payment, 2),
            "total_revenue": round(total_revenue, 2),
            "revenue_from_delivery": round(revenue_from_delivery, 2),
            "revenue_from_pickup": round(revenue_from_pickup, 2),
            "revenue_from_dinein": round(revenue_from_dinein, 2),
            "revenue_from_online": round(revenue_from_online, 2),
            "revenue_from_offline": round(revenue_from_offline, 2),
            "revenue_from_cash_payment": round(revenue_from_cash_payment, 2),
            "revenue_from_online_payment": round(revenue_from_online_payment, 2),
            "revenue_from_card_payment": round(revenue_from_card_payment, 2)
        })
    
    elif is_download.lower() == "true":
        report_data = {
            'Delivery Orders': {'orders': delivery_orders_count, 'tax': tax_collected_from_delivery, 'revenue': revenue_from_delivery},
            'Pickup Orders': {'orders': pickup_orders_count, 'tax': tax_collected_from_pickup, 'revenue': revenue_from_pickup},
            'DineIn Orders': {'orders': dinein_orders_count, 'tax': tax_collected_from_dinein, 'revenue': revenue_from_dinein},
            'Total': {'orders': total_orders, 'tax': total_tax_collected, 'revenue': total_revenue},
            'Cash Payment': {'orders': cash_payment_orders_count, 'tax': tax_collected_from_cash_payment, 'revenue': revenue_from_cash_payment},
            'Online Payment': {'orders': online_payment_orders_count, 'tax': tax_collected_from_online_payment, 'revenue': revenue_from_online_payment},
            'Card Payment': {'orders': card_payment_orders_count, 'tax': tax_collected_from_card_payment, 'revenue': revenue_from_card_payment},
        }

        if platform:
            report_data['Online Orders'] = {'orders': online_orders_count, 'tax': tax_collected_from_online, 'revenue': revenue_from_online}
            report_data['Offline Orders'] = {'orders': offline_orders_count, 'tax': tax_collected_from_offline, 'revenue': revenue_from_offline}

        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.append(['Start Date', f'{formatted_start_date}'])
        sheet.append(['End Date', f'{formatted_end_date}'])
        sheet.append([''])

        sheet.append(['Category', 'Total Orders', 'Tax Collected', 'Revenue Generated'])

        for key, value in report_data.items():
            sheet.append([key, value["orders"], value["tax"], value["revenue"]])
        
        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Finance_Report_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)
    
    else:
        return Response("Invalid 'download' key", status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def footfall_revenue_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    is_download = request.GET.get('download')
    filter_by = request.GET.get('filter')
    filter_type = request.GET.get('type')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if not is_download:
        is_download = "false"
    
    else:
        is_download = str(is_download)

    if filter_by not in ('date', 'month', 'day', 'hour'):
        return Response("Invalid filter parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if filter_type not in ('footfall', 'revenue'):
        return Response("Invalid type parameter", status=status.HTTP_400_BAD_REQUEST)
    
    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    all_orders = OrderPayment.objects.filter(
        status=True,
        orderId__OrderDate__date__range=(start_date, end_date),
        orderId__vendorId=vendor_id
    ).exclude(orderId__Status=OrderStatus.get_order_status_value('CANCELED'))

    # ISO standard mapping
    weekday_names = {
        1: 'Monday',
        2: 'Tuesday',
        3: 'Wednesday',
        4: 'Thursday',
        5: 'Friday',
        6: 'Saturday',
        7: 'Sunday'
    }
    
    if filter_type == 'footfall':
        if filter_by == 'date':
            top_data = all_orders.values('orderId__OrderDate__date').distinct() \
                        .annotate(total_orders=Count('orderId__id')) \
                        .filter(total_orders__gt=0) \
                        .order_by('-total_orders')[:5]

        
        elif filter_by == 'month':
            top_data = all_orders.annotate(order_month=ExtractMonth('orderId__OrderDate')) \
                        .values('order_month').distinct() \
                        .annotate(total_orders=Count('orderId__id')) \
                        .filter(total_orders__gt=0) \
                        .order_by('-total_orders')[:6]
        
        elif filter_by == 'day':
            top_data = all_orders.annotate(weekday=ExtractWeekDay('orderId__OrderDate')) \
                .values('weekday').distinct() \
                .annotate(total_orders=Count('orderId__id')) \
                .filter(total_orders__gt=0) \
                .order_by('-total_orders')[:4]

            weekday_counts = defaultdict(int)

            for order in all_orders:
                weekday = order.orderId.OrderDate.weekday() + 1
                weekday_counts[weekday] += 1

            non_zero_weekdays = {}
            
            for weekday, count in weekday_counts.items():
                if count > 0:
                    non_zero_weekdays[weekday] = count

            top_data = sorted(non_zero_weekdays, key=non_zero_weekdays.get, reverse=True)[:4]
        
        elif filter_by == 'hour':
            top_data = all_orders.annotate(order_hour=ExtractHour('orderId__OrderDate')) \
                        .values('order_hour').distinct() \
                        .annotate(total_orders=Count('orderId__id')) \
                        .filter(total_orders__gt=0) \
                        .order_by('-total_orders')[:5]
    
    elif filter_type == 'revenue':
        if filter_by == 'date':
            top_data = all_orders.values('orderId__OrderDate__date').distinct() \
                        .annotate(subtotal_sum=Sum('orderId__subtotal')) \
                        .filter(subtotal_sum__gt=0) \
                        .order_by('-subtotal_sum')[:5]

        elif filter_by == 'month':
            top_data = all_orders.annotate(order_month=ExtractMonth('orderId__OrderDate')) \
                        .values('order_month').distinct() \
                        .annotate(subtotal_sum=Sum('orderId__subtotal')) \
                        .filter(subtotal_sum__gt=0) \
                        .order_by('-subtotal_sum')[:6]
        
        elif filter_by == 'day':
            top_data = all_orders.annotate(weekday=(ExtractWeekDay('orderId__OrderDate'))) \
                        .values('weekday').distinct() \
                        .annotate(subtotal_sum=Sum('orderId__subtotal')) \
                        .filter(subtotal_sum__gt=0) \
                        .order_by('-subtotal_sum')[:4]
            
            weekday_subtotal_sum = defaultdict(int)

            for order in all_orders:
                weekday = order.orderId.OrderDate.weekday() + 1
                weekday_subtotal_sum[weekday] += order.orderId.subtotal

            non_zero_weekdays = {}

            for weekday, subtotal_sum in weekday_subtotal_sum.items():
                if subtotal_sum > 0:
                    non_zero_weekdays[weekday] = subtotal_sum

            top_data = sorted(non_zero_weekdays, key=non_zero_weekdays.get, reverse=True)[:4]
    
        elif filter_by == 'hour':
            top_data = all_orders.annotate(order_hour=ExtractHour('orderId__OrderDate')) \
                        .values('order_hour').distinct() \
                        .annotate(subtotal_sum=Sum('orderId__subtotal')) \
                        .filter(subtotal_sum__gt=0) \
                        .order_by('-subtotal_sum')[:5]
    
    filtered_data = []
    
    for instance in top_data:
        if filter_by == 'date':
            orders = all_orders.filter(orderId__OrderDate__date=instance['orderId__OrderDate__date'].strftime('%Y-%m-%d'))

            actual_instance = instance['orderId__OrderDate__date'].strftime('%Y-%m-%d')

        elif filter_by == 'month':
            orders = all_orders.filter(orderId__OrderDate__month=instance["order_month"])

            actual_instance = calendar.month_name[instance["order_month"]]
        
        elif filter_by == 'day':
            orders = all_orders.filter(orderId__OrderDate__week_day=instance+1)

            for key,value in weekday_names.items():
                if key == instance:
                    actual_instance = value

        elif filter_by == 'hour':
            orders = all_orders.filter(orderId__OrderDate__hour=instance['order_hour'])

            actual_instance = datetime.strptime(str(instance['order_hour']), '%H').strftime('%I%p') + ' - ' + \
            datetime.strptime(str(instance['order_hour'] + 1), '%H').strftime('%I%p')

        delivery_orders = orders.filter(orderId__orderType=OrderType.get_order_type_value('DELIVERY'))
        pickup_orders = orders.filter(orderId__orderType=OrderType.get_order_type_value('PICKUP'))
        dinein_orders = orders.filter(orderId__orderType=OrderType.get_order_type_value('DINEIN'))
        cash_payment_orders = orders.filter(type=PaymentType.get_payment_number('CASH'))
        online_payment_orders = orders.filter(type=PaymentType.get_payment_number('ONLINE'))
        card_payment_orders = orders.filter(type=PaymentType.get_payment_number('CARD'))

        total_orders = orders.count()
        delivery_orders_count = delivery_orders.count()
        pickup_orders_count = pickup_orders.count()
        dinein_orders_count = dinein_orders.count()
        cash_payment_orders_count = cash_payment_orders.count()
        online_payment_orders_count = online_payment_orders.count()
        card_payment_orders_count = card_payment_orders.count()
        
        total_tax_collected = orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_delivery = delivery_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_pickup = pickup_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_dinein = dinein_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_cash_payment = cash_payment_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_online_payment = online_payment_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
        tax_collected_from_card_payment = card_payment_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0

        total_orders_aggregation = orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        delivery_orders_aggregation = delivery_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        pickup_orders_aggregation = pickup_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        dinein_orders_aggregation = dinein_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        cash_payment_orders_aggregation = cash_payment_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        online_payment_orders_aggregation = online_payment_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )

        card_payment_orders_aggregation = card_payment_orders.aggregate(
            subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
            discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
        )
        
        total_revenue = total_orders_aggregation['subtotal_sum'] - total_orders_aggregation['discount_sum']
        revenue_from_delivery = delivery_orders_aggregation['subtotal_sum'] - delivery_orders_aggregation['discount_sum']
        revenue_from_pickup = pickup_orders_aggregation['subtotal_sum'] - pickup_orders_aggregation['discount_sum']
        revenue_from_dinein = dinein_orders_aggregation['subtotal_sum'] - dinein_orders_aggregation['discount_sum']
        revenue_from_cash_payment = cash_payment_orders_aggregation['subtotal_sum'] - cash_payment_orders_aggregation['discount_sum']
        revenue_from_online_payment = online_payment_orders_aggregation['subtotal_sum'] - online_payment_orders_aggregation['discount_sum']
        revenue_from_card_payment = card_payment_orders_aggregation['subtotal_sum'] - card_payment_orders_aggregation['discount_sum']
        
        online_orders_count = 0
        offline_orders_count = 0

        tax_collected_from_online = 0.0
        tax_collected_from_offline = 0.0

        revenue_from_online = 0.0
        revenue_from_offline = 0.0
        
        if platform:
            online_orders = orders.filter(orderId__platform=platform.pk)
            offline_orders = orders.exclude(orderId__platform=platform.pk)

            online_orders_count = online_orders.count()
            offline_orders_count = offline_orders.count()

            tax_collected_from_online = online_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0
            tax_collected_from_offline = offline_orders.aggregate(total_tax=Sum('orderId__tax'))['total_tax'] or 0.0

            online_orders_aggregation = online_orders.aggregate(
                subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
                discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
            )

            offline_orders_aggregation = offline_orders.aggregate(
                subtotal_sum=Coalesce(Sum('orderId__subtotal'), 0.0),
                discount_sum=Coalesce(Sum('orderId__discount'), 0.0)
            )
            
            revenue_from_online = online_orders_aggregation['subtotal_sum'] - online_orders_aggregation['discount_sum']
            revenue_from_offline = offline_orders_aggregation['subtotal_sum'] - offline_orders_aggregation['discount_sum']

        filtered_data.append({
            "instance": actual_instance,
            "total_orders": total_orders,
            "delivery_orders_count": delivery_orders_count,
            "pickup_orders_count": pickup_orders_count,
            "dinein_orders_count": dinein_orders_count,
            "offline_orders_count": offline_orders_count,
            "online_orders_count": online_orders_count,
            "cash_payment_orders_count": cash_payment_orders_count,
            "online_payment_orders_count": online_payment_orders_count,
            "card_payment_orders_count": card_payment_orders_count,
            "total_tax_collected": round(total_tax_collected, 2),
            "tax_collected_from_delivery": round(tax_collected_from_delivery, 2),
            "tax_collected_from_pickup": round(tax_collected_from_pickup, 2),
            "tax_collected_from_dinein": round(tax_collected_from_dinein, 2),
            "tax_collected_from_offline": round(tax_collected_from_offline, 2),
            "tax_collected_from_online": round(tax_collected_from_online, 2),
            "tax_collected_from_cash_payment": round(tax_collected_from_cash_payment, 2),
            "tax_collected_from_online_payment": round(tax_collected_from_online_payment, 2),
            "tax_collected_from_card_payment": round(tax_collected_from_card_payment, 2),
            "total_revenue": round(total_revenue, 2),
            "revenue_from_delivery": round(revenue_from_delivery, 2),
            "revenue_from_pickup": round(revenue_from_pickup, 2),
            "revenue_from_dinein": round(revenue_from_dinein, 2),
            "revenue_from_offline": round(revenue_from_offline, 2),
            "revenue_from_online": round(revenue_from_online, 2),
            "revenue_from_cash_payment": round(revenue_from_cash_payment, 2),
            "revenue_from_online_payment": round(revenue_from_online_payment, 2),
            "revenue_from_card_payment": round(revenue_from_card_payment, 2)
        })
    
    if is_download.lower() == "false":
        return JsonResponse({"data": filtered_data})
    
    elif is_download.lower() == "true":
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.append(['Start Date', f'{formatted_start_date}'])
        sheet.append(['End Date', f'{formatted_end_date}'])
        sheet.append(['Filtered by', f'{filter_by}'])
        sheet.append([''])

        if platform:
            sheet.append(['Order Count Data'])
            sheet.append([
                'Instance',
                'Total Orders',
                'Total Delivery Orders',
                'Total Pickup Orders',
                'Total DineIn Orders',
                'Total Offline Orders',
                'Total Online Orders',
                'Cash Payment Orders',
                'Online Payment Orders',
                'Card Payment Orders',
            ])

            for data in filtered_data:
                sheet.append([
                    data['instance'],
                    data['total_orders'],
                    data['delivery_orders_count'],
                    data['pickup_orders_count'],
                    data['dinein_orders_count'],
                    data['offline_orders_count'],
                    data['online_orders_count'],
                    data['cash_payment_orders_count'],
                    data['online_payment_orders_count'],
                    data['card_payment_orders_count'],
                ])

            sheet.append([''])
            sheet.append(['Tax Collection Data'])
            sheet.append([
                'Instance',
                'Total Tax Collected',
                'Tax Colllection from Delivery',
                'Tax Colllection from Pickup',
                'Tax Colllection from DineIn',
                'Tax Colllection from Offline Orders',
                'Tax Colllection from Online Orders',
                'Tax Colllection from Cash Payment',
                'Tax Colllection from Online Payment',
                'Tax Colllection from Card Payment',
            ])

            for data in filtered_data:
                sheet.append([
                    data['instance'],
                    data['total_tax_collected'],
                    data['tax_collected_from_delivery'],
                    data['tax_collected_from_pickup'],
                    data['tax_collected_from_dinein'],
                    data['tax_collected_from_offline'],
                    data['tax_collected_from_online'],
                    data['tax_collected_from_cash_payment'],
                    data['tax_collected_from_online_payment'],
                    data['tax_collected_from_card_payment'],
                ])
            
            sheet.append([''])
            sheet.append(['Revenue Generation Data'])
            sheet.append([
                'Instance',
                'Total Revenue Generated',
                'Revenue from Delivery',
                'Revenue from Pickup',
                'Revenue from DineIn',
                'Revenue from Offline Orders',
                'Revenue from Online Orders',
                'Revenue from Cash Payment',
                'Revenue from Online Payment',
                'Revenue from Card Payment',
            ])

            for data in filtered_data:
                sheet.append([
                    data['instance'],
                    data['total_revenue'],
                    data['revenue_from_delivery'],
                    data['revenue_from_pickup'],
                    data['revenue_from_dinein'],
                    data['revenue_from_offline'],
                    data['revenue_from_online'],
                    data['revenue_from_cash_payment'],
                    data['revenue_from_online_payment'],
                    data['revenue_from_card_payment'],
                ])

        else:
            sheet.append(['Order Count Data'])
            sheet.append([
                'Instance',
                'Total Orders',
                'Total Delivery Orders',
                'Total Pickup Orders',
                'Total DineIn Orders',
                'Cash Payment Orders',
                'Online Payment Orders',
                'Card Payment Orders',
            ])

            for data in filtered_data:
                sheet.append([
                    data['instance'],
                    data['total_orders'],
                    data['delivery_orders_count'],
                    data['pickup_orders_count'],
                    data['dinein_orders_count'],
                    data['cash_payment_orders_count'],
                    data['online_payment_orders_count'],
                    data['card_payment_orders_count'],
                ])

            sheet.append([''])
            sheet.append(['Tax Collection Data'])
            sheet.append([
                'Instance',
                'Total Tax Collected',
                'Tax Colllection from Delivery',
                'Tax Colllection from Pickup',
                'Tax Colllection from DineIn',
                'Tax Colllection from Cash Payment',
                'Tax Colllection from Online Payment',
                'Tax Colllection from Card Payment',
            ])

            for data in filtered_data:
                sheet.append([
                    data['instance'],
                    data['total_tax_collected'],
                    data['tax_collected_from_delivery'],
                    data['tax_collected_from_pickup'],
                    data['tax_collected_from_dinein'],
                    data['tax_collected_from_cash_payment'],
                    data['tax_collected_from_online_payment'],
                    data['tax_collected_from_card_payment'],
                ])
            
            sheet.append([''])
            sheet.append(['Revenue Generation Data'])
            sheet.append([
                'Instance',
                'Total Revenue Generated',
                'Revenue from Delivery',
                'Revenue from Pickup',
                'Revenue from DineIn',
                'Revenue from Cash Payment',
                'Revenue from Online Payment',
                'Revenue from Card Payment',
            ])

            for data in filtered_data:
                sheet.append([
                    data['instance'],
                    data['total_revenue'],
                    data['revenue_from_delivery'],
                    data['revenue_from_pickup'],
                    data['revenue_from_dinein'],
                    data['revenue_from_cash_payment'],
                    data['revenue_from_online_payment'],
                    data['revenue_from_card_payment'],
                ])
        
        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Footfall_Report_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)
    
    else:
        return Response("Invalid 'download' key", status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def order_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    is_download = request.GET.get('download')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if is_download not in ("false", "true"):
        return Response("Invalid download parameter", status=status.HTTP_400_BAD_REQUEST)
    
    all_order_details = order_count(start_date, end_date, "all", vendor_id)
    
    delivery_order_details = order_count(start_date, end_date, "delivery", vendor_id)

    pickup_order_details = order_count(start_date, end_date, "pickup", vendor_id)

    dinein_order_details = order_count(start_date, end_date, "dinein", vendor_id)

    online_order_details = order_count(start_date, end_date, "online", vendor_id)

    offline_order_details = order_count(start_date, end_date, "offline", vendor_id)

    order_count_details = {
        "All": all_order_details,
        "Delivery": delivery_order_details,
        "Pickup": pickup_order_details,
        "DineIn": dinein_order_details,
        "Online": online_order_details,
        "Offline": offline_order_details
    }
    
    if is_download == "false":    
        return JsonResponse(order_count_details)
    
    elif is_download == "true":
        platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()

        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.append(['Start Date', f'{formatted_start_date}'])
        sheet.append(['End Date', f'{formatted_end_date}'])
        sheet.append([''])

        sheet.append(["Category", "Total Orders", "Complete Orders", "Cancelled Orders", "Processing Orders"])

        for category, orders_info in order_count_details.items():
            if category == "Online" and not platform:
                pass
            
            else:
                sheet.append([
                    category,
                    orders_info.get("total_orders"),
                    orders_info.get("complete_orders"),
                    orders_info.get("cancelled_orders"),
                    orders_info.get("processing_orders")
                ])

        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Order_Count_Report_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)


@api_view(["GET"])
def cancel_order_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    order_type = request.GET.get('type')
    is_download = request.GET.get('download')
    top_number = request.GET.get('top')
    sort_by = request.GET.get('sort')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if is_download not in ("false", "true"):
        return Response("Invalid download parameter", status=status.HTTP_400_BAD_REQUEST)

    if order_type not in ("all", "delivery", "pickup", "dinein", "online", "offline"):
        return Response("Invalid type parameter", status=status.HTTP_400_BAD_REQUEST)

    try:
        top_number = int(top_number)
    except ValueError:
        return Response("Invalid top parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if sort_by not in ("ascending", "descending"):
        return Response("Invalid sort parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if order_type == "delivery":
        order_type_code = OrderType.get_order_type_value('DELIVERY')

    elif order_type == "pickup":
        order_type_code = OrderType.get_order_type_value('PICKUP')

    elif order_type == "dinein":
        order_type_code = OrderType.get_order_type_value('DINEIN')
    
    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    cancelled_orders = KOMSOrder.objects.filter(
        master_order__Status=OrderStatus.get_order_status_value('CANCELED'),
        master_order__OrderDate__date__range=(start_date, end_date),
        master_order__vendorId=vendor_id,
        vendorId=vendor_id
    )

    most_cancelled_products = Order_content.objects.filter(
        status=5,
        orderId__order_status=5,
        orderId__master_order__Status=OrderStatus.get_order_status_value('CANCELED'),
        orderId__master_order__OrderDate__date__range=(start_date, end_date),
        orderId__master_order__vendorId=vendor_id,
        orderId__vendorId=vendor_id
    )
    
    if order_type == "all":
        pass
    
    elif order_type == "online":
            if platform:
                cancelled_orders = cancelled_orders.filter(master_order__platform=platform.pk)

                most_cancelled_products = most_cancelled_products.filter(orderId__master_order__platform=platform.pk)
            
            else:
                return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)
            
    elif order_type == "offline":
        if platform:
            cancelled_orders = cancelled_orders.exclude(master_order__platform=platform.pk)

            most_cancelled_products = most_cancelled_products.exclude(orderId__master_order__platform=platform.pk)

        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)

    else:
        cancelled_orders = cancelled_orders.filter(master_order__orderType=order_type_code)

        most_cancelled_products = most_cancelled_products.filter(orderId__master_order__orderType=order_type_code)

    cancelled_orders_count = len(list(cancelled_orders.values_list('master_order', flat=True).distinct()))

    cancelled_products_count = most_cancelled_products.count()
    
    most_cancelled_products = most_cancelled_products.values('SKU').distinct() \
                            .annotate(cancel_count=Count('SKU')) \
                            .filter(cancel_count__gt=0) \
                            .order_by('-cancel_count')[:top_number]

    if sort_by == "descending":
        pass

    elif sort_by == "ascending":
        most_cancelled_products = sorted(most_cancelled_products, key=itemgetter('cancel_count'))

    cancelled_product_details = []
    
    for product in most_cancelled_products:
        product_info = Product.objects.filter(PLU=product["SKU"], vendorId=vendor_id).first()

        images = ProductImage.objects.filter(product=product_info.pk)

        image_list = []
        
        for image in images:
            if image.url:
                image_list.append(image.url)

        cancelled_product_details.append({
            'product_id': product_info.pk,
            'product_name': product_info.productName,
            'image': image_list[0] if len(image_list)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
            'price': product_info.productPrice,
            'cancel_count': product['cancel_count'],
            'cancelled_estimated_sale': product['cancel_count'] * product_info.productPrice
        })

    estimated_revenue_from_cancelled_orders = 0.0

    for product_detail in cancelled_product_details:
        estimated_revenue_from_cancelled_orders = estimated_revenue_from_cancelled_orders + product_detail["cancelled_estimated_sale"]

    if is_download == "false":    
        return JsonResponse({
            "cancelled_orders_count": cancelled_orders_count,
            "cancelled_products_count": cancelled_products_count,
            "cancelled_estimated_revenue": estimated_revenue_from_cancelled_orders,
            "cancelled_products": cancelled_product_details
        })
    
    elif is_download == "true":
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.append(['Start Date', f'{formatted_start_date}'])
        sheet.append(['End Date', f'{formatted_end_date}'])
        sheet.append(['Order Type', f'{order_type}'])
        sheet.append([''])

        sheet.append(["Cancelled Orders", "Cancelled Products", "Loss Made (Rs.)"])
        sheet.append([cancelled_orders_count, cancelled_products_count, estimated_revenue_from_cancelled_orders])

        sheet.append([''])

        sheet.append(['Cancelled Product Details'])
        sheet.append(['Top', top_number])
        sheet.append(['Sorted by', sort_by])

        sheet.append([''])

        sheet.append(['Product Name', 'Quantity Cancelled', 'Unit Price (Rs.)', 'Estimated Revenue (Rs.)'])

        for product_detail in cancelled_product_details:
            sheet.append([
                product_detail["product_name"],
                product_detail["cancel_count"],
                product_detail["price"],
                product_detail["cancelled_estimated_sale"]
            ])

        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Cancel_Order_Report_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)


@api_view(["GET"])
def pincode_report(request):
    vendor_id = request.GET.get("vendorId")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    order_type = request.GET.get('type')
    is_download = request.GET.get('download')
    top_number = request.GET.get('top')
    sort_by = request.GET.get('sort')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    if (((not start_date) or (not end_date)) or (start_date > end_date)):
        return Response("Invalid start date or end date", status=status.HTTP_400_BAD_REQUEST)
    
    if is_download not in ("false", "true"):
        return Response("Invalid download parameter", status=status.HTTP_400_BAD_REQUEST)

    if order_type not in ("all", "delivery", "pickup", "dinein", "online", "offline"):
        return Response("Invalid type parameter", status=status.HTTP_400_BAD_REQUEST)

    try:
        top_number = int(top_number)
    except ValueError:
        return Response("Invalid top parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if sort_by not in ("ascending", "descending"):
        return Response("Invalid sort parameter", status=status.HTTP_400_BAD_REQUEST)
    
    if order_type == "delivery":
        order_type_code = OrderType.get_order_type_value('DELIVERY')

    elif order_type == "pickup":
        order_type_code = OrderType.get_order_type_value('PICKUP')

    elif order_type == "dinein":
        order_type_code = OrderType.get_order_type_value('DINEIN')
    
    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()

    order_items = Order_content.objects.filter(
        orderId__order_status=10,
        orderId__master_order__Status=OrderStatus.get_order_status_value('COMPLETED'),
        orderId__master_order__orderpayment__status=True,
        orderId__master_order__OrderDate__date__range=(start_date, end_date),
        orderId__master_order__customerId__address__isnull=False,
        orderId__master_order__customerId__address__is_selected=True,
        orderId__vendorId=vendor_id
    ).exclude(status=5)
    
    if order_type == "all":
        pass
    
    elif order_type == "online":
        if platform:
            order_items = order_items.filter(orderId__master_order__platform=platform.pk)
        
        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)
            
    elif order_type == "offline":
        if platform:
            order_items = order_items.exclude(orderId__master_order__platform=platform.pk)
        
        else:
            return Response("Contact you administrator to activate the platform", status=status.HTTP_400_BAD_REQUEST)
            
    else:
        order_items = order_items.filter(orderId__master_order__orderType=order_type_code)

    top_pincodes = order_items.values('orderId__master_order__customerId__address__zipcode').distinct() \
                    .annotate(order_count=Count('orderId__master_order__pk', distinct=True)) \
                    .filter(order_count__gt=0) \
                    .order_by('-order_count')[:top_number]
    
    if sort_by == "ascending":
        top_pincodes = sorted(top_pincodes, key=itemgetter('order_count'))

    pincode_list = []

    # Initialize pgeocode
    nomi = pgeocode.Nominatim("in")
    
    for details in top_pincodes:
        order_items_by_area = order_items.filter(
            orderId__master_order__customerId__address__zipcode=details["orderId__master_order__customerId__address__zipcode"]
        )

        master_order_ids = set(order_items_by_area.values_list('orderId__master_order', flat=True))

        subtotal_sum = Order.objects.filter(pk__in=master_order_ids).aggregate(subtotal_sum=Sum('subtotal'))['subtotal_sum'] or 0.0

        most_ordered_items = order_items_by_area.values('SKU').distinct() \
                            .annotate(item_count=Sum('quantity')) \
                            .filter(item_count__gt=0) \
                            .order_by('-item_count')[:10]

        product_details = []
        
        for product in most_ordered_items:
            product_info = Product.objects.filter(PLU=product["SKU"], vendorId=vendor_id).first()

            images = ProductImage.objects.filter(product=product_info.pk)

            image_list = []
            
            for image in images:
                if image.url:
                    image_list.append(image.url)

            product_details.append({
                'product_id': product_info.pk,
                'product_name': product_info.productName,
                'image': image_list[0] if len(image_list)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                'price': product_info.productPrice,
                'quantity_sold': product['item_count'],
                'revenue': product['item_count'] * product_info.productPrice
            })

        # url = f'https://api.postalpincode.in/pincode/{details["customerId__address__zipcode"]}'

        # response = requests.get(url)
        # data = response.json()
        
        # locality_name = ""

        # if data and data[0]['Status'] == 'Success':
        #     locality_name = data[0]['PostOffice'][0]['Name']

        location = nomi.query_postal_code(details["orderId__master_order__customerId__address__zipcode"])

        locality = ""

        if (not location.empty) and (str(location["place_name"]) != 'nan'):
            locality = location["place_name"].split(", ")[0]
            
        pincode_list.append({
            "pincode": details["orderId__master_order__customerId__address__zipcode"],
            "locality_name": locality,
            "total_orders": details["order_count"],
            "revenue": round(subtotal_sum, 2),
            "products": product_details
        })

    if is_download == "false":    
        return JsonResponse({"pincodes": pincode_list})
    
    elif is_download == "true":
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        formatted_start_date = start_date.strftime('%d-%m-%Y')
        formatted_end_date = end_date.strftime('%d-%m-%Y')

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.append(['Start Date', f'{formatted_start_date}'])
        sheet.append(['End Date', f'{formatted_end_date}'])
        sheet.append(['Order Type', f'{order_type}'])
        sheet.append([''])

        sheet.append(["Pincode", "Locality", "Orders", "Revenue", "Most Ordered Products"])
        
        for info in pincode_list:
            list_of_items = ''
            
            for product in info.get('products', []):
                if list_of_items:
                    list_of_items = list_of_items + ", " + product["product_name"]
                else:
                    list_of_items = product["product_name"]

            sheet.append([info["pincode"], info["locality_name"], info["total_orders"], info["revenue"], list_of_items])

        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Pincode_Report_{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=200)


@api_view(["GET"])
def get_delivery_settings(request):
    vendor_id = request.GET.get('vendor')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    delivery_settting = Setting.objects.filter(name="delivery", vendor=vendor_id).first()

    if not delivery_settting:
        json_data = {
            "kilometer_limit": 0,
            "delivery_charges": 0
        }
    
    else:
        json_data = delivery_settting.json_object
    
    return JsonResponse(json_data)


@api_view(["POST"])
def update_delivery_settings(request):
    vendor_id = request.GET.get('vendor')

    if not vendor_id:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vendor_id = int(vendor_id)
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
    kilometer_limit = request.data.get('kilometer_limit')
    delivery_charges = request.data.get('delivery_charges')

    if kilometer_limit is None or delivery_charges is None:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)

    try:
        kilometer_limit = int(kilometer_limit)
        delivery_charges = int(delivery_charges)

    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    json_data = {
        "kilometer_limit": kilometer_limit,
        "delivery_charges": delivery_charges
    }

    delivery_settting_instance = Setting.objects.filter(name="delivery", vendor=vendor_id).first()

    if delivery_settting_instance:
        delivery_settting_instance.json_object = json_data

        delivery_settting_instance.save()
        
        return JsonResponse(delivery_settting_instance.json_object)

    else:
        delivery_settting = Setting(
            name="delivery",
            json_object = json_data,
            vendor=vendor_instance
        )

        delivery_settting.save()
        
        return JsonResponse(delivery_settting.json_object)


import zipfile
@api_view(["POST"])
def product_excel_upload_for_pos(request):
    try:
        if 'excel_file' not in request.FILES:
            return Response("No file uploaded", status=status.HTTP_400_BAD_REQUEST)

        vendor_id = request.POST.get('vendor')

        if not vendor_id:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['excel_file']

        directory = os.path.join(settings.MEDIA_ROOT, 'Product Details Excel')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"{uploaded_file.name.split('.')[0]}_Vendor{vendor_id}.{uploaded_file.name.split('.')[-1]}"

        relative_file_path = os.path.join('Product Details Excel', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        print(file_path)

        with default_storage.open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        workbook = openpyxl.load_workbook(file_path)
        sheet_title = workbook.active.title
        
        file_status, response = process_product_excel(file_path, sheet_title, vendor_id)

        if (file_status == 1) and (response == None):
            return Response("Excel file uploaded successfully")

        elif (file_status == 1) and (response != None):
            return HttpResponse(response, status=status.HTTP_201_CREATED)
        
        elif file_status == 2:
            return Response(response, status=status.HTTP_202_ACCEPTED)

        elif file_status == 3:
            return Response(response, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
        
        elif file_status == 4:
            return Response(response, status=status.HTTP_205_RESET_CONTENT)

        else:
            return Response(f"Excel file upload failed: {response}", status=status.HTTP_400_BAD_REQUEST)

    except zipfile.BadZipFile:
        return Response("Excel file corrupt", status=status.HTTP_206_PARTIAL_CONTENT)
    
    except Exception as e:
        return Response(f"{str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def download_product_excel_upload_template(request):
    try:
        vendor_id = request.GET.get('vendor')

        if not vendor_id:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

        file_name = f"Product_Excel_Template.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        response = "/media/" + relative_file_path

        if not os.path.exists(file_path):
            workbook = openpyxl.Workbook()
            sheet = workbook.active

            sheet.append([
                "Category Name", "Category SKU", "Category Description", "Is Category Active (yes/no)", "Category Image",
                "Product Name", "Product SKU", "Product Description", "Tag", "Product Price (in Rs.)", "Is Product Active (yes/no)", "Product Image",
                "Modifier Group Name", "Modifier Group SKU", "Modifier Group Description", "Modifier Group Min", "Modifier Group Max", "Is Modifier Group Active (yes/no)",
                "Modifier Name", "Modifier SKU", "Modifier Description", "Modifier Price (in Rs.)", "Modifier Active (yes/no)", "Modifier Image"
            ])

            directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
            os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

            workbook.save(file_path)

            print(f"Excel file '{file_name}' has been created.")
        
        return HttpResponse(response, status=status.HTTP_200_OK)
    
    except Exception as e:
        print(e)
        return HttpResponse("Something went wrong", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def download_product_data_excel(request):
    try:
        vendor_id = request.GET.get('vendor')

        if not vendor_id:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
    
        categories = ProductCategory.objects.filter(vendorId=vendor_id).order_by("categoryName", "-is_active")

        if not categories.exists():
            return Response("No categories found", status=status.HTTP_404_NOT_FOUND)
        
        port = request.META.get("SERVER_PORT")

        # Get the IP addresses associated with the hostname
        host_ip_list = socket.gethostbyname_ex(socket.gethostname())[2]

        # Filter out localhost addresses (those starting with "127.")
        filtered_ip_list = []
        for ip in host_ip_list:
            if not ip.startswith("127."):
                filtered_ip_list.append(ip)

        # Take the first non-localhost IP address if it exists
        if filtered_ip_list:
            server_ip = filtered_ip_list[0]

        else:
            server_ip = None

        # Create a socket to determine the external IP address by connecting to a public DNS server
        if not server_ip:
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                soc.connect(('8.8.8.8', 53))
                server_ip = soc.getsockname()[0]
                soc.close()
            except Exception as e:
                server_ip = None

        # server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        
        # Create a new Excel workbook and select the active sheet
        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet.title = "Sheet1"
        
        sheet.append([
            "Category Name", "Category SKU", "Category Description", "Is Category Active (yes/no)", "Category Image",
            "Product Name", "Product SKU", "Product Description", "Tag", "Product Price (in Rs.)", "Is Product Active (yes/no)", "Product Image",
            "Modifier Group Name", "Modifier Group SKU", "Modifier Group Description", "Modifier Group Min", "Modifier Group Max", "Is Modifier Group Active (yes/no)",
            "Modifier Name", "Modifier SKU", "Modifier Description", "Modifier Price (in Rs.)", "Modifier Active (yes/no)", "Modifier Image"
        ])
        
        for category in categories:
            category_product_joint = ProductCategoryJoint.objects.filter(
                category=category,
                vendorId=vendor_id
            ).order_by("product__productName", "-product__active")

            if not category_product_joint.exists():
                return Response(f"No products found for category: {category.categoryName}", status=status.HTTP_404_NOT_FOUND)

            is_category_active = "no"
                        
            if category.is_active == True:
                is_category_active = "yes"
            
            # category_image = f"http://{server_ip}:{port}{category.categoryImage.url}" if category.categoryImage else ""
            
            category_image = category.categoryImageUrl if category.categoryImageUrl else ""
            
            for product_info in category_product_joint:
                is_product_active = "no"

                if product_info.product.active == True:
                    is_product_active = "yes"

                product_image = ""
                
                product_picture = ProductImage.objects.filter(product=product_info.product.pk, vendorId=vendor_id).first()

                if product_picture:
                    product_image = product_picture.url

                product_modifier_group_joint = ProductAndModifierGroupJoint.objects.filter(
                    product=product_info.product.pk,
                    vendorId=vendor_id
                ).order_by("modifierGroup__name", "-modifierGroup__active")

                if not product_modifier_group_joint.exists():
                    sheet.append([
                        f"{category.categoryName}", f"{category.categoryPLU}", f"{category.categoryDescription}", f"{is_category_active}", f"{category_image}",
                        f"{product_info.product.productName}", f"{product_info.product.PLU}", f"{product_info.product.productDesc}",
                        f"{product_info.product.tag}", f"{product_info.product.productPrice}", f"{is_product_active}", f"{product_image}",
                    ])

                else:
                    for modifier_group_info in product_modifier_group_joint:
                        modifier_group_modifier_joint = ProductModifierAndModifierGroupJoint.objects.filter(
                            modifierGroup=modifier_group_info.modifierGroup.pk,
                            vendor=vendor_id
                        ).order_by("modifier__modifierName", "-modifier__active")

                        if not modifier_group_modifier_joint.exists():
                            return Response("Modifier group has no modifiers", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                        
                        is_modifier_group_active = "no"
                        
                        if modifier_group_info.modifierGroup.active == True:
                            is_modifier_group_active = "yes"
                        
                        for modifier_info in modifier_group_modifier_joint:
                            is_modifier_active = "no"
                        
                            if modifier_info.modifier.active == True:
                                is_modifier_active = "yes"

                            modifier_image = ""
                
                            if modifier_info.modifier.modifierImg:
                                modifier_image = modifier_info.modifier.modifierImg

                            sheet.append([
                                f"{category.categoryName}", f"{category.categoryPLU}", f"{category.categoryDescription}", f"{is_category_active}", f"{category_image}",
                                f"{product_info.product.productName}", f"{product_info.product.PLU}", f"{product_info.product.productDesc}",
                                f"{product_info.product.tag}", f"{product_info.product.productPrice}", f"{is_product_active}", f"{product_image}",
                                f"{modifier_group_info.modifierGroup.name}", f"{modifier_group_info.modifierGroup.PLU}", f"{modifier_group_info.modifierGroup.modifier_group_description}",
                                f"{modifier_group_info.modifierGroup.min}", f"{modifier_group_info.modifierGroup.max}", f"{is_modifier_group_active}",
                                f"{modifier_info.modifier.modifierName}", f"{modifier_info.modifier.modifierPLU}", f"{modifier_info.modifier.modifierDesc}",
                                f"{modifier_info.modifier.modifierPrice}", f"{is_modifier_active}", f"{modifier_image}",
                            ])
        
        directory = os.path.join(settings.MEDIA_ROOT, 'Excel Downloads')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"Products_data_Vendor{vendor_id}.xlsx"

        relative_file_path = os.path.join('Excel Downloads', file_name)

        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

        workbook.save(file_path)

        print(f"Excel file '{file_name}' has been created.")
        
        response = "/media/" + relative_file_path
        
        return HttpResponse(response, status=status.HTTP_200_OK)
    
    except Exception as e:
        print(e)
        return HttpResponse("Something went wrong", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # # To return excel file
    # with open(file_path, 'rb') as excel_file:
    #     response = FileResponse(excel_file.read(), as_attachment=True, filename=file_name)
    # return response

    # # To return excel file as Base64
    # with open(file_path, 'rb') as excel_file:
    #     excel_content = excel_file.read()
        
    # base64_encoded = b64encode(excel_content).decode('utf-8')
    
    # response = HttpResponse(base64_encoded, content_type='text/plain')
    # response['Content-Disposition'] = 'attachment; filename="file.xlsx"'
    
    # return response


@api_view(["POST"])
def is_platform(request):
    try:
        request_data = request.data
        
        if not request_data:
            return Response("No data in the request body", status=status.HTTP_400_BAD_REQUEST)
        
        required_keys = {"platform", "vendor_id"}

        if not required_keys.issubset(request_data.keys()):
            return Response("Keys in request data should be: 'platform', 'vendor_id'", status=status.HTTP_400_BAD_REQUEST)

        platform_to_check = (request_data.get("platform")).lower()
        vendor_id = request_data.get("vendor_id")

        if not vendor_id:
            return Response("Vendor ID empty", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)    

        platform_names = ()

        vendor_platforms = Platform.objects.filter(VendorId=vendor_id)

        for platform in vendor_platforms:
            platform_names = platform_names + (platform.Name.lower(),)
        
        if (not platform_to_check) or (platform_to_check not in platform_names):
            return Response("Invalid Platform key", status=status.HTTP_400_BAD_REQUEST)
        
        specific_platform = Platform.objects.filter(Name__iexact=platform_to_check, VendorId=vendor_id).first()

        if not specific_platform:
            return Response("Platform does not exist", status=status.HTTP_404_NOT_FOUND)
        
        current_date = datetime.today().strftime("%Y-%m-%d")
        
        if (platform.isActive == True) and (current_date < platform.expiryDate.strftime("%Y-%m-%d")):
            return Response("True", status=status.HTTP_200_OK)
        
        return Response("False", status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(f"{str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CoreUserCategoryModelViewSet(viewsets.ModelViewSet):
    queryset = CoreUserCategory.objects.all().order_by('-pk')
    serializer_class = CoreUserCategoryModelSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ('name',)
    search_fields = ('name',)
    ordering_fields = ('id', 'name',)
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]
    
    def get_queryset(self):
        vendor_id = self.request.GET.get('vendor')

        if vendor_id:
            return CoreUserCategory.objects.filter(vendor=vendor_id).order_by('name')
        
        return CoreUserCategory.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)

        serializer_data = serializer.data
        serializer_data.insert(0, {'id':0, 'name': 'Uncategorized', 'vendor': 1})
        
        return JsonResponse({"user_categories": serializer_data})

    def create(self, request, *args, **kwargs):
        try:
            name = request.data.get('name')
            vendor_id = request.data.get('vendor')

            if not name: 
                return JsonResponse({"name": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
            
            if not vendor_id:
                return JsonResponse({"vendor": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

            existing_category = CoreUserCategory.objects.filter(
                Q(name__iexact=f"{name}_{vendor_id}") & Q(vendor_id=vendor_id)
            )

            if existing_category.exists():
                return Response(
                    {"error": "Category with this name already exists"},
                    status=status.HTTP_400_BAD_REQUEST
            )
            
            core_user_category = CoreUserCategory(name=f"{name}_{vendor_id}", vendor_id=vendor_id)
            core_user_category.save()

            serializer = self.get_serializer(core_user_category)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except IntegrityError:
            return JsonResponse({"name": ["group with this name already exists."]}, status=status.HTTP_400_BAD_REQUEST)
        
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            name = request.data.get('name')
            vendor_id = request.GET.get('vendor')

            if not name: 
                return JsonResponse({"name": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
                
            if not vendor_id:
                return JsonResponse({"vendor": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

            existing_category = CoreUserCategory.objects.filter(
                Q(name__iexact=f"{name}_{vendor_id}") & ~Q(pk=instance.pk) & Q(vendor_id=vendor_id)
            )

            if existing_category.exists():
                return Response(
                    {"error": "Category with this name already exists"},
                    status=status.HTTP_400_BAD_REQUEST
            )
            
            instance.name = f"{name}_{vendor_id}"
            instance.save()

            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
        except IntegrityError:
            return JsonResponse({"name": ["group with this name already exists."]}, status=status.HTTP_400_BAD_REQUEST)


class CoreUserModelViewSet(viewsets.ModelViewSet):
    queryset = CoreUser.objects.all().order_by('-pk')
    serializer_class = CoreUserModelSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ('first_name', 'last_name', 'email')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number',)
    ordering_fields = ('id', 'first_name', 'last_name',)
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]

    def get_queryset(self):
        vendor_id = self.request.GET.get('vendor')
        group_id = self.request.GET.get('group')

        if vendor_id:
            if not group_id:
                return CoreUser.objects.filter(vendor=vendor_id).order_by('-pk')

            elif group_id=='0':
                return CoreUser.objects.filter(groups__isnull=True, vendor=vendor_id).order_by('-pk')
            
            else:
                return CoreUser.objects.filter(groups=group_id, vendor=vendor_id).order_by('-pk')
        
        return CoreUser.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        
        return JsonResponse({"users": serializer.data})
    
    def perform_create(self, serializer):
        password = self.request.data.get('password')
        if password:
            serializer.save(password=make_password(password))
        else:
            serializer.save()

    def perform_update(self, serializer):
        password = self.request.data.get('password')
        if password:
            serializer.save(password=make_password(password))
        else:
            serializer.save()


class DepartmentModelViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('-pk')
    serializer_class = DepartmentModelSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ('name',)
    search_fields = ('name',)
    ordering_fields = ('id', 'name',)
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]
    
    def get_queryset(self):
        vendor_id = self.request.GET.get('vendor')

        if vendor_id:
            return Department.objects.filter(vendor=vendor_id).order_by('-pk')
        
        return Department.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        
        return JsonResponse({"departments": serializer.data})
    
    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        vendor_id = request.data.get('vendor')

        existing_department = Department.objects.filter(Q(name__iexact=name) & Q(vendor=vendor_id))

        if existing_department.exists():
            return Response(
                {"error": "Department with this name already exists"},
                status=status.HTTP_400_BAD_REQUEST
        )

        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        name = request.data.get('name')
        vendor_id = request.GET.get('vendor')

        instance = self.get_object()

        if name:
            existing_department = Department.objects.filter(
                Q(name__iexact=name) & ~Q(pk=instance.pk) & Q(vendor=vendor_id)
            )

            if existing_department.exists():
                return Response(
                    {"error": "Department with this name already exists"},
                    status=status.HTTP_400_BAD_REQUEST
            )

        return super().update(request, *args, **kwargs)
