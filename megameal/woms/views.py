from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from woms.models import *
from woms.serializer import *
from static.order_status_const import *
from core.models import Product, ProductAndModifierGroupJoint, ProductModifierAndModifierGroupJoint
from koms.models import Order, Order_content, Order_modifer, Order_tables
from koms.views import webSocketPush, getOrder
from datetime import datetime
import secrets
import socket



def gettable(id, vendorId, language="English"):
    try:
        waiter = Waiter.objects.get(pk=id, vendorId=vendorId)
        
        if waiter.is_waiter_head:
            data = HotelTable.objects.filter(vendorId=vendorId).order_by('tableNumber')

        else:
            data = HotelTable.objects.filter(waiterId=id, vendorId=vendorId).order_by('tableNumber')
        
        result = []

        for table in data:
            table_data = get_table_data(table, language)
            result.append(table_data)
        
        return result
    
    except Exception as e:
        print(e)
        return []


def get_table_data(hotelTable, vendorId, language="English"):
    waiter_name = ""
    floor_name = ""

    if hotelTable:
        if language == "English":
            if hotelTable.waiterId:
                waiter_name = hotelTable.waiterId.name

            floor_name = hotelTable.floor.name

        else:
            if hotelTable.waiterId:
                waiter_name = hotelTable.waiterId.name_locale
                
            floor_name = hotelTable.floor.name_locale
    
    data = { 
        "tableId": hotelTable.pk, 
        "tableNumber": hotelTable.tableNumber,
        "waiterId": hotelTable.waiterId.pk if hotelTable.waiterId else 0,
        "status": hotelTable.status,
        "waiterName": waiter_name,
        "tableCapacity": hotelTable.tableCapacity, 
        "guestCount": hotelTable.guestCount,
        "floorId": hotelTable.floor.pk,
        "floorName": floor_name
    }
    
    try:
        test = Order_tables.objects.filter(tableId_id=hotelTable.pk).values_list("orderId_id",flat=True)

        latest_order = Order.objects.filter(id__in=test,vendorId=vendorId).order_by('-arrival_time').first()

        if latest_order:
            data["order"] = latest_order.externalOrderId
            data["total_amount"] = latest_order.master_order.subtotal

        else:
            data["order"] = 0
            data["total_amount"] = 0.0

    except Order_tables.DoesNotExist:
        print("Table not found")
        data["order"] = 0
        data["total_amount"] = 0.0

    except Order.DoesNotExist:
        print("Order not found")
        data["order"] = 0
        data["total_amount"] = 0.0

    except Exception as e:
        data["order"] = 0
        data["total_amount"] = 0.0
        print(f"Unexpected {e=}, {type(e)=}")

    return data


def filter_tables(waiterId, filter, search, status, waiter, floor, vendorId, language="English"):
    try:
        if waiterId == "POS" or Waiter.objects.get(pk=waiterId, vendorId=vendorId).is_waiter_head:
            data = HotelTable.objects.filter(vendorId=vendorId)
        
        else:
            data = HotelTable.objects.filter(waiterId=waiterId, vendorId=vendorId)

        if filter != 'All':
            data = data.filter(tableCapacity=filter)

        if search != 'All':
            data = data.filter(tableNumber=search)

        if status != 'All':
            data = data.filter(status__icontains=status)

        if waiter != 'All':
            waiter_ids = [i.pk for i in Waiter.objects.filter(name__icontains=waiter, vendorId=vendorId)]
            data = data.filter(waiterId__in=waiter_ids)

        if floor != 'All':
            data = data.filter(floor__id=floor)

        data = data.order_by('tableNumber')
        
        table_data = []
        
        for table in data:
            table_info = get_table_data(hotelTable=table, vendorId=vendorId, language=language)

            table_data.append(table_info)
        
        return table_data
    
    except Exception as e:
        print(e)
        return []


