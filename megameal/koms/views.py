from order import order_helper
from core.utils import API_Messages, UpdatePoint, OrderType
from core.models import Product, ProductImage, Platform, ProductModifier, Tax, ProductModifierGroup, ProductCategory, Vendor
from woms.models import HotelTable, Waiter
from django.db.models import Count, Sum
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from koms.serializers.order_point_serializer import Order_point_serializer
from koms.serializers.order_content_serializer import Order_content_serializer
from koms.serializers.order_modifer_serializer import Order_modifer_serializer, OrderModifierWriterSerializer
from koms.serializers.order_serializer import Order_serializer, OrderSerializerWriterSerializer
from koms.serializers.user_settings_serializer import UserSettingReaderSerializer
from koms.serializers.stations_serializer import Stations_serializer, StationsReadSerializer
from koms.serializers.staff_serializer import StaffReaderSerializer,StaffWriterSerializer
from static.order_status_const import PENDING, PENDINGINT, STATION, STATUSCOUNT, MESSAGE, WOMS
from .models import (
    Order_point, Order, Order_content, Order_modifer, Order_tables, Station, Staff, UserSettings,
    KOMSOrderStatus, Content_assign, OrderHistory, massage_history, Message_type,
)
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta, time
from .serializers.content_assign_serializer import Content_assign_serializer
from static.order_status_const import WHEELSTATS, STATIONSIDEBAR
from static.statusname import *
from order.models import Order as coreOrder, OrderPayment, Address, LoyaltyProgramSettings, LoyaltyPointsRedeemHistory
from pos.models import StoreTiming
from pos.language import order_has_arrived_locale, payment_type_english, language_localization
from inventory.utils import sync_order_content_with_inventory
import secrets
import json
import string
import random
import pytz
import logging
import sys


def updateCoreOrder(order):
    try:
        if order.order_status in [READY,CANCELED,CLOSE]:
            data=getOrder(ticketId=order.pk,vendorId=order.vendorId_id)
            orderstatut= "PREPARED" if order.order_status==READY else "CANCELED"
            orderstatut= "COMPLETED" if order.order_status==CLOSE else orderstatut
            # ++++++++++ request data
            data = {"status":orderstatut,"orderId":data['orderId'], "vendorId":order.vendorId_id}
            vendorId = data["vendorId"]
            data["updatePoint"]=UpdatePoint.KOMS
            # ++++ pick all the channels of vendor
            rs=order_helper.OrderHelper.orderStatusUpdate(data=data,vendorId=vendorId)
            # return Response(rs[0], status=rs[1])
    except Exception as err :
        print(f"updateCoreOrder {err=}, {type(err)=}")
        

@api_view(["GET", "POST"])
def orderPoint(request,vendorId):
    order_points = Order_point.objects.all(vendorId=vendorId)
    serializer = Order_point_serializer(order_points, many=True)
    return Response(serializer.data)

@api_view(["GET", "POST"])
def orderList(request):
    result = {}
    orderList = Order.objects.filter(vendorId=request.GET.get("vendorId"))
    serializers = Order_serializer(orderList, many=True)
    result["order"] = serializers.data
    for orderIndex, order in enumerate(orderList, start=0):
        orderContent = Order_content.objects.filter(orderId=order.id)
        contentSerializers = Order_content_serializer(orderContent, many=True)
        result["order"][orderIndex]["Appetizer"] = contentSerializers.data
        for modifierIndex, modifier in enumerate(orderContent, start=0):
            modifierContent = Order_modifer.objects.filter(contentID=modifier.id)
            modifier_serializer = Order_modifer_serializer(modifierContent, many=True)
            result["order"][orderIndex]["Appetizer"][modifierIndex][
                "subItems"
            ] = modifier_serializer.data
    return JsonResponse(json.dump(result, sys.stdout), safe=False)