def get_orders_of_waiter(waiter_id, filter, search, vendor_id, language="English"):
    station_wise_data = {}

    waiter_instance = Waiter.objects.filter(pk=waiter_id, vendorId=vendor_id).first()

    if waiter_instance.is_waiter_head == True:
        waiter_tables = HotelTable.objects.filter(vendorId=vendor_id)

    else:
        waiter_tables = HotelTable.objects.filter(waiterId=waiter_id, vendorId=vendor_id)

    table_ids = []
    order_ids = []

    for table in waiter_tables:
        table_ids.append(str(table.pk))
    
    tables_of_order = Order_tables.objects.filter(tableId_id__in=table_ids)

    for instance in tables_of_order:
        order_ids.append(str(instance.orderId.pk))

    date = datetime.today().strftime("20%y-%m-%d")

    orders = Order.objects.filter(id__in=order_ids, arrival_time__contains=date, vendorId=vendor_id)

    if filter == 'All':
        pass

    elif filter == "7":
        orders = orders.filter(isHigh=True)

    else:
        orders = orders.filter(order_status=filter)

    if search != 'All':
        order_ids = []
        table_ids = []

        table_ids = HotelTable.objects.filter(tableNumber=search, vendorId=vendor_id).values_list('pk', flat=True)

        order_ids = Order_tables.objects.filter(tableId__in = table_ids).values_list('orderId', flat=True)

        orders = orders.filter(id__in = order_ids)

    koms_order_ids = orders.values_list('pk', flat=True)
    
    order_content = Order_content.objects.filter(orderId__in = koms_order_ids).order_by("-orderId")
    
    for single_content in order_content:
        order_instance = Order.objects.filter(pk = single_content.orderId.pk, vendorId = vendor_id).first()

        single_order_info = getOrder(ticketId=order_instance.pk, language=language, vendorId=vendor_id)
        
        single_order_info['TotalAmount'] = order_instance.master_order.TotalAmount
        
        station_wise_data[order_instance.externalOrderId] = single_order_info
    
    return station_wise_data