@api_view(["POST"])
def PostOrder(request):
    orderData = JSONParser().parse(request)
    serializers = Order_serializer(data=orderData)
    if serializers.is_valid():
        serializers.save()
        return JsonResponse(serializers.data, status=status.HTTP_201_CREATED)
    return JsonResponse(
        {"message": "something went wrong please check your response"},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET", "POST"])
class TestingViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializers = Order_serializer


class StationsView(APIView):
    # 1. List all
    def get(self,request, *args, **kwargs):
        stationList = Station.objects.filter(isStation=True,vendorId=request.GET.get("vendorId")).all()
        serializers = StationsReadSerializer(stationList, many=True)
        return JsonResponse(serializers.data, safe=False)

    # 2. Create
    def post(self,request, *args, **kwargs):
        data = {
            "name": request.data.get("stationName"),
            "station_name": request.data.get("stationName"),
            "colorCode": request.data.get("colorCode"),
            "client_id": "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            ),
            "client_secrete": "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            ),
            "tag": "1",
            "isStation": request.data.get("isStation"),
            "vendorId":request.data.get("vendorId")
        }
        # print(data)
        serializer = Stations_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StationsDetailView(APIView):
    def get_object(self,stationId,vendorId):
        try:
            return Station.objects.get(id=stationId,vendorId=vendorId)
        except Station.DoesNotExist:
            return None

    # 3. Retrieve
    def get(self, request, *args, **kwargs):
        station_instance = self.get_object(request.GET.get("stationId"),request.GET.get("vendorId"))
        if not station_instance:
            return Response(
                {"res": "Station with  id " + str(request.GET.get("stationId")) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StationsReadSerializer(station_instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 4. Update
    def put(self, request, *args, **kwargs):
        station_instance = self.get_object(request.data.get("stationId"),request.data.get("vendorId"))
        if not station_instance:
            return Response(
                {"res": "Station with id " + str(request.data.get("stationId")) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {
            "station_name": request.data.get("stationName"),
            "colorCode": request.data.get("colorCode"),
        }
        serializer = Stations_serializer(
            instance=station_instance, data=data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 5. Delete
    def delete(self, request, *args, **kwargs):
        station_instance = self.get_object(request.GET.get("stationId"),request.GET.get("vendorId"))
        if not station_instance:
            return Response(
                {"res": "Station with id " + str(request.GET.get("stationId")) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        station_name = station_instance.station_name
        station_instance.delete()
        return Response({"res": station_name + " deleted!"}, status=status.HTTP_200_OK)


class StaffView(APIView):
    # 1. List all
    def get(self, request, *args, **kwargs):
        stationList = Staff.objects.filter(vendorId=request.GET.get("vendorId"))
        serializers = StaffReaderSerializer(stationList, many=True)
        return JsonResponse(serializers.data, safe=False)

    # 2. Create
    def post(self, request, *args, **kwargs):
        data = {
            "first_name": request.data.get("firstName"),
            "last_name": request.data.get("lastName"),
            "staff_type": 1,
            "active_status": 1,
            "station_id": None,
            "vendorId":request.GET.get("vendorId")
        }
        # print(data)
        serializer = StaffWriterSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffDetailView(APIView):
    def get_object(self, staffId,vendorId):
        try:
            return Staff.objects.get(id=staffId,vendorId=vendorId)
        except Staff.DoesNotExist:
            return None

    # 3. Retrieve
    def get(self, request, staffId, *args, **kwargs):
        staff_instance = self.get_object(staffId,request.GET.get("vendorId"))
        if not staff_instance:
            return Response(
                {"res": "Staff with  id " + str(staffId) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StaffReaderSerializer(staff_instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 4. Update
    def put(self, request, staffId, *args, **kwargs):
        staff_instance = self.get_object(staffId,request.GET.get("vendorId"))
        if not staff_instance:
            return Response(
                {"res": "Staff with id " + str(staffId) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {}
        if request.data.get("firstName"):
            data["first_name"] = request.data.get("firstName")
        if request.data.get("lastName"):
            data["last_name"] = request.data.get("lastName")
        if request.data.get("staffType"):
            data["staff_type"] = request.data.get("staffType")
        if request.data.get("activeStatus"):
            data["active_status"] = request.data.get("activeStatus")
        data["vendorId"]=request.GET.get("vendorId")
        if request.data.get("stationId"):
            data["station_id"] = request.data.get("stationId")
            selectedStation = StationsDetailView.get_object(
                StationsDetailView, request.data.get("stationId")
            )
            if not selectedStation:
                return Response(
                    {
                        "res": "Station with  id "
                        + str(request.data.get("stationId"))
                        + " does not exists"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # print(selectedStation)

        serializer = StaffWriterSerializer(
            instance=staff_instance, data=data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 5. Delete
    def delete(self, request, staffId, *args, **kwargs):
        staff_instance = self.get_object(staffId,request.GET.get("vendorId"))
        if not staff_instance:
            return Response(
                {"res": "Staff with id " + str(staffId) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        staffName = staff_instance.last_name
        staff_instance.delete()
        return Response({"res": staffName + " deleted!"}, status=status.HTTP_200_OK)


class StationsStaffView(APIView):
    def get(self, request, stationId, *args, **kwargs):
        stationList = Staff.objects.filter(station_id=stationId,vendorId_id=request.GET.get("vendorId")).all()
        serializers = StaffReaderSerializer(stationList, many=True)
        return JsonResponse(serializers.data, safe=False)


class UserSettingsView(APIView):
    def get_object(self, stationId,vendorId):
        try:
            return UserSettings.objects.get(stationId=stationId,vendorId=vendorId)
        except UserSettings.DoesNotExist:
            return None

    # 3. Retrieve
    def get(self, request, stationId, *args, **kwargs):
        user_settings = self.get_object(stationId,request.GET.get("vendorId"))
        if not user_settings:
            return Response(
                {"res": "User Settings not found for id " + str(stationId)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserSettingReaderSerializer(user_settings)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 5. Delete
    def delete(self, request, stationId, *args, **kwargs):
        user_settings = self.get_object(stationId,request.GET.get("vendorId"))
        if not user_settings:
            return Response(
                {"res": "User Settings not found for id " + str(stationId)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_settings.delete()
        return Response({"res": " deleted!"}, status=status.HTTP_200_OK)

    def post(self, request, stationId, *args, **kwargs):
        ### check station settings available or not
        station_instance = StationsDetailView.get_object(self, stationId,request.GET.get("vendorId"))
        if not station_instance:
            return Response(
                {"res": "Station with  id " + str(stationId) + " does not exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {
            "notification": request.data.get("notification"),
            "cooking": request.data.get("cooking"),
            "incoming": request.data.get("cooking"),
            "dragged": request.data.get("cooking"),
            "complete": request.data.get("cooking"),
            "cancel": request.data.get("cooking"),
            "recall": request.data.get("cooking"),
            "priority": request.data.get("cooking"),
            "nearTo": request.data.get("cooking"),
            "stationId": stationId,
        }
        user_settings = self.get_object(stationId)

        serializer = UserSettingReaderSerializer(
            instance=user_settings, data=data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def stationOrder(request):
    request_body = JSONParser().parse(request)

    start_date = request_body.get("start")
    end_date = request_body.get("end")
    vendor_id = request.GET.get("vendorId")

    order_ids = Order.objects.filter(
        arrival_time__date__range=(start_date, end_date),
        vendorId=vendor_id
    ).values_list("id", flat=True)

    stations = Station.objects.filter(isStation=True, vendorId=vendor_id)

    response = []

    for station in stations:
        station_id = station.pk

        test = Order_content.objects.filter(orderId__in=order_ids, stationId=station_id)
        
        station_details = {
            "id": station_id,
            "name": station.station_name,
            "count": test.count(),
            "colorCode": station.color_code,
        }

        response.append(station_details)

    return Response(response, status=status.HTTP_200_OK)


@api_view(["POST"])
def orderCount(request):
    requestJson = JSONParser().parse(request)
    start = requestJson.get("start")
    end = requestJson.get("end")
    order_status = KOMSOrderStatus.objects.all()
    s_date = start + " 00:00:00.000000"
    e_date = end + " 23:59:59.000000"
    total = Order.objects.filter(arrival_time__range=(s_date, e_date),vendorId=request.GET.get("vendorId")).count()
    response = []
    try:
        for orderStatus in order_status:
            data = {
                "status": orderStatus.id,
                "name": orderStatus.status,
                "count": Order.objects.filter(Q(order_status=orderStatus.id) & Q(arrival_time__range=(s_date, e_date)) & Q(vendorId=request.GET.get("vendorId"))
                ).count(),
            }
            if orderStatus.id == 7:
                data['count']  = Order.objects.filter(Q(isHigh=True) & Q(arrival_time__range=(s_date, e_date)) & Q(vendorId=request.GET.get("vendorId"))).count()
            response.append(data)
    except Exception as e:
        print(str(e))
        pass

    return Response({"total": total, "data": response}, status=status.HTTP_200_OK)


@api_view(["POST"])
def ticketSearch(request):
    requestJson = JSONParser().parse(request)
    ticketId = requestJson.get("ticketId")
    tableId = requestJson.get("tableId")

    if ticketId is not None:
        print(ticketId)
        try:
            orders = Order.objects.filter(Q(vendorId=request.GET.get("vendorId")) & (Q(externalOrderId=ticketId) | Q(id=ticketId)))
            serializedData = Order_serializer(orders, many=True)
        except:
            return Response(
                {"error": "Invalid ticket Id"}, status=status.HTTP_400_BAD_REQUEST
            )
    elif tableId is not None:
        print(tableId)
    else:
        print("invalid arguments")
        return Response(
            {"error": "invalid arguments"}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(serializedData.data, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def saveOrder(request):
    try:
        #  order section
        vendorId=request.GET.get("vendorId")
        order_data = JSONParser().parse(request)
        # order_data["vendorId"]=vendorId
        response=createOrderInKomsAndWoms(order_data)
        return JsonResponse(response,status= status.HTTP_200_OK if response[API_Messages.STATUS]==API_Messages.SUCCESSFUL else status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        return JsonResponse(
            {   API_Messages.STATUS:API_Messages.ERROR,
                API_Messages.RESPONSE: f"Unexpected {e=}, {type(e)=}" }, status=status.HTTP_400_BAD_REQUEST
        )


def createOrderInKomsAndWoms(orderJson):
    try:
        #  order section
        vendorId = orderJson.get("vendorId")

        order_data = orderJson

        order_data["externalOrderId"] = order_data["orderId"]
        order_data["master_order"] = order_data["master_id"]
        order_data["order_status"] = 1  if Platform.objects.filter(Name="KOMS",VendorId= vendorId).first().isActive else 8 # pending order
        order_data["status"] = 1 # pending order
        order_data["order_type"] = order_data["orderType"]
        order_data["arrival_time"] = order_data["arrivalTime"]
        order_data["order_note"] = order_data["note"]
        order_data["isHigh"] = False if order_data.get('isHigh') is None else order_data["isHigh"]
        tablesData=order_data["tableNo"] if order_data["tableNo"] else []
        guestCount = 0
        for guest in order_data["tableNo"]:
            guestCount=+guest.get('guestCount',0)
        order_data["guest"]=guestCount
        order_data["tableNo"]=''
        order_data["vendorId"]=vendorId
        print("koms_order_data \n",order_data)
        order_serializers = OrderSerializerWriterSerializer(
            data=order_data, partial=True
        )

        if order_serializers.is_valid():
            order_save_data = order_serializers.save()
            order_data["id"] = order_save_data.id

            #### +++ Table Link
            try:
                for table in tablesData:
                        Order_tables(
                        orderId_id=order_data["id"],
                        tableId_id=table["tableId"]
                        ).save()
            except Exception as err:
                    print(f"Unexpected {err=}, {type(err)=}") 
            ####
            
        else:
            print("order err",order_serializers._errors)
            return  {
                API_Messages.STATUS:API_Messages.ERROR,
                API_Messages.RESPONSE: order_serializers.errors}

        #  product section
        for key, value in order_data["items"].items():
            for singleProduct in value:
                # print(singleProduct)
                singleProduct["orderId"] = order_save_data.id
                singleProduct["quantityStatus"] = 1  # quantityStatus
                singleProduct["stationId"] = singleProduct["tag"]
                singleProduct["stationName"] = "Fry"
                category = ProductCategory.objects.filter(categoryName = key,vendorId = order_data["vendorId"])
                if category.exists():
                    category = category.first()
                    if category.categoryStation is not None:
                        singleProduct["stationId"] = category.categoryStation.pk
                        singleProduct["stationName"] = category.categoryStation.station_name
                # singleProduct["stationName"] = Station.objects.get(
                #     pk=singleProduct["tag"],
                #     vendorId=order_data["vendorId"]
                # ).station_name
                singleProduct["chefId"] = 0
                singleProduct["note"] = singleProduct["itemRemark"]
                singleProduct["SKU"] = singleProduct["plu"]
                singleProduct["status"] = '1' if Platform.objects.filter(Name="KOMS", VendorId= vendorId).first().isActive else '8' # pending order
                singleProduct["categoryName"] = key
                single_product_serializer = Order_content_serializer(
                    data=singleProduct, partial=True
                )

                if single_product_serializer.is_valid():
                    single_product_data = single_product_serializer.save()
                    singleProduct["id"] = single_product_data.id  # id
                    #  modifier section
                    for singleModifier in singleProduct["subItems"]:
                        # print(singleModifier)
                        singleModifier["contentID"] = single_product_data.id
                        singleModifier["quantityStatus"] = 1  # original
                        if "itemRemark" in singleModifier.keys():
                            singleModifier["note"] = singleModifier["itemRemark"]
                        singleModifier["SKU"] = singleModifier["plu"]
                        singleModifier["status"] = "1" if singleModifier.get("status") else "0"
                        singleModifier["quantity"] = singleModifier["quantity"] if 'quantity' in singleModifier.keys() else 1
                        single_modifier_serializer = OrderModifierWriterSerializer(data=singleModifier, partial=True)
                        if single_modifier_serializer.is_valid():
                            single_mod_data = single_modifier_serializer.save()
                            singleModifier["id"] = single_mod_data.id
                            print('modifier saved')
                        else:
                            # print(single_modifier_serializer.error_messages)
                            print("invalid modifier   ",single_modifier_serializer.errors)
                            logging.exception("invalid modifier" + str(singleModifier))
                else:
                    print(single_product_serializer.error_messages)
                    print(single_product_serializer._errors)
                    logging.exception("invalid product" + str(singleProduct))
        webSocketPush(message=stationQueueCount(vendorId=vendorId),room_name= WHEELSTATS+str(vendorId), username="CORE")  # wheel man left side
        webSocketPush(message=statuscount(vendorId=vendorId),room_name= STATUSCOUNT+str(vendorId),username= "CORE")  # wheel man status count
        try:
            orderTables=Order_tables.objects.filter(
                orderId_id=order_save_data.id
            )
            values_list = [str(item.tableId.tableNumber) for item in orderTables]
            values_list= ', '.join(values_list) 
        
        except Order_tables.DoesNotExist:
            print("Order table not found")
            values_list=""
        
        wheelman=[i.pk for i in Station.objects.filter(isStation=False,vendorId=vendorId) ]
        
        if Platform.objects.filter(Name="KOMS",VendorId= vendorId).first().isActive :
                webSocketPush(message=order_data, room_name=str(vendorId)+"-"+str(PENDINGINT), username="CORE")  # wheelMan Pending section
                notify(type=1,msg=order_save_data.id,desc=f"Order No { order_save_data.externalOrderId } on Table No {values_list} is arrived",stn=[4],vendorId=vendorId)
        
        else :
                # processStation(oldStatus=str(8),currentStatus=str(8),orderId=order_save_data.id,station=content.stationId,vendorId=vendorId)
                stnlist=[i.stationId.pk for i in Order_content.objects.filter(orderId=order_save_data.id)]
                allStationWiseSingle(id=order_save_data.id,vendorId=vendorId)
                notify(type=1,msg=order_save_data.id,desc=f"Order No { order_save_data.externalOrderId } is arrived",stn=stnlist,vendorId=vendorId)
        
        language = order_data.get("language", "English")

        if language == "English":
            notify(type=1, msg=order_save_data.id, desc=f"Order No {order_save_data.externalOrderId} is arrived", stn=['POS'], vendorId=vendorId)
        
        else:
            notify(type=1, msg=order_save_data.id, desc=order_has_arrived_locale(order_save_data.externalOrderId), stn=['POS'], vendorId=vendorId)
            
            
        waiteOrderUpdate(orderid=order_save_data.id, language=language, vendorId=vendorId)
        allStationWiseCategory(vendorId=vendorId)  # all stations sidebar category wise counts
        
        platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendorId).first()

        if platform:
            sync_order_content_with_inventory(order_data["master_id"], vendorId)
            
        return {API_Messages.STATUS:API_Messages.SUCCESSFUL, "id": order_save_data.id,"wheelman":wheelman}
    
    except Exception as e:
        print(e)
        return {API_Messages.STATUS:API_Messages.ERROR, API_Messages.RESPONSE: f"Unexpected {e=}, {type(e)=}" }
        

def webSocketPush(message, room_name, username):
    print("webSocketPush Room Name : ",room_name)
    channel_layer = get_channel_layer()
    data = async_to_sync(channel_layer.group_send)(
        "chat_%s" % room_name,
        {"type": "chat_message", "message": message, "username": username},
    )
  

def waiteOrderUpdate(orderid, vendorId, language="English"):
    try:
        data = getOrder(ticketId=orderid, language="English", vendorId=vendorId)

        listOrder = Order_tables.objects.filter(orderId_id=orderid)

        waiters = []

        master_order = coreOrder.objects.filter(Q(externalOrderId=str(data.get('orderId'))) | Q(pk=str(data.get('orderId')))).first()

        payment_type = OrderPayment.objects.filter(orderId=master_order.pk).last()
        
        if payment_type:
            payment_mode = payment_type_english[payment_type.type]

        else:
            payment_mode = payment_type_english[1]
        
        payment_details = {
            "total": master_order.TotalAmount,
            "subtotal": master_order.subtotal,
            "tax": master_order.tax,
            "delivery_charge": master_order.delivery_charge,
            "discount": master_order.discount,
            "tip": master_order.tip,
            "paymentKey": payment_type.paymentKey,
            "platform": payment_type.platform,
            "status": payment_type.status,
            "mode": payment_mode
        }

        data['payment'] = payment_details

        platform_details = {
            "id": master_order.platform.pk,
            "name": master_order.platform.Name
        }

        data["platform_details"] = platform_details

        address = Address.objects.filter(customer=master_order.customerId.pk, is_selected=True, type="shipping_address").first()
        
        customer_address = ""

        if address:
            address_line_1 = address.address_line1 if address.address_line1 else ""
            address_line_2 = address.address_line2 if address.address_line2 else ""
            city = address.city if address.city else ""
            state = address.state if address.state else ""
            country = address.country if address.country else ""
            zipcode = address.zipcode if address.zipcode else ""
            
            customer_address = address_line_1 + ", " + address_line_2 + ", " + city + ", " + state + ", " + country + ", " + zipcode
        
        customer_details = {
            "id": master_order.customerId.pk,
            "name": master_order.customerId.FirstName + " " + master_order.customerId.LastName,
            "mobile": master_order.customerId.Phone_Number,
            "email": master_order.customerId.Email,
            "shipping_address": customer_address
        }

        data["customer_details"] = customer_details

        total_points_redeemed = 0
        
        loyalty_program = LoyaltyProgramSettings.objects.filter(is_active=True, vendor=vendorId).first()

        if loyalty_program:
            loyalty_points_redeem_history = LoyaltyPointsRedeemHistory.objects.filter(
                customer=master_order.customerId.pk,
                order=master_order.pk
            )

            if loyalty_points_redeem_history.exists():
                total_points_redeemed = loyalty_points_redeem_history.aggregate(Sum('points_redeemed'))['points_redeemed__sum']

                if not total_points_redeemed:
                    total_points_redeemed = 0

        data["total_points_redeemed"] = total_points_redeemed

        secondary_language = Vendor.objects.filter(pk=vendorId).first().secondary_language

        if secondary_language:
            data_locale = getOrder(ticketId=orderid, language=secondary_language, vendorId=vendorId)

            if payment_type:
                payment_mode_locale = language_localization[payment_type_english[payment_type.type]]

            else:
                payment_mode_locale = language_localization[payment_type_english[1]]

            payment_details_locale = payment_details.copy()

            payment_details_locale["mode"] = payment_mode_locale

            data_locale['payment'] = payment_details_locale
            data_locale["platform_details"] = platform_details
            data_locale["customer_details"] = customer_details
            data_locale["total_points_redeemed"] = total_points_redeemed

        if master_order.Status == 2:
            for order in listOrder:
                order.tableId.status = 1 # EMPTY TABLE
                order.tableId.guestCount = 0
                order.tableId.save()

                waiters.append(order.tableId.waiterId.pk)

        else:
            for order in listOrder:
                waiters.append(order.tableId.waiterId.pk)

        waiter_heads = Waiter.objects.filter(is_waiter_head=True, vendorId=vendorId).values_list("pk", flat=True)

        waiters = set(waiters) - set(waiter_heads)

        if data['orderType'] == OrderType.DINEIN:
            for waiter_id in waiters:
                webSocketPush(
                    message = {"result": data, "UPDATE": "UPDATE"},
                    room_name = f"STATIONWOMS{str(waiter_id)}---English-{str(vendorId)}",
                    username = "CORE",
                )

                if secondary_language:
                    webSocketPush(
                        message = {"result": data_locale, "UPDATE": "UPDATE"},
                        room_name = f"STATIONWOMS{str(waiter_id)}---{secondary_language}-{str(vendorId)}",
                        username = "CORE",
                    )
            
            for waiter_head_id in waiter_heads:
                webSocketPush(
                    message = {"result": data, "UPDATE": "UPDATE"},
                    room_name = f"STATIONWOMS{str(waiter_head_id)}---English-{str(vendorId)}",
                    username = "CORE",
                )

                if secondary_language:
                    webSocketPush(
                        message = {"result": data_locale, "UPDATE": "UPDATE"},
                        room_name = f"STATIONWOMS{str(waiter_head_id)}---{secondary_language}-{str(vendorId)}",
                        username = "CORE",
                    )
        
        for table in listOrder:
            hotelTable = HotelTable.objects.get(pk=table.tableId.pk)

            table_data = { 
                "tableId": hotelTable.pk, 
                "tableNumber": hotelTable.tableNumber,
                "waiterId": hotelTable.waiterId.pk if hotelTable.waiterId else 0,
                "waiterName": hotelTable.waiterId.name if hotelTable.waiterId else "",
                "status": hotelTable.status,
                "tableCapacity": hotelTable.tableCapacity, 
                "guestCount": hotelTable.guestCount,
                "floorId": hotelTable.floor.pk,
                "floorName": hotelTable.floor.name,
                "order": master_order.externalOrderId,
                "total_amount": master_order.subtotal,
            }

            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMSPOS------English-{str(vendorId)}",
                username = "CORE",
            )

            if secondary_language:
                table_data_locale = table_data.copy()

                table_data_locale["waiterName"] = hotelTable.waiterId.name_locale if hotelTable.waiterId else ""
                table_data_locale["floorName"] = hotelTable.floor.name_locale
            
                webSocketPush(
                    message = {"result": table_data_locale, "UPDATE": "UPDATE"},
                    room_name = f"WOMSPOS------{secondary_language}-{str(vendorId)}",
                    username = "CORE",
                )
               
            waiter_id = 0
            
            for waiter_id in waiters:
                webSocketPush(
                    message = {"result": table_data, "UPDATE": "UPDATE"},
                    room_name = f"WOMS{str(waiter_id)}------English-{str(vendorId)}",
                    username = "CORE",
                )

                if secondary_language:
                    webSocketPush(
                        message = {"result": table_data_locale, "UPDATE": "UPDATE"},
                        room_name = f"WOMS{str(waiter_id)}------{secondary_language}-{str(vendorId)}",
                        username = "CORE",
                    )

            waiter_head_id = 0
            
            for waiter_head_id in waiter_heads:
                webSocketPush(
                    message = {"result": table_data, "UPDATE": "UPDATE"},
                    room_name = f"WOMS{str(waiter_head_id)}------English-{str(vendorId)}",
                    username = "CORE",
                )

                if secondary_language:
                    webSocketPush(
                        message = {"result": table_data_locale, "UPDATE": "UPDATE"},
                        room_name = f"WOMS{str(waiter_head_id)}------{secondary_language}-{str(vendorId)}",
                        username = "CORE",
                    )
        
        webSocketPush(message={"result": data, "UPDATE": "UPDATE"}, room_name=f"POS-------0-English-{str(vendorId)}", username="CORE",)
        webSocketPush(message={"result": data, "UPDATE": "UPDATE"}, room_name=f"POS-------1-English-{str(vendorId)}", username="CORE",)

        if secondary_language:
            webSocketPush(
                message = {"result": data_locale, "UPDATE": "UPDATE"},
                room_name = f"POS-------0-{secondary_language}-{str(vendorId)}",
                username = "CORE",
            )

            webSocketPush(
                message = {"result": data_locale, "UPDATE": "UPDATE"},
                room_name = f"POS-------1-{secondary_language}-{str(vendorId)}",
                username = "CORE",
            )

        webSocketPush(
            message = data,
            room_name = f"{str(vendorId)}-{str(data['status'])}",
            username = "CORE"
        )

        webSocketPush(
            message = stationQueueCount(vendorId=vendorId),
            room_name = f"WHEELSTATS{str(vendorId)}",
            username = "CORE"
        )

        webSocketPush(
            message = statuscount(vendorId=vendorId),
            room_name = f"STATUSCOUNT{str(vendorId)}",
            username = "CORE"
        )

        webSocketPush(
            message = CategoryWise(vendorId=vendorId),
            room_name = "STATIONSIDEBAR",
            username = "CORE"
        )
    
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")


@api_view(["POST", "PUT"])
def updateTicketStatus(request):
    requestJson = JSONParser().parse(request)

    ticketId = requestJson.get("ticketId")
    contentId = requestJson.get("contentId")
    orderStatus = requestJson.get("status")
    ticketStatus = requestJson.get("ticketStatus")
    vendorId = request.GET.get("vendorId")
    language = request.GET.get("language", "English")

    if contentId is not None:
        changeTicketStatus = False

        try:
            content = Order_content.objects.get(pk=contentId)

            data = {"status": orderStatus}

            oldContent = content.status

            serializedData = Order_content_serializer(instance=content, data=data, partial=True)

            orders = Order.objects.get(pk=ticketId,vendorId=vendorId)

            oldStatus = orders.order_status

            recall= Order_content.objects.get(pk=contentId).isrecall

            if serializedData.is_valid():
                serializedData.save()
                oc = Order_content.objects.filter(orderId=ticketId)
                Order_content.objects.filter(pk=contentId).update(status=orderStatus,isrecall=recall)
                
                # TEMP
                if oc.filter(status=komsOrderStatus.PROCESSING).count() > 0:
                    processStation(oldStatus=str(oldStatus),currentStatus=str(komsOrderStatus.PROCESSING),orderId=orders.pk,station=content.stationId,vendorId=vendorId)
                #
                
                if oc.exclude(status__in = [
                    komsOrderStatus.READY, komsOrderStatus.ONHOLD, komsOrderStatus.CANCELED, komsOrderStatus.RECALL
                ]).count() == oc.filter(status=komsOrderStatus.PROCESSING).count():
                    if content.orderId.order_status in [ASSIGN, ONHOLD]:
                        changeTicketStatus = True 

                        Order.objects.filter(id=content.orderId.pk,vendorId=vendorId).update(order_status=PROCESSING) 
                        
                        webSocketPush(message={"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",}, room_name=str(vendorId)+"-"+str(oldStatus), username="CORE",)  # wheel remove order
                
                if oc.count() == oc.filter(status=komsOrderStatus.CANCELED).count():
                    changeTicketStatus=True

                    Order.objects.filter(id=content.orderId.pk,vendorId=vendorId).update(order_status=CANCELED, isHigh=False)
                    
                    webSocketPush(message={"id": orders.pk, "orderId": orders.externalOrderId,"UPDATE": "REMOVE",}, room_name=str(vendorId)+"-"+str(oldStatus),username="CORE",)  # wheel remove order
                
                elif oc.exclude(status=komsOrderStatus.CANCELED).count() == oc.filter(status=komsOrderStatus.READY).count():
                    if orders.order_status != 3:
                        changeTicketStatus = True
                        
                        webSocketPush(message={"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",}, room_name=str(vendorId)+"-"+str(oldStatus) ,username="CORE",)  # wheel remove order
                     
                    # if oc.count() == oc.filter(status=komsOrderStatus.READY).count():
                    Order.objects.filter(id=content.orderId.pk,vendorId=vendorId).update(order_status=READY, isHigh=False)
                
                if oc.count() == 1:
                    Order.objects.filter(id=content.orderId.pk,vendorId=vendorId).update(order_status=READY, isHigh=False)
                    
                    changeTicketStatus=True
                    
                    webSocketPush(message={"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",}, room_name=str(vendorId)+"-"+str(oldStatus), username="CORE",)                      

                if content.status==komsOrderStatus.RECALL:
                    Order_content.objects.exclude(status__in =[komsOrderStatus.READY,komsOrderStatus.CANCELED,komsOrderStatus.RECALL]).filter(pk=content.pk).update(status=str(PROCESSING),isrecall=True)
                    
                    Order.objects.filter(id=content.orderId.pk,vendorId=vendorId).update(order_status=PROCESSING, isHigh=False)
                    
                    if oldStatus != PROCESSING:
                        changeTicketStatus = True

                        webSocketPush(message={"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",}, room_name=str(vendorId)+"-"+str(oldStatus), username="CORE",)  # wheel remove order
                        
                order_content = Order_content.objects.filter(orderId=ticketId)
                
                status_list = tuple(order_content.values_list("status", flat=True).distinct())

                # 4=Onhold, 8=Assign
                if ('4' in status_list) and ('8' not in status_list):
                    changeTicketStatus = True
                    
                    Order.objects.filter(id=content.orderId.pk, vendorId=vendorId).update(order_status=ONHOLD)
                    
                    webSocketPush(
                        message={"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE"},
                        room_name=str(vendorId) + "-" + str(oldStatus),
                        username="CORE",
                    )
                
                if not changeTicketStatus:
                    webSocketPush(message=getOrder(ticketId=ticketId,vendorId=vendorId), room_name=str(vendorId)+"-"+str(Order.objects.get(pk=ticketId,vendorId=vendorId).order_status), username="CORE")
                
                webSocketPush(message=stationQueueCount(vendorId=vendorId), room_name=WHEELSTATS+str(vendorId), username="CORE")  # wheel man left side
                webSocketPush(message=statuscount(vendorId=vendorId), room_name=STATUSCOUNT, username="CORE")  # wheel man status count
                webSocketPush(message=CategoryWise(vendorId=vendorId), room_name=STATIONSIDEBAR, username="CORE")
                
                ####++++ Here We are processing station sockets
                processStation(
                    oldStatus=oldContent,
                    currentStatus=Order_content.objects.get(pk=content.pk).status,
                    orderId=content.orderId.pk,station=content.stationId,
                    vendorId=vendorId
                )
                # singleStationWiseRemove(id=content.orderId.pk,old=oldContent,current=Order_content.objects.get(pk=content.pk).status,stn=content.stationId)
                # allStationWiseSingle(id=ticketId,vendorId=vendorId)
                ####+++++++++
                subtotal = 0

                for cont in Order_content.objects.filter(orderId=orders.pk).exclude(status__in =[komsOrderStatus.CANCELED]):
                    prodData = Product.objects.filter(PLU=cont.SKU, vendorId_id=request.GET.get("vendorId")).first()
                    
                    subtotal = subtotal + (prodData.productPrice * cont.quantity)
                    
                    for mod in Order_modifer.objects.filter(contentID=cont.pk):
                        modifierData = ProductModifier.objects.filter(modifierPLU=mod.SKU, vendorId=request.GET.get("vendorId")).first()
                        
                        subtotal = subtotal + (modifierData.modifierPrice * mod.quantity)
                
                master_order_instance = coreOrder.objects.filter(pk=orders.master_order.pk).first()
                
                master_order_instance.subtotal = subtotal
                
                tax_total = 0

                for tax in Tax.objects.filter(vendorId=request.GET.get("vendorId")):
                    tax_total = tax_total + (master_order_instance.subtotal * (tax.percentage / 100))
                
                master_order_instance.tax = tax_total
                
                master_order_instance.TotalAmount = master_order_instance.subtotal + tax_total
                
                master_order_instance.save()
                
                waiteOrderUpdate(orderid=ticketId, language=language, vendorId=vendorId)
                
                updateCoreOrder(order=Order.objects.get(pk=ticketId,vendorId=vendorId))
                
                allStationWiseCategory(vendorId=vendorId)  # all stations sidebar category wise counts
                
                return Response(serializedData.data, status=status.HTTP_200_OK)
        
        except:
            return Response({"error": "Invalid ticket Id"}, status=status.HTTP_400_BAD_REQUEST)

    if ticketId is not None:
        try:
            orders = Order.objects.get(pk=ticketId,vendorId=request.GET.get("vendorId"))
        
        except:
            orders = Order.objects.filter(pk=ticketId,vendorId=request.GET.get("vendorId")).first()
        
        try:
            oldStatus = orders.order_status

            if ticketStatus in [1, 2, 3, 4, 5, 7, 8,9,10]:

                order_status = orderStatus

                if ticketStatus == 7:
                    Order.objects.filter(pk=ticketId,vendorId=request.GET.get("vendorId")).update(isHigh=True)
                    
                    Order_content.objects.filter(orderId=ticketId).update(status=8)
                
                elif ticketStatus==8:
                    if oldStatus==6:
                        for i in Order_content.objects.filter(orderId=ticketId):
                            if i.status == "6":
                                i.status = order_status
                                i.save()
                    
                    else:
                        Order_content.objects.filter(orderId=ticketId).update(status=orderStatus)
                
                elif ticketStatus in [4,5]  :
                    Order_content.objects.exclude(status__in =['3','5','6']).filter(orderId=ticketId).update(status=str(orderStatus))
                
                elif ticketStatus in [3, 5]:
                    Order_content.objects.filter(orderId=ticketId).exclude(status__in =[komsOrderStatus.CANCELED]).update(status=str(orderStatus))
                    
                    Order.objects.filter(id=ticketId).update(isHigh=False)
                
                if oldStatus == 7:
                    Order_content.objects.filter(orderId=ticketId).update(status=str(orderStatus))
                    
                    Order.objects.filter(id=ticketId,vendorId=request.GET.get("vendorId")).update(isHigh=True)
                
                elif oldStatus in [2,4]:
                    Order_content.objects.exclude(status__in =['3','5','6']).filter(orderId=ticketId).update(status=str(orderStatus))
                
                Order.objects.filter(id=ticketId,vendorId=request.GET.get("vendorId")).update(order_status=order_status)
            

            elif ticketStatus == 6:
                order_status = orderStatus
                
                Order.objects.filter(id=ticketId,vendorId=request.GET.get("vendorId")).update(order_status=order_status)
                
                Order_content.objects.exclude(status__in =['3','5','6']).filter(orderId=ticketId).update(status=order_status)
          
            data = {"order_status": orderStatus}
            
            serializedData = Order_serializer(instance=orders, data=data, partial=True)
            
            if serializedData.is_valid():
                serializedData.save()

            if Order.objects.get(pk=ticketId, vendorId=request.GET.get("vendorId")).order_status==HIGH:
                Order.objects.filter(pk=ticketId, vendorId=request.GET.get("vendorId")).update(isHigh=True) # Set priority till ticket is canceled or closed
                
                Order.objects.filter(pk=ticketId, vendorId=request.GET.get("vendorId")).update(order_status=ASSIGN)
            
            elif Order.objects.get(pk=ticketId ,vendorId=request.GET.get("vendorId")).order_status in [3, 5]:
                Order.objects.filter(id=ticketId, vendorId=request.GET.get("vendorId")).update(isHigh=False)
            
            webSocketPush(message={"id": orders.pk,"orderId": orders.externalOrderId, "UPDATE": "REMOVE",}, room_name=str(vendorId)+'-'+str(oldStatus), username="CORE",)  # WheelMan order remove order from old status
            
            for cont in Order_content.objects.filter(orderId=orders.pk):
                processStation(oldStatus=str(oldStatus), currentStatus=str(orderStatus), orderId=orders.pk, station=cont.stationId, vendorId=vendorId)
            
            allStationWiseRemove(id=orders.pk, old=str(oldStatus), current=str(orderStatus), vendorId=vendorId)
            allStationWiseSingle(id=ticketId, vendorId=vendorId)
           
            waiteOrderUpdate(orderid=ticketId, language=language, vendorId=vendorId)
            
            allStationWiseCategory(vendorId=vendorId)  # all stations sidebar category wise counts
            
            updateCoreOrder(order=Order.objects.get(pk=ticketId))

            return Response(serializedData.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response( {"error": "Invalid ticket Id"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        print("invalid arguments")
        return Response({"error": "invalid arguments"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def assignChef(request):
    requestJson = JSONParser().parse(request)
    contentId = requestJson.get("contentId")
    chefId = requestJson.get("chefId")
    ticketId = requestJson.get("ticketId")
    orderStatus = requestJson.get("orderStatus")
    ticketChange=False
    vendorId=request.GET.get("vendorId")
    if contentId is not None:
        data = {
            "staffId": chefId,
            "contentID": contentId,
        }
        try:
            try:
                contentAssign = Content_assign.objects.get(contentID=contentId)
            except:
                contentAssign = None

            orderContent = Order_content.objects.get(pk=contentId)
            oc = Order_content.objects.filter(orderId=orderContent.orderId.pk)
            oldStatus = orderContent.orderId.order_status
            if not contentAssign:
                contentSeral = Content_assign_serializer(data=data)
                contentData = {"status": 2}  # assign
                orderContentSerializer = Order_content_serializer(instance=orderContent, data=contentData, partial=True)
                if orderContentSerializer.is_valid():
                    orderContentSerializer.save()
                if oc.exclude(status__in={komsOrderStatus.READY,komsOrderStatus.CANCELED}).count() == oc.filter(status=komsOrderStatus.PROCESSING).count():
                    ticketChange=True
                    Order.objects.filter(pk=orderContent.orderId.pk,vendorId=vendorId).update(order_status=2)
                    webSocketPush(message={"id": orderContent.orderId.pk,"orderId": orderContent.orderId.externalOrderId,"UPDATE": "REMOVE",},room_name=str(vendorId)+"-"+str(oldStatus),username="CORE",)  # wheel remove order
                    # allStationWiseRemove(id=orderContent.orderId.pk,old=oldStatus,current=orderStatus,vendorId=vendorId)
            else:
                Order_content.objects.filter(pk=contentId).update(status=2)
                contentSeral = Content_assign_serializer(instance=contentAssign, data=data)
                if oc.exclude(status__in=[komsOrderStatus.READY,komsOrderStatus.CANCELED]).count() == oc.filter(status=komsOrderStatus.PROCESSING).count():
                    if Order.objects.get(pk=orderContent.orderId.pk,vendorId=vendorId).order_status !=2:
                        ticketChange=True
                        Order.objects.filter(pk=orderContent.orderId.pk,vendorId=vendorId).update(order_status=2)
                        webSocketPush(message={"id": orderContent.orderId.pk,"orderId": orderContent.orderId.externalOrderId,"UPDATE": "REMOVE",},room_name=str(vendorId)+"-"+str(oldStatus),username="CORE",)  # wheel remove order
                        # allStationWiseRemove(id=orderContent.orderId.pk,old=oldStatus,current=orderStatus,vendorId=vendorId)

            if contentSeral.is_valid():
                oldStatus = orderContent.orderId.order_status
                contentSeral.save()

                order_content = Order_content.objects.filter(orderId=orderContent.orderId.pk)
                
                status_list = tuple(order_content.values_list("status", flat=True).distinct())
                print(f"\nstatus_list: {status_list}\n")

                # 4=Onhold, 8=Assign
                if ('4' in status_list) and ('8' not in status_list):
                    ticketChange=True

                    Order.objects.filter(pk=orderContent.orderId.pk,vendorId=vendorId).update(order_status=ONHOLD)
                    
                    webSocketPush(
                        message={"id": orderContent.orderId.pk,"orderId": orderContent.orderId.externalOrderId,"UPDATE": "REMOVE"},
                        room_name=str(vendorId)+"-"+str(oldStatus),
                        username="CORE"
                    )
                elif ('2' in status_list) and ('8' not in status_list):
                    webSocketPush(message={
                        "oldStatus": oldStatus,
                        "newStatus": orderContent.status,
                        "id": orderContent.orderId.pk,
                        "orderId": orderContent.orderId.externalOrderId,
                        "UPDATE": "REMOVE"
                    },room_name=STATION+str(orderContent.stationId.pk),username="CORE")
                # TEMP
                if oc.filter(status=komsOrderStatus.PROCESSING).exists():
                    webSocketPush(message={"oldStatus": oldStatus,"newStatus": str(komsOrderStatus.PROCESSING),"id": orderContent.orderId.pk,"orderId": orderContent.orderId.externalOrderId,"UPDATE": "REMOVE"},room_name=STATION+str(orderContent.stationId.pk),username="CORE")
                    processStation(oldStatus=str(oldStatus),currentStatus=str(komsOrderStatus.PROCESSING),orderId=orderContent.orderId.pk,station=orderContent.stationId,vendorId=vendorId)
                #

                if not ticketChange:
                    webSocketPush(message=getOrder(ticketId=ticketId,vendorId=vendorId),room_name=str(vendorId)+"-"+ str(orderStatus), username="CORE")
                    webSocketPush(message=getOrder(ticketId=ticketId,vendorId=vendorId), room_name=str(vendorId)+"-"+ str(Order.objects.get(pk=ticketId,vendorId=vendorId).order_status), username="CORE") # Update items status if ticket status is not changed
                webSocketPush(message=stationQueueCount(vendorId=vendorId),room_name= WHEELSTATS+str(vendorId),username= "CORE")  # wheel man left side
                # removeFromInqueueAndInsertInProcessing(id=orderContent.orderId.pk,old=oldStatus,current=orderContent.status,stn=orderContent.stationId)
                # singleStationWiseRemove(id=orderContent.orderId.pk,old=oldStatus,current=orderContent.status,stn=orderContent.stationId)
                allStationWiseSingle(id=orderContent.orderId.pk,vendorId=vendorId)
                waiteOrderUpdate(orderid=orderContent.orderId.pk,vendorId=vendorId)## Bug fix[1]:
            else:
                # print(contentSeral.errors)
                return Response({"error": "Something went wrong"},status=status.HTTP_400_BAD_REQUEST,)
        except Exception as e:
            print(e)
            return Response({"error": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
    webSocketPush(message=statuscount(vendorId=vendorId),room_name= STATUSCOUNT+str(vendorId),username= "CORE")  # wheel man status count
    return Response(contentSeral.data, status=status.HTTP_200_OK)


def statuscount(vendorId):
    date = datetime.today().strftime("20%y-%m-%d")
    result = {}
    for i in KOMSOrderStatus.objects.all():
        result[i.get_status_display()] = Order.objects.filter(order_status=i.pk, arrival_time__contains=date,vendorId=vendorId).count()
    return result


def getOrder(ticketId, vendorId, language="English"):
    try:
        singleOrder = Order.objects.get(pk=ticketId,vendorId=vendorId)
    
    except:
        singleOrder = Order.objects.filter(pk=ticketId,vendorId=vendorId).first()

    mapOfSingleOrder = {}

    mapOfSingleOrder["id"] = singleOrder.pk
    mapOfSingleOrder["orderId"] = singleOrder.externalOrderId
    mapOfSingleOrder["master_order_id"] = singleOrder.master_order.pk
    mapOfSingleOrder["orderType"] = singleOrder.order_type

    pickupTime = singleOrder.pickupTime

    if pickupTime == singleOrder.arrival_time:
        pickupTime += timedelta(minutes=30)

    if singleOrder.order_note:
        order_note = singleOrder.order_note

    else:
        if language == "English":
            order_note = "None"

        else:
            order_note = language_localization["None"]

    waiters = ""
    waiter_names = []

    if singleOrder.server:
        waiter_ids_string = singleOrder.server

        waiter_id_list = waiter_ids_string.split(',')

        if language == "English":
            for waiter_id in waiter_id_list:
                waiter_instance = Waiter.objects.filter(pk=int(waiter_id), vendorId=vendorId).first()
                
                waiter_names.append(waiter_instance.name)

        else:
            for waiter_id in waiter_id_list:
                waiter_instance = Waiter.objects.filter(pk=int(waiter_id), vendorId=vendorId).first()

                waiter_names.append(waiter_instance.name_locale)

        waiters = waiters = ', '.join(waiter_names)

    mapOfSingleOrder["pickupTime"] =  pickupTime.astimezone(pytz.timezone('Asia/Kolkata')).strftime("20%y-%m-%dT%H:%M:%S")
    mapOfSingleOrder["arrivalTime"] = singleOrder.arrival_time.astimezone(pytz.timezone('Asia/Kolkata')).strftime("20%y-%m-%dT%H:%M:%S")
    mapOfSingleOrder["order_datetime"] = singleOrder.master_order.OrderDate.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%dT%H:%M:%S")
    mapOfSingleOrder["is_edited"] = singleOrder.is_edited
    mapOfSingleOrder["edited_at"] = singleOrder.edited_at.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%dT%H:%M:%S")
    mapOfSingleOrder["deliveryIsAsap"] = singleOrder.deliveryIsAsap
    mapOfSingleOrder["note"] = order_note
    mapOfSingleOrder["remake"] = False
    mapOfSingleOrder["customerName"] = ""
    mapOfSingleOrder["status"] = singleOrder.order_status
    mapOfSingleOrder["guest"] = singleOrder.guest
    mapOfSingleOrder["server"] = waiters

    try:
        orderTables = Order_tables.objects.filter(orderId_id=singleOrder.pk)

        listOfTableNumber = " "

        listOfTableIds = []

        for orderTable in orderTables:
            listOfTableNumber += str(orderTable.tableId.tableNumber) + ","
            listOfTableIds.append(orderTable.tableId.pk)

        mapOfSingleOrder["tableIds"] = listOfTableIds
        mapOfSingleOrder["tableNo"] = listOfTableNumber[:-1]

    except Order_tables.DoesNotExist:
            print("Order table not found")
            mapOfSingleOrder["tableIds"] = []
            mapOfSingleOrder["tableNo"] = ""

    mapOfSingleOrder["tableId"] = 1 #HotelTable.objects.filter(tableNumber=singleOrder.tableNo).first().pk
    mapOfSingleOrder["isHigh"] = singleOrder.isHigh

    orderContentList = Order_content.objects.filter(orderId=singleOrder.pk).order_by('-pk')

    items = {}

    for singleContent in orderContentList:
        mapOfSingleContent = {}

        product_name = ""
        station_name = ""
        
        if language == "English":
            product_name = singleContent.name
            station_name = singleContent.stationId.station_name

        else:
            product_instance = Product.objects.filter(PLU=singleContent.SKU, vendorId=vendorId).first()

            product_name = product_instance.productName_locale
            station_name = singleContent.stationId.station_name_locale

        mapOfSingleContent["id"] = singleContent.pk
        mapOfSingleContent["plu"] = singleContent.SKU
        mapOfSingleContent["name"] = product_name
        mapOfSingleContent["quantity"] = singleContent.quantity
        mapOfSingleContent["status"] = singleContent.status
        mapOfSingleContent["stationId"] = singleContent.stationId.pk
        mapOfSingleContent["stationName"] = station_name
        mapOfSingleContent["isRecall"] = singleContent.isrecall
        mapOfSingleContent["isEdited"] = singleContent.isEdited

        product_image = ""
        product_price = 0.0
        recipe_video_url = ""
        
        product_instance = Product.objects.filter(PLU=singleContent.SKU, vendorId=vendorId).first()

        if product_instance:
            product_price = product_instance.productPrice
            recipe_video_url = product_instance.recipe_video_url if product_instance.recipe_video_url else ""

            product_image_instance = ProductImage.objects.filter(product=product_instance.pk).first()

            if product_image_instance:
                product_image = product_image_instance.url

        mapOfSingleContent["image"] = product_image
        mapOfSingleContent["price"] = product_price
        mapOfSingleContent["recipe_video_url"] = recipe_video_url
        
        try:
            conAssign = Content_assign.objects.get(contentID=singleContent.pk)
            mapOfSingleContent["chefId"] = conAssign.staffId.pk
            mapOfSingleContent["assignedChef"] = conAssign.staffId.last_name
        
        except Content_assign.DoesNotExist:
            mapOfSingleContent["chefId"] = 0

        mapOfSingleContent["quantityStatus"] = singleContent.quantityStatus
        mapOfSingleContent["itemRemark"] = singleContent.note if singleContent.note and singleContent.note!="" and singleContent.note is not None  else ""

        orderContentModifierList = Order_modifer.objects.filter(contentID=singleContent.pk, status="1")

        modList = []

        for singleContentModifier in orderContentModifierList:
            if singleContentModifier.quantity > 0 :
                mapOfSingleModifier = {}

                modifier_name = ""

                modifier_instance = ProductModifier.objects.filter(
                    modifierPLU=singleContentModifier.SKU, vendorId=vendorId
                ).first()
                
                if language == "English":
                    modifier_name = modifier_instance.modifierName

                else:
                    modifier_name = modifier_instance.modifierName_locale

                mapOfSingleModifier["id"] = singleContentModifier.pk
                mapOfSingleModifier["plu"] = singleContentModifier.SKU
                mapOfSingleModifier["name"] = modifier_name
                mapOfSingleModifier["quantityStatus"] = singleContentModifier.quantityStatus
                mapOfSingleModifier["quantity"] = singleContentModifier.quantity

                try:
                    mapOfSingleModifier["price"] = modifier_instance.modifierPrice
                
                except:
                    mapOfSingleModifier["price"] = 0

                modList.append(mapOfSingleModifier)

        mapOfSingleContent["subItems"] = modList

        if singleContent.categoryName in items.keys():
            alreayList = items[singleContent.categoryName]
            alreayList.append(mapOfSingleContent)
        
        else:
            items[singleContent.categoryName] = [mapOfSingleContent]

    mapOfSingleOrder["items"] = items

    return mapOfSingleOrder


def stationQueueCount(vendorId):
    try:
        date = datetime.today().strftime(
            "20%y-%m-%d"
        )
        all_orders = Order.objects.filter(arrival_time__contains=date,vendorId=vendorId).values_list("id")
        stationList = Station.objects.filter(isStation=True,vendorId=vendorId)
        statusName = KOMSOrderStatus.objects.all()
        response = {}
        for station in stationList:
            station_details = {
                # "id": station.id,
                # "name": station.station_name,
                # "colorCode": station.color_code
            }
            for singleStatus in statusName:
                test = Order_content.objects.filter(
                    orderId__in=all_orders, stationId=station.pk, status=singleStatus.pk
                )
                station_details[singleStatus.status] = len(test)
                response[station.station_name] = station_details
        return response
    except:
        pass


def stationCategoryWise(id,vendorId):
    date = datetime.today().strftime("20%y-%m-%d")  # order_status=int(self.room_name),
    all_orders = Order.objects.exclude(order_status__in=[PENDING,CLOSE,CANCELED]).filter(arrival_time__contains=date,vendorId=vendorId).values_list("pk")
    orderContents = (
        Order_content.objects.exclude(status__in=["1","5","10"]).filter(orderId__in=all_orders, stationId=id)
        .values("categoryName", "name")
        .annotate(count=Count("name"), qty=Sum("quantity"))
    )
    result = {}
    try:
        for sigleContent in orderContents:
            if sigleContent["categoryName"] in result:
                singleList = result[sigleContent["categoryName"]]
                singleList.append(sigleContent)
                result[sigleContent["categoryName"]] = singleList
            else:
                result[sigleContent["categoryName"]] = [sigleContent]
    except:
        pass
    return result


def CategoryWise(vendorId):
    date = datetime.today().strftime("20%y-%m-%d")  # order_status=int(self.room_name),
    all_orders = Order.objects.exclude(order_status__in=[PENDING,CLOSE,CANCELED]).filter(arrival_time__contains=date,vendorId=vendorId).values_list("pk")
    orderContents = (
        Order_content.objects.exclude(status__in=["1","5","10"]).filter(orderId__in=all_orders)
        .values("categoryName", "name")
        .annotate(count=Count("name"), qty=Sum("quantity"))
    )
    result = {}
    try:
        for sigleContent in orderContents:
            result[sigleContent["categoryName"]] = [sigleContent]
    except:
        pass
    return result


def allStationWiseCategory(vendorId):
    stationList = Station.objects.filter(vendorId=vendorId)
    for station in stationList:
        webSocketPush(
            message=stationCategoryWise(id=station.pk,vendorId=vendorId),room_name= STATIONSIDEBAR + str(station.pk),username= "CORE"
        )
    webSocketPush(message=CategoryWise(vendorId=vendorId),room_name= STATIONSIDEBAR, username="CORE")
    return


def allStationData(vendorId):
    date = datetime.today().strftime("20%y-%m-%d")
    orderList = Order.objects.filter(arrival_time__contains=date,vendorId=vendorId)
    stationWise = {}
    for singleOrder in orderList:
        mapOfSingleOrder = getOrder(ticketId=singleOrder.pk,vendorId=vendorId)
        if singleOrder.order_status in stationWise:
            singleMap = stationWise[singleOrder.order_status]
            singleMap[singleOrder.externalOrderId] = mapOfSingleOrder
        else:
            stationWise[singleOrder.order_status] = {singleOrder.externalOrderId: mapOfSingleOrder}
    for i in stationWise:
        stationWise[i]= dict(sorted(stationWise[i].items(), key=lambda x: not x[1]["isHigh"])) # Station put high priority tickets at begining
    return stationWise


# Data per station
def stationdata(id,vendorId):
    stationWise={}
    date = datetime.today().strftime("20%y-%m-%d")

    ####+++++++
    for singleOrder in Order.objects.filter(arrival_time__contains=date,vendorId=vendorId):
        orderContents=Order_content.objects.filter(stationId=id,orderId=singleOrder)
        totalContentsCount=orderContents.count()
        if orderContents:
            mapOfSingleOrder = getOrder(ticketId=singleOrder.pk,vendorId=vendorId)
            data= dict(sorted(mapOfSingleOrder['items'].items(), key=lambda x: x[1][0]["stationId"] != int(id)))
            mapOfSingleOrder['items']=data

            if orderContents.filter(status=komsOrderStatus.PROCESSING).exists():
                if komsOrderStatus.PROCESSING in stationWise:
                    singleMap = stationWise[komsOrderStatus.PROCESSING]
                    singleMap[singleOrder.externalOrderId] = mapOfSingleOrder 
                else:
                    stationWise[komsOrderStatus.PROCESSING] = {singleOrder.externalOrderId: mapOfSingleOrder}
            elif totalContentsCount==orderContents.filter(status=komsOrderStatus.CANCELED).count():
                if komsOrderStatus.CANCELED in stationWise:
                    singleMap = stationWise[komsOrderStatus.CANCELED]
                    singleMap[singleOrder.externalOrderId] = mapOfSingleOrder 
                else:
                    stationWise[komsOrderStatus.CANCELED] = {singleOrder.externalOrderId: mapOfSingleOrder}
            elif totalContentsCount==orderContents.filter(status__in=[komsOrderStatus.READY,komsOrderStatus.CANCELED]).count():
                if komsOrderStatus.READY in stationWise:
                    singleMap = stationWise[komsOrderStatus.READY]
                    singleMap[singleOrder.externalOrderId] = mapOfSingleOrder 
                else:
                    stationWise[komsOrderStatus.READY] = {singleOrder.externalOrderId: mapOfSingleOrder}

            elif orderContents.filter(status=komsOrderStatus.ONHOLD).exists():
                if komsOrderStatus.ONHOLD in stationWise:
                    singleMap = stationWise[komsOrderStatus.ONHOLD]
                    singleMap[singleOrder.externalOrderId] = mapOfSingleOrder 
                else:
                    stationWise[komsOrderStatus.ONHOLD] = {singleOrder.externalOrderId: mapOfSingleOrder}
            else:
                if orderContents.first().status in stationWise:
                    singleMap = stationWise[orderContents.first().status]
                    singleMap[singleOrder.externalOrderId] = mapOfSingleOrder 
                else:
                    stationWise[orderContents.first().status] = {singleOrder.externalOrderId: mapOfSingleOrder}

    ###++++++++

    # for single_content in Order_content.objects.filter(stationId=id):
    #     oldStatus=single_content.status
    #     for singleOrder in Order.objects.filter(arrival_time__contains=date,pk=single_content.orderId.pk,vendorId=vendorId):
    #         mapOfSingleOrder = getOrder(ticketId=singleOrder.pk,vendorId=vendorId)
    #         data= dict(sorted(mapOfSingleOrder['items'].items(), key=lambda x: x[1][0]["stationId"] != int(id)))
    #         mapOfSingleOrder['items']=data
    #         if single_content.status in stationWise:
    #             singleMap = stationWise[single_content.status]
    #             singleMap[singleOrder.externalOrderId] = mapOfSingleOrder 
    #         else:
    #             stationWise[single_content.status] = {singleOrder.externalOrderId: mapOfSingleOrder}

    ###++++Here we are shifting high priority orders to the start            
    for i in stationWise:
        stationWise[i]= dict(sorted(stationWise[i].items(), key=lambda x: not x[1]["isHigh"]))
    return stationWise


def processStation(oldStatus,currentStatus,orderId,station,vendorId):
    singleOrder= Order.objects.get(pk=orderId)
    ##++++++ Remove Order from old status
    webSocketPush(message={"oldStatus": oldStatus,"newStatus": currentStatus,"id": orderId,"orderId": singleOrder.externalOrderId,"UPDATE": "REMOVE"},room_name=STATION+str(station.pk),username="CORE")

    ##++++ Update order to all station
    
    for station in Station.objects.filter(vendorId=vendorId):#TODO temp id added
            orderContents=Order_content.objects.filter(stationId=station,orderId=singleOrder)
            if orderContents:
                totalContentsCount=orderContents.count()
                mapOfSingleOrder = getOrder(ticketId=singleOrder.pk,vendorId=vendorId)
                data= dict(sorted(mapOfSingleOrder['items'].items(), key=lambda x: x[1][0]["stationId"] != int(station.pk)))
                mapOfSingleOrder['items']=data
                if orderContents.filter(status=komsOrderStatus.PROCESSING).exists():
                    mapOfSingleOrder['status']= int(komsOrderStatus.PROCESSING)
                elif totalContentsCount==orderContents.filter(status=komsOrderStatus.CANCELED).count():
                    mapOfSingleOrder['status']=int(komsOrderStatus.CANCELED)
                elif totalContentsCount==orderContents.filter(status__in=[komsOrderStatus.READY,komsOrderStatus.CANCELED]).count():
                    mapOfSingleOrder['status']=int(komsOrderStatus.READY)
                elif orderContents.filter(status=komsOrderStatus.ONHOLD).exists():
                    mapOfSingleOrder['status']=int(komsOrderStatus.ONHOLD)
                webSocketPush(message=mapOfSingleOrder,room_name= STATION+str(station.pk),username= "CORE")
                if int(currentStatus) == ASSIGN:
                    notify(type=currentStatus,msg=singleOrder.id,desc=f"Order No { singleOrder.externalOrderId } is arrived",stn=[station.pk],vendorId=vendorId)


def singleStationWiseRemove(id,old,current,stn):
    try:
        # print("singleStationWiseRemove ",Order_content.objects.filter(orderId_id=id,stationId_id=stn.pk).count())
        if old==komsOrderStatus.PROCESSING:
            if Order_content.objects.filter(orderId_id=id,status=komsOrderStatus.PROCESSING,stationId_id=stn.pk).exists():
                current=komsOrderStatus.PROCESSING
        else:
            orderContents=Order_content.objects.filter(stationId=stn,orderId_id=id)
            if orderContents:
                totalContentsCount=orderContents.count()
                if totalContentsCount==orderContents.filter(status=komsOrderStatus.READY):
                        old=komsOrderStatus.READY
        webSocketPush(message={"oldStatus": old,"newStatus": current,"id": id,"orderId": Order.objects.get(pk=id).externalOrderId,"UPDATE": "REMOVE"},room_name=STATION+str(stn.pk),username="CORE")
        print("Station Remove ",{"oldStatus": old,"newStatus": current,"id": id,"orderId": Order.objects.get(pk=id).externalOrderId,"UPDATE": "REMOVE"})
    except Exception as e:
        print(e)


def removeFromInqueueAndInsertInProcessing(id,old,current,stn):
    try:
        ##++++ If station has any of item is in cooking don't remove it
        # allContentsOfStation=Order_content.objects.filter(orderId_id=id,stationId=stn)
        # print("id : ",id,"old : ",old,"current : ",current,"stn : ",stn.pk)
        # if allContentsOfStation.filter(status=komsOrderStatus.PROCESSING).count() ==1:
        webSocketPush(message={"oldStatus": old,"newStatus": current,"id": id,"orderId": Order.objects.get(pk=id).externalOrderId,"UPDATE": "REMOVE"},room_name=STATION+str(stn.pk),username="CORE")
    except Exception as e:
        print(e)


def allStationWiseData(vendorId):
    for i in Station.objects.filter(vendorId=vendorId):
        webSocketPush(message=stationdata(i.pk),room_name= STATION+str(i.pk),username= "CORE") 
        
        
def allStationWiseSingle(id,vendorId):
    ####+++++++
        singleOrder= Order.objects.get(pk=id)
        for station in Station.objects.filter(vendorId=vendorId):
            orderContents=Order_content.objects.filter(stationId=station,orderId=singleOrder)
            if orderContents:
                totalContentsCount=orderContents.count()
                mapOfSingleOrder = getOrder(ticketId=singleOrder.pk,vendorId=vendorId)
                data= dict(sorted(mapOfSingleOrder['items'].items(), key=lambda x: x[1][0]["stationId"] != int(station.pk)))
                mapOfSingleOrder['items']=data

                if orderContents.filter(status=komsOrderStatus.ASSIGN).exists():
                    mapOfSingleOrder['status']= int(komsOrderStatus.ASSIGN)
                elif orderContents.filter(status=komsOrderStatus.PROCESSING).exists():
                    mapOfSingleOrder['status']= int(komsOrderStatus.PROCESSING)
                elif totalContentsCount==orderContents.filter(status=komsOrderStatus.READY):
                    mapOfSingleOrder['status']=int(komsOrderStatus.READY)
                elif totalContentsCount==orderContents.filter(status=komsOrderStatus.CANCELED):
                    mapOfSingleOrder['status']=int(komsOrderStatus.CANCELED)
                elif orderContents.filter(status=komsOrderStatus.ONHOLD).exists():
                    mapOfSingleOrder['status']=int(komsOrderStatus.ONHOLD)
                # TEMP
                if orderContents.filter(status=komsOrderStatus.PROCESSING).exists():
                    mapOfSingleOrder['status']=int(komsOrderStatus.PROCESSING)                #
                #
                webSocketPush(message=mapOfSingleOrder,room_name= STATION+str(station.pk),username= "CORE")

    ###++++++++

    # for i in Station.objects.filter(vendorId=vendorId):
    #     mapOfSingleOrder = getOrder(ticketId=id,vendorId=vendorId)
    #     data= dict(sorted(mapOfSingleOrder['items'].items(), key=lambda x: x[1][0]["stationId"] != int(i.pk)))
    #     mapOfSingleOrder['items']=data
    #     webSocketPush(message=mapOfSingleOrder,room_name= STATION+str(i.pk),username= "CORE")


def allStationWiseRemove(id,old,current,vendorId):  
    for i in Station.objects.filter(vendorId=vendorId):
        webSocketPush(message={"oldStatus": old,"newStatus": current,"id": id,"orderId": Order.objects.get(pk=id).externalOrderId,"UPDATE": "REMOVE",},room_name=STATION+str(i.pk),username="CORE",)
        print("oldStatus : ", old,"newStatus : " ,current,"id : ", id,"orderId : ", Order.objects.get(pk=id).externalOrderId,)


def percent(a, b):
    try:
        return round(((a / b) * 100), 2)
    except:
        return 0


@api_view(["GET"])
def total_order_history(request):
    result = {}
    total = OrderHistory.objects.filter(vendorId=request.GET.get("vendorId")).count()
    complete = OrderHistory.objects.filter(order_status=3,vendorId=request.GET.get("vendorId")).count()
    cancel = OrderHistory.objects.filter(order_status=5,vendorId=request.GET.get("vendorId")).count()
    recall = OrderHistory.objects.filter(order_status=6,vendorId=request.GET.get("vendorId")).count()
    totalrecall = 0
    totaldelayno = 0
    totalrecallno = 0
    result["total"] = total
    result["complete"] = percent(complete, total)
    result["cancel"] = percent(cancel, total)
    for i in OrderHistory.objects.filter(vendorId=request.GET.get("vendorId")):
        totalrecall += i.recall
        if i.recall > 0:
            totalrecallno += 1
        if i.delay > 0:
            totaldelayno += 1
    return Response(result)


@api_view(["GET"])
def total_order_history_by_stations(request):
    stationchart = {}
    order = 0
    for i in Order.objects.filter(vendorId=request.GET.get("vendorId")):
        o = Order_content.objects.filter(orderId=i.pk).count()
        order += o
        stationchart["total"] = order
    for x in Station.objects.filter(isStation=1,vendorId=request.GET.get('vendorId')):
        content = 0
        for i in Order.objects.filter(vendorId=request.GET.get("vendorId")):
            count = Order_content.objects.filter(
                Q(orderId=i.pk) & Q(stationId=x.pk)
            ).count()
            if count > 0:
                content += count
                stationchart[x.station_name] = content
            else:
                stationchart[x.station_name] = count

    return Response(stationchart)


@api_view(["GET"])
def total_order_history_bydate(request, start, end):
    result = {}
    s_date = "2023-01-01" + " 00:00:00.000000"
    e_date = "2023-01-24" + " 23:59:59.000000"
    vendorId=request.GET.get("vendorId")
    total = OrderHistory.objects.filter(timestamp__range=(s_date, e_date),vendorId=vendorId).count()
    complete = OrderHistory.objects.filter(
        Q(order_status=3) & Q(timestamp__range=(s_date, e_date) & Q(vendorId=vendorId))
    ).count()
    cancel = OrderHistory.objects.filter(
        Q(order_status=5) & Q(timestamp__range=(s_date, e_date)) & Q(vendorId=vendorId)
    ).count()
    recall = OrderHistory.objects.filter(
        Q(order_status=6) & Q(timestamp__range=(s_date, e_date)) & Q(vendorId=vendorId)
    ).count()
    totalrecall = 0
    totaldelayno = 0
    totalrecallno = 0
    for i in OrderHistory.objects.filter(vendorId=Q(vendorId=vendorId)):
        totalrecall += i.recall
        if i.recall > 0:
            totalrecallno += 1
        if i.delay > 0:
            totaldelayno += 1
    result["total"] = total
    result["complete"] = percent(complete, total)
    result["cancel"] = percent(cancel, total)
    result["recall"] = percent(recall, total)
    result["delay"] = percent(totaldelayno, total)
    return JsonResponse(result)


@api_view(["GET"])
def total_order_by_stations_and_date(request, start, end):
    s_date = "2023-01-01" + " 00:00:00.000000"
    e_date = "2023-01-24" + " 23:59:59.000000"
    stationchart = {}
    order = 0
    for i in Order.objects.filter(arrival_time__range=(s_date, e_date),vendorId=request.GET.get("vendorId")):
        o = Order_content.objects.filter(orderId=i.pk).count()
        order += o
        stationchart["total"] = order
    for x in Station.objects.filter(isStation=1,vendorId=request.GET.get('vendorId')):
        content = 0
        for i in Order.objects.filter(arrival_time__range=(s_date, e_date),vendorId=request.GET.get("vendorId")):
            count = Order_content.objects.filter(
                Q(orderId=i.pk) & Q(stationId=x.pk)
            ).count()
            if count > 0:
                content += count
                stationchart[x.station_name] = percent(content, order)
            else:
                stationchart[x.station_name] = count
    return Response(stationchart)


def dictionary_to_list(dictionary):
        resultlist = []

        for key, value in dictionary.items():
            resultlist.append({"name": str(key).capitalize(), "value": value})

        return resultlist


@api_view(["GET"])
def chart_api(request, start_date, end_date):
    try:
        vendor_id = request.GET.get("vendorId")

        start_datetime = start_date + " 00:00:00.000000"
        end_datetime = end_date + " 23:59:59.000000"
        
        result = {}
        realtime = {}

        total_orders = Order.objects.filter(master_order__OrderDate__range=(start_datetime, end_datetime), vendorId=vendor_id)
        
        total_order_count = total_orders.count()
        inqueue_order_count = total_orders.filter(order_status=1).count()
        cooking_order_count = total_orders.filter(order_status__in=(2,6,7)).count()
        complete_order_count = total_orders.filter(order_status=3).count()
        onhold_order_count = total_orders.filter(order_status=4).count()
        cancel_order_count = total_orders.filter(order_status=5).count()
        assign_order_count = total_orders.filter(order_status=8).count()
        close_order_count = total_orders.filter(order_status=10).count()

        realtime['Inqueue'] = percent(inqueue_order_count, total_order_count)
        realtime['Cooking'] = percent(cooking_order_count, total_order_count)
        realtime['Complete'] = percent(complete_order_count, total_order_count)
        realtime['OnHold'] = percent(onhold_order_count, total_order_count)
        realtime['Cancel'] = percent(cancel_order_count, total_order_count)
        realtime['Assign'] = percent(assign_order_count, total_order_count)
        realtime['Close'] = percent(close_order_count, total_order_count)
        
        result["realtime"] = dictionary_to_list(realtime)

        # total order history
        history = {}

        total_orders = OrderHistory.objects.filter(timestamp__range=(start_datetime, end_datetime), vendorId=vendor_id)
        
        total_orders_count = total_orders.count()

        complete_order_count = total_orders.filter(order_status=3).count()
        cancel_order_count = total_orders.filter(order_status=5).count()
        
        history["complete"] = percent(complete_order_count, total_orders_count)
        history["cancel"] = percent(cancel_order_count, total_orders_count)

        result["orderHistory"] = history

        # stations
        stationchart = {}
        order = 0

        total_orders = Order.objects.filter(arrival_time__range=(start_datetime, end_datetime), vendorId=vendor_id)

        for i in total_orders:
            order = order + Order_content.objects.filter(orderId=i.pk).count()
        
        for x in Station.objects.filter(isStation=1, vendorId=vendor_id):
            content = 0

            for i in total_orders:
                count = Order_content.objects.filter(Q(orderId=i.pk) & Q(stationId=x.pk)).count()

                if count > 0:
                    content = content + count

                    stationchart[x.station_name] = percent(content, order)

                else:
                    stationchart[x.station_name] = percent(count, order)
        
        result["stations"] = dictionary_to_list(stationchart)

        # history of completed order
        complete_orders = OrderHistory.objects.filter(order_status=3, timestamp__range=(start_datetime, end_datetime), vendorId=vendor_id)
        
        complete_order_data = {
            "delay": percent(complete_orders.filter(Q(delay__gt=10) & Q(recall=0)).count(), complete_orders.count()),
            "recall": percent(complete_orders.filter(recall=1).count(), complete_orders.count()),
        }

        result["complete"] = dictionary_to_list(complete_order_data)

        # history of canceled order
        cancel_orders = OrderHistory.objects.filter(order_status=5, timestamp__range=(start_datetime, end_datetime), vendorId=vendor_id)
        
        cancel_order_data = {
            "delay": percent(cancel_orders.filter(Q(delay__gt=10) & Q(recall=0)).count(), cancel_orders.count()),
            "recall": percent(cancel_orders.filter(recall=1).count(), cancel_orders.count()),
        }

        result["cancel"] = dictionary_to_list(cancel_order_data)

        # sources
        source = {}

        result["source"] = dictionary_to_list(source)

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        current_date = start_date

        data = []

        while current_date <= end_date:
            store_timing = StoreTiming.objects.filter(day=current_date.strftime("%A"), vendor=vendor_id).first()

            if store_timing:
                start_time = datetime.combine(current_date, store_timing.open_time)

                if end_date == datetime.now().date():
                    end_time = datetime.combine(current_date, time(datetime.now().time().hour, 0, 0))
                else:
                    end_time = datetime.combine(current_date, store_timing.close_time)

                current_time = start_time

                while current_time <= end_time:
                    orders = Order.objects.filter(arrival_time__range=(current_time, current_time + timedelta(hours=1)), vendorId=vendor_id)

                    newdata = {"date": str(current_time), "count": orders.count()}

                    data.append(newdata)

                    current_time = current_time + timedelta(hours=1)

            else:
                return JsonResponse({"error": "Store open time not set"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            current_date = current_date + timedelta(days=1)

        if len(data) == 1:
            existing_datetime = data[0]["date"]

            existing_datetime_obj = datetime.strptime(existing_datetime, '%Y-%m-%d %H:%M:%S')

            temp_date = existing_datetime_obj - timedelta(hours=1)

            temp_date = temp_date.strftime('%Y-%m-%d %H:%M:%S')

            data.append({"date": temp_date, "count": 0})
        
        graph_data = []
        count = 0

        for iterator in data:
            count = count + iterator["count"]

            newdata = {"date": iterator["date"], "count": count}

            graph_data.append(newdata)

        result["date"] = graph_data

        return Response(result)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def massages(request, start, end):
    s_date = start + " 00:00:00.000000"
    e_date = end + " 23:59:59.000000"
    total = {}
    ready = {}
    cancel = {}
    succ = []
    canc = []
    for j in Order.objects.filter(Q(arrival_time__range=(s_date, e_date)) & Q(vendorId=request.GET.get("vendorId"))):
        if j.order_status == 3:
            succ.append(j.pk)
        if j.order_status == 5:
            canc.append(j.pk)
    for i in Message_type.objects.filter(vendorId=request.GET.get("vendorId")):
        ready[i.massage_type] = percent(
            massage_history.objects.filter(
                massage_type=i.pk, order_id__in=succ
            ).count(),
            massage_history.objects.filter(order_id__in=succ).count(),
        )
        cancel[i.massage_type] = percent(
            massage_history.objects.filter(
                massage_type=i.pk, order_id__in=canc
            ).count(),
            massage_history.objects.filter(order_id__in=canc).count(),
        )
        total[i.massage_type] = percent(
            massage_history.objects.filter(massage_type=i.pk).count(),
            massage_history.objects.filter(vendorId=request.GET.get("vendorId")).count(),
        )
    return Response({"total": total, "complete": ready, "cancel": cancel})


@api_view(["POST"])
def additem(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language", "English")

        if not vendor_id:
            return JsonResponse({"message": "Invalid vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)

        except ValueError:
            return JsonResponse({"message": "Invalid vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return JsonResponse({"message": "Vendor does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        new_items = dict(request.data)

        order = Order.objects.get(pk=new_items['orderId'], vendorId=vendor_id)

        old_status = order.order_status
        
        station_instance = Station.objects.filter(vendorId=vendor_id).first()

        subtotal = 0

        for single_product in new_items["products"]:
            modifier_list = []
            
            for modifier_group in single_product['modifiersGroup']:
                for modifier in modifier_group['modifiers']:
                    modifier["group"] = ProductModifierGroup.objects.filter(PLU=modifier_group['plu'], vendorId=vendor_id).first().pk
                    modifier_list.append(modifier)

            product_instance = Product.objects.filter(pk=single_product['productId'], vendorId=vendor_id).first()

            order_status = 8

            if order.order_status == 1:
                order_status = 1

            product_note = None

            if single_product['note']:
                product_note = single_product['note']

            category_instance = ProductCategory.objects.filter(pk=single_product['categoryId'], vendorId=vendor_id).first()

            if category_instance:
                station_instance = category_instance.categoryStation

            single_product["orderId"] = new_items['orderId']
            single_product['name'] = product_instance.productName
            single_product["quantityStatus"] = 1
            single_product["stationId"] = station_instance.pk
            single_product['unit'] = "qty"
            single_product["stationName"] = station_instance.station_name
            single_product["chefId"] = 0
            single_product["note"] = product_note
            single_product["SKU"] = single_product["plu"]
            single_product["status"] = order_status
            
            single_product_serializer = Order_content_serializer(data=single_product, partial=True)
            
            subtotal = subtotal + (product_instance.productPrice * single_product["quantity"])
            
            if single_product_serializer.is_valid():
                single_product_data = single_product_serializer.save()
                single_product["id"] = single_product_data.id
                
                for single_modifier in modifier_list:
                    modifier_details = ProductModifier.objects.filter(modifierPLU=single_modifier['plu'], vendorId=vendor_id).first()

                    modifier_quantity_status = 0
                    modifier_status = 0

                    if single_modifier['status']:
                        modifier_quantity_status = 1

                    if single_modifier['status']:
                        modifier_status = 1
                    
                    modifier_info = {
                        "name": single_modifier['name'],
                        "SKU": single_modifier['plu'],
                        "quantityStatus": modifier_quantity_status,
                        "quantity": single_modifier['quantity'],
                        "unit": "qty",
                        "status": modifier_status,
                        "contentID": single_product_data.pk,
                        "group": single_modifier["group"]
                    }

                    subtotal = subtotal + (modifier_details.modifierPrice * single_modifier['quantity'])
                    
                    if single_modifier['status']:
                        single_modifier_serializer = OrderModifierWriterSerializer(data=modifier_info, partial=True)
                    
                        if single_modifier_serializer.is_valid():
                            single_modifier_serializer.save()
                        
                        else:
                            print("error ", single_product_serializer.errors)
        
        if order.order_status != 1:
            order.order_status = 8

        order.save()

        master_order_instance = coreOrder.objects.filter(pk=order.master_order.pk).first()

        master_order_instance.subtotal = subtotal + master_order_instance.subtotal

        tax_total = 0

        vendor_taxes = Tax.objects.filter(vendorId=vendor_id)

        for tax in vendor_taxes:
            tax_total = tax_total + (master_order_instance.subtotal * (tax.percentage / 100))

        tax_total = round(tax_total, 2)

        master_order_instance.tax = tax_total

        master_order_instance.TotalAmount = master_order_instance.subtotal + tax_total

        master_order_instance.save()

        webSocketPush(
            message = {"id": order.pk, "orderId": order.externalOrderId, "UPDATE": "REMOVE",},
            room_name = f"{str(vendor_id)}-{str(old_status)}",
            username = "CORE",
        )
        
        processStation(
            oldStatus = old_status,
            currentStatus = order.order_status,
            orderId = order.pk,
            station = station_instance,
            vendorId = vendor_id
        )
        
        waiteOrderUpdate(orderid=order.pk, language=language, vendorId=vendor_id)

        allStationWiseRemove(id=order.pk, old=str(old_status), current=str(order.order_status), vendorId=vendor_id)
        allStationWiseSingle(id=order.pk, vendorId=vendor_id)
        allStationWiseCategory(vendorId=vendor_id)
        
        return JsonResponse({
            "id": new_items['orderId'],
            "oldstatus": old_status,
            "current_status": order.order_status
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        print(e)
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def koms_login(request):
    request_json = JSONParser().parse(request)

    try:
        station = Station.objects.filter(
            client_id=request_json.get('username'),
            client_secrete=request_json.get('password')
        ).first()

        station.key = secrets.token_hex(8)
        station.save()
        
        response_data = {
            "token": station.key,
            "stationId": station.pk,
            "stationName": station.station_name,
            "vendorId": station.vendorId.pk,
            "vendorName": station.vendorId.Name,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse(
            {"msg": "not found"}, status=status.HTTP_400_BAD_REQUEST
        )


def notify(type,msg,desc='',stn=[],vendorId=-1):
    print("notification to ",stn)
    order = Order.objects.filter(id=int(msg)).first()
    for i in set(stn):
        webSocketPush(message={
                            "type":int(type),
                            "orderId":int(msg),
                            "description":desc,
                            "status":order.order_status if order else None,
                            "order_type":order.master_order.orderType if order else None
                            }
                      ,room_name=MESSAGE+'-'+str(vendorId)+'-'+str(i),username="CORE")
          
    
@api_view(["GET"])
def makeunique(request,msg_type='',msg='',desc='',stn='',vendorId=3):
    for i in stn.split(','):
        notify(type=msg_type,msg=msg,desc=desc,stn=[i],vendorId=vendorId)
    return Response({"G": "G"})


@api_view(['POST'])
def editContent(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get('language', 'English')

        if not vendor_id:
            return JsonResponse({"message": "Invalid vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)

        except ValueError:
            return JsonResponse({"message": "Invalid vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return JsonResponse({"message": "Vendor does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        data = dict(JSONParser().parse(request))
        
        order = Order.objects.get(pk=data['orderId'], vendorId=vendor_id)

        content = Order_content.objects.get(orderId=order.pk, SKU=data['plu'])

        old_status = content.status

        item = {}
        modifier_list = []

        for modifier_group in data['modifiersGroup']:
            for modifier in modifier_group['modifiers']:
                modifier["group"] = ProductModifierGroup.objects.filter(PLU=modifier_group['plu'], vendorId=vendor_id).first().pk
                
                modifier_list.append(modifier)

        if (content.quantity != data['quantity']) or (content.note != data['note']):
            item["isEdited"]= True 

        item["orderId"] = order.pk
        item["quantity"] = data['quantity']
        item["note"] = data["note"]

        single_product_serializer = Order_content_serializer(instance=content, data=item, partial=True)

        if single_product_serializer.is_valid():
            single_product_data = single_product_serializer.save()

        for single_modifier in modifier_list:
            try:
                modifier_data = {
                    "quantity": single_modifier['quantity'],
                    "quantityStatus": 1 if single_modifier['status'] else 0,
                    "status": 1 if single_modifier['status'] else 0,
                }

                old_modifier_instance = Order_modifer.objects.get(contentID=content.pk, SKU=single_modifier['plu'])

                single_modifier_serializer = OrderModifierWriterSerializer(
                    instance = old_modifier_instance,
                    data = modifier_data,
                    partial = True
                )
                
                if single_modifier_serializer.is_valid():
                    single_modifier_serializer.save()

                    if old_modifier_instance.quantity != single_modifier['quantity']:
                        single_product_data.isEdited == True
                        single_product_data.save()

            except Order_modifer.DoesNotExist:
                modifier_data = {
                    "name": single_modifier['name'],
                    "SKU": single_modifier['plu'],
                    "quantityStatus": 1 if single_modifier['status'] else 0,
                    "quantity": single_modifier['quantity'],
                    "unit": "qty",
                    "status": 1 if single_modifier['status'] else 0,
                    "contentID": content.pk,
                    "group": single_modifier["group"]
                }
                
                single_modifier_serializer = OrderModifierWriterSerializer(data=modifier_data, partial=True)
                
                if single_modifier_serializer.is_valid():
                    single_modifier_serializer.save()

        subtotal = 0

        for content_info in Order_content.objects.filter(orderId=order.pk):
            product_instance = Product.objects.filter(PLU=content_info.SKU, vendorId_id=vendor_id).first()

            subtotal = subtotal + (product_instance.productPrice * content_info.quantity)
            
            for modifier_instance in Order_modifer.objects.filter(contentID=content_info.pk):
                modifierData = ProductModifier.objects.filter(modifierPLU=modifier_instance.SKU, vendorId=vendor_id).first()
                subtotal = subtotal + (modifierData.modifierPrice * modifier_instance.quantity)

        master_order_instance = coreOrder.objects.filter(pk=order.master_order.pk).first()
        master_order_instance.subtotal = subtotal

        tax_total = 0

        taxes = Tax.objects.filter(vendorId=vendor_id)
        
        for tax in taxes:
            tax_total = tax_total + (master_order_instance.subtotal * (tax.percentage / 100))

        tax_total = round(tax_total, 2)

        master_order_instance.tax = tax_total
        master_order_instance.TotalAmount = master_order_instance.subtotal + tax_total
        master_order_instance.save()

        current_status = Order_content.objects.get(pk=content.pk).status
        
        processStation(
            oldStatus = old_status,
            currentStatus = current_status,
            orderId = content.orderId.pk,
            station = content.stationId,
            vendorId = vendor_id
        )
        
        waiteOrderUpdate(orderid=order.pk, language=language, vendorId=vendor_id)
        
        allStationWiseRemove(id=order.pk, old=str(old_status), current=str(current_status), vendorId=vendor_id)
        allStationWiseSingle(id=order.pk, vendorId=vendor_id)
        allStationWiseCategory(vendorId=vendor_id)
        
        return Response({"message": ""})
    
    except Exception as e:
        return Response({"message": str(e)})