@api_view(["POST"])
def waiter_login(request):
    request_data = JSONParser().parse(request)

    try:
        waiter = Waiter.objects.filter(
            username=request_data.get('username'),
            password=request_data.get('password')
        ).first()

        if not waiter:
            return Response({"message": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        
        waiter.token = secrets.token_hex(8)
        waiter.save()

        local_ips = []

        host_name = socket.gethostname()

        host_ip_info = socket.gethostbyname_ex(host_name)

        for ip in host_ip_info[2]:
            if not ip.startswith("127."):
                local_ips.append(ip)

        external_ip = None

        external_ip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        port = request.META.get("SERVER_PORT")

        try:
            external_ip_socket.connect(('8.8.8.8', 53))

            external_ip = external_ip_socket.getsockname()[0]

        finally:
            external_ip_socket.close()

        if local_ips:
            server_ip = local_ips[0]

        else:
            server_ip = external_ip

        return Response({
            "message": "",
            "id": waiter.pk,
            "username": waiter.username,
            "token": waiter.token,
            "name": waiter.name,
            "email": waiter.email,
            "is_waiter_head": waiter.is_waiter_head,
            "profile_picture": f"http://{server_ip}:{port}{waiter.image.url}",
            "primary_language": waiter.vendorId.primary_language,
            "secondary_language": waiter.vendorId.secondary_language if waiter.vendorId.secondary_language else "",
            "currency": waiter.vendorId.currency,
            "currency_symbol": waiter.vendorId.currency_symbol,
            "vendor_id": waiter.vendorId.pk,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 
@api_view(['GET'])
def get_tables(request):
    waiter_id = request.GET.get("waiterId")
    vendor_id = request.GET.get("vendorId")

    try:
        if (not vendor_id) or (not waiter_id):
            return Response("Invalid Vendor ID or Waiter ID", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
            waiter_id = int(waiter_id)

        except ValueError:
            return JsonResponse({"message": "Invalid Vendor ID or Waiter ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return JsonResponse({"message": "Vendor does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    
        waiter_instance = Waiter.objects.filter(pk=waiter_id, vendorId=vendor_id).first()

        if not waiter_instance:
            return JsonResponse({"message": "Waiter does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        hotel_tables = HotelTable.objects.filter(vendorId=vendor_id)
        
        if waiter_instance.is_waiter_head == False:
            hotel_tables = hotel_tables.filter(waiterId=waiter_id)
        
        table_capacity_set = set()

        for table in hotel_tables:
            table_capacity_set.add(str(table.tableCapacity))
        
        return JsonResponse({"message": "", "tableCapacity": list(table_capacity_set)}, safe=False)
    
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_waiters(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language", "English")

        if not vendor_id:
            return JsonResponse({"message": "Invalid Vendor ID", "waiters": []}, status=status.HTTP_400_BAD_REQUEST)
        
        waiters = Waiter.objects.filter(is_active=True, vendorId=vendor_id)
        
        waiter_list = []

        waiter_name = ""
        
        for waiter in waiters:
            if language == "English":
                waiter_name = waiter.name

            else:
                waiter_name = waiter.name_locale

            waiter_info = {
                "id": waiter.pk,
                "name": waiter_name,
                "is_waiter_head": waiter.is_waiter_head
            }

            waiter_list.append(waiter_info)

        return JsonResponse({"message": "", "waiters": waiter_list}, status=status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse({"message": str(e), "waiters": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
 
@api_view(["post"])
def assign_waiter_to_table(request):
    requestJson = JSONParser().parse(request)

    table_id = requestJson.get('tableId')
    waiter_id = requestJson.get('waiterId')
    vendor_id = request.GET.get("vendorId")
    language = request.GET.get("language", "English")

    if not all((table_id, waiter_id, vendor_id)):
        return Response("Invalid Table ID, Waiter ID or Vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        table_id = int(table_id)
        waiter_id = int(waiter_id)
        vendor_id = int(vendor_id)
        
    except ValueError:
        return Response("Invalid Table ID, Waiter ID or Vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    table_instance = HotelTable.objects.filter(pk=table_id, vendorId=vendor_id).first()
    waiter_instance = Waiter.objects.filter(pk=waiter_id, vendorId=vendor_id).first()
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not all((vendor_instance, table_instance, waiter_instance)):
        return Response("Table, Waiter or Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    try:
        if table_instance.waiterId != None:
            result = get_table_data(hotelTable=table_instance, language=language, vendorId=vendor_id)

            old_waiter_id = str(table_instance.waiterId.pk)
            
            webSocketPush(
                message = {"result": result, "UPDATE": "REMOVE",},
                room_name = f"WOMS{old_waiter_id}------English-{str(vendor_id)}",
                username = "CORE",
            )#remove table from old waiter
            
            if vendor_instance.secondary_language and (language != "English"):
                webSocketPush(
                    message = {"result": result, "UPDATE": "REMOVE",},
                    room_name = f"WOMS{old_waiter_id}------{language}-{str(vendor_id)}",
                    username = "CORE",
                )
        
        table_instance.waiterId = waiter_instance
        table_instance.save()

        table_data = get_table_data(hotelTable=table_instance, language=language, vendorId=vendor_id)

        webSocketPush(
            message = {"result": table_data, "UPDATE": "UPDATE"},
            room_name = f"WOMS{str(waiter_id)}------English-{str(vendor_id)}",
            username = "CORE",
        )
        
        webSocketPush(
            message = {"result": table_data, "UPDATE": "UPDATE"},
            room_name = f"WOMSPOS------English-{str(vendor_id)}",
            username = "CORE",
        )
        
        if vendor_instance.secondary_language and (language != "English"):
            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMS{str(waiter_id)}------{language}-{str(vendor_id)}",
                username = "CORE",
            )
            
            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMSPOS------{language}-{str(vendor_id)}",
                username = "CORE",
            )
        
        waiter_heads = Waiter.objects.filter(is_waiter_head=True, vendorId=vendor_id)
        
        for waiter_head in waiter_heads:
            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMS{str(waiter_head.pk)}------English-{str(vendor_id)}",
                username = "CORE",
            )
            
            if vendor_instance.secondary_language and (language != "English"):
                webSocketPush(
                    message = {"result": table_data, "UPDATE": "UPDATE"},
                    room_name = f"WOMS{str(waiter_head.pk)}------{language}-{str(vendor_id)}",
                    username = "CORE",
                )
        
        return JsonResponse(table_data, safe=False)
    
    except Exception as e:
        print(str(e))
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST']) 
def update_table_status(request):
    try:
        requestJson = JSONParser().parse(request)

        table_id = requestJson.get('id')
        table_status = requestJson.get('tableStatus')
        guest_count = requestJson.get('guestCount')
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language", "English")

        if not all((table_id, vendor_id)):
            return Response("Invalid Table ID or Vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            table_id = int(table_id)
            vendor_id = int(vendor_id)
            
        except ValueError:
            return Response("Invalid Table ID or Vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        table_instance = HotelTable.objects.filter(pk=table_id, vendorId=vendor_id).first()
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not all((vendor_instance, table_instance)):
            return Response("Table or Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
        
        if requestJson.get('tableStatus') == None:
            table_status = table_instance.status
        
        if requestJson.get('guestCount') == None:
            guest_count = table_instance.guestCount
        
        table_instance.status = table_status
        table_instance.guestCount = guest_count

        table_instance.save()
        
        table_data = get_table_data(hotelTable=table_instance, language=language, vendorId=vendor_id)

        waiter_id = 0

        if table_instance.waiterId:
            waiter_id = table_instance.waiterId.pk
        
        webSocketPush(
            message = {"result": table_data, "UPDATE": "UPDATE"},
            room_name = f"WOMS{str(waiter_id)}------English-{str(vendor_id)}",
            username = "CORE",
        )

        webSocketPush(
            message = {"result": table_data, "UPDATE": "UPDATE"},
            room_name = f"WOMSPOS------English-{str(vendor_id)}",
            username = "CORE",
        )
        
        if vendor_instance.secondary_language and (language != "English"):
            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMS{str(waiter_id)}------{language}-{str(vendor_id)}",
                username = "CORE",
            )

            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMSPOS------{language}-{str(vendor_id)}",
                username = "CORE",
            )
        
        waiter_heads = Waiter.objects.filter(is_waiter_head=True, vendorId=vendor_id)
        
        for waiter_head in waiter_heads:
            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMS{str(waiter_head.pk)}------English-{str(vendor_id)}",
                username = "CORE",
            )
            
            if vendor_instance.secondary_language and (language != "English"):
                webSocketPush(
                    message = {"result": table_data, "UPDATE": "UPDATE"},
                    room_name = f"WOMS{str(waiter_head.pk)}------{language}-{str(vendor_id)}",
                    username = "CORE",
                )

        return JsonResponse(table_data, safe=False)
    
    except Exception as e:
        print(e)
        return JsonResponse({"msg": e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_modifiers_of_product(request):
    try:
        content_id = request.GET.get("content")
        vendor_id = request.GET.get("vendor")
        language = request.GET.get("language", "English")

        if (not content_id) or (not vendor_id):
            return JsonResponse({"message": "Invalid Content ID or Vendor ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vendor_id = int(vendor_id)
            content_id = int(content_id)

        except ValueError:
            return JsonResponse({"message": "Invalid Content ID or Vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
        
        order_content = Order_content.objects.filter(pk=content_id, orderId__vendorId=vendor_id).first()

        if not order_content:
            return JsonResponse({"message": "Content does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(PLU=order_content.SKU, vendorId=vendor_id).first()

        modifier_plu_list = []
        count = 0

        order_modifiers = Order_modifer.objects.filter(contentID=order_content.pk, status=1)

        for instance in order_modifiers:
            modifier_plu_list.append(instance.SKU)

            if instance.quantity > 0:
                count = count + 1
        
        modifier_group_list = []

        product_and_modifier_group_joint = ProductAndModifierGroupJoint.objects.filter(product=product.pk, vendorId=vendor_id)

        for modifier_group_info in product_and_modifier_group_joint:
            modifier_list = []

            modifier_and_modifier_group_joint = ProductModifierAndModifierGroupJoint.objects.filter(
                modifierGroup = modifier_group_info.modifierGroup.pk,
                modifierGroup__isDeleted = False,
                vendor = vendor_id
            )
            
            for modifier_info in modifier_and_modifier_group_joint:
                if modifier_info.modifier.modifierPLU in modifier_plu_list:
                    quantity = Order_modifer.objects.get(
                        contentID=order_content.pk,
                        SKU=modifier_info.modifier.modifierPLU
                    ).quantity
                    
                    status_of_modifier = True
                
                else:
                    quantity = 0

                    status_of_modifier = False
                
                modifier_image = modifier_info.modifier.modifierImg

                if not modifier_image:
                    modifier_image = "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg"
                
                modifier_name = modifier_info.modifier.modifierName

                if language != "English":
                    modifier_name = modifier_info.modifier.modifierName_locale
                
                modifier_list.append({
                    "modifierId": modifier_info.modifier.pk,
                    "name": modifier_name,
                    "plu": modifier_info.modifier.modifierPLU,
                    "image": modifier_image,
                    "cost": modifier_info.modifier.modifierPrice,
                    "quantity": quantity,
                    "status": status_of_modifier,
                })

            modifier_group_name = modifier_group_info.modifierGroup.name

            if language != "English":
                modifier_group_name = modifier_group_info.modifierGroup.name_locale
            
            modifier_group_list.append({
                "name": modifier_group_name,
                "plu": modifier_group_info.modifierGroup.PLU,
                "min": modifier_group_info.modifierGroup.min,
                "max": modifier_group_info.modifierGroup.max,
                "type": modifier_group_info.modifierGroup.modGrptype,
                "count": count,
                "modifiers": modifier_list
            })

        product_name = product.productName
                    
        if language != "English":
            product_name = product.productName_locale

        product_info = {
            "productId": product.pk,
            "text": product_name,
            "plu": product.PLU,
            "quantity": order_content.quantity,
            "modifiersGroup": modifier_group_list,
            "note": order_content.note if order_content.note else ""
        }

        return JsonResponse(product_info)
    
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
