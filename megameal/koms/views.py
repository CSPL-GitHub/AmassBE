from django.db.models import Count, Sum, Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from django.http.response import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta, time
from core.models import Product, ProductImage, Platform, ProductModifier, Tax, ProductModifierGroup, ProductCategory, Vendor
from woms.models import HotelTable, Waiter
from koms.models import Order, Order_content, Order_modifer, Order_tables, Station, Staff, Content_assign
from order.models import Order as coreOrder, OrderPayment, Address, LoyaltyProgramSettings, LoyaltyPointsRedeemHistory, SplitOrderItem
from pos.language import master_order_status_number
from core.utils import API_Messages
from koms.serializers.order_serializer import Order_serializer, OrderSerializerWriterSerializer
from koms.serializers.staff_serializer import StaffReaderSerializer
from koms.serializers.order_content_serializer import Order_content_serializer
from koms.serializers.order_modifer_serializer import OrderModifierWriterSerializer
from koms.serializers.content_assign_serializer import Content_assign_serializer
from pos.language import (
    order_has_arrived_locale, payment_type_english, language_localization, local_timezone,
    koms_order_status_number, order_type_number,
)
from inventory.utils import sync_order_content_with_inventory
import secrets



def sort_koms_orders(orders):
    return not orders[1]["isHigh"]


def percent(a, b):
    try:
        return round(((a / b) * 100), 2)
    
    except:
        return 0


def dictionary_to_list(dictionary):
    result = []

    for key, value in dictionary.items():
        result.append({"name": str(key).capitalize(), "value": value})

    return result


def webSocketPush(message, room_name, username):
    print("webSocketPush Room Name : ",room_name)

    channel_layer = get_channel_layer()

    data = async_to_sync(channel_layer.group_send)(
        "chat_%s" % room_name,
        {"type": "chat_message", "message": message, "username": username},
    )


def notify(type, msg, desc='', stn=[], vendorId=0):
    print("notification sent to ", stn)

    order = Order.objects.filter(id = int(msg)).first()

    for station in set(stn):
        webSocketPush(
            message = {
                "type": int(type),
                "orderId": int(msg),
                "description": desc,
                "status": order.order_status if order else None,
                "order_type": order.master_order.orderType if order else None
            },
            room_name = f"MESSAGE-{str(vendorId)}-{str(station)}",
            username = "CORE"
        )


def getOrder(ticketId, vendorId, language="English"):
    koms_order = Order.objects.filter(pk = ticketId, vendorId = vendorId).first()

    koms_order_data = {}

    koms_order_data["id"] = koms_order.pk
    koms_order_data["orderId"] = koms_order.externalOrderId
    koms_order_data["master_order_id"] = koms_order.master_order.pk
    koms_order_data["orderType"] = koms_order.order_type

    pickup_time = koms_order.pickupTime

    if pickup_time == koms_order.arrival_time:
        pickup_time = pickup_time + timedelta(minutes=30)

    if koms_order.order_note:
        order_note = koms_order.order_note

    else:
        if language == "English":
            order_note = "None"

        else:
            order_note = language_localization["None"]

    waiters = ""
    waiter_names = []

    if koms_order.server:
        waiter_ids_string = koms_order.server

        waiter_id_list = waiter_ids_string.split(',')

        if language == "English":
            for waiter_id in waiter_id_list:
                waiter_instance = Waiter.objects.filter(pk = int(waiter_id), vendorId = vendorId).first()
                
                waiter_names.append(waiter_instance.name)

        else:
            for waiter_id in waiter_id_list:
                waiter_instance = Waiter.objects.filter(pk = int(waiter_id), vendorId = vendorId).first()

                waiter_names.append(waiter_instance.name_locale)

        waiters = waiters = ', '.join(waiter_names)

    koms_order_data["pickupTime"] =  pickup_time.astimezone(local_timezone).strftime("%Y-%m-%dT%H:%M:%S")
    koms_order_data["arrivalTime"] = koms_order.arrival_time.astimezone(local_timezone).strftime("%Y-%m-%dT%H:%M:%S")
    koms_order_data["order_datetime"] = koms_order.master_order.OrderDate.astimezone(local_timezone).strftime("%Y-%m-%dT%H:%M:%S")
    koms_order_data["is_edited"] = koms_order.is_edited
    koms_order_data["edited_at"] = koms_order.edited_at.astimezone(local_timezone).strftime("%Y-%m-%dT%H:%M:%S")
    koms_order_data["deliveryIsAsap"] = koms_order.deliveryIsAsap
    koms_order_data["note"] = order_note
    koms_order_data["remake"] = False
    koms_order_data["customerName"] = ""
    koms_order_data["status"] = koms_order.order_status
    koms_order_data["guest"] = koms_order.guest
    koms_order_data["server"] = waiters

    try:
        order_tables = Order_tables.objects.filter(orderId = koms_order.pk)

        table_number_list = " "

        table_id_list = []

        for orderTable in order_tables:
            table_number_list = table_number_list + str(orderTable.tableId.tableNumber) + ","
            table_id_list.append(orderTable.tableId.pk)

        koms_order_data["tableIds"] = table_id_list
        koms_order_data["tableNo"] = table_number_list[:-1]

    except Order_tables.DoesNotExist:
        koms_order_data["tableIds"] = []
        koms_order_data["tableNo"] = ""

    koms_order_data["tableId"] = 1 #HotelTable.objects.filter(tableNumber=singleOrder.tableNo).first().pk # Remove this line
    koms_order_data["isHigh"] = koms_order.isHigh

    order_content = Order_content.objects.filter(orderId=koms_order.pk).order_by('-pk')

    items = {}

    for single_content in order_content:
        single_content_data = {}

        product_name = ""
        station_name = ""

        product_instance = Product.objects.filter(PLU=single_content.SKU, vendorId=vendorId).first()
        
        if language == "English":
            product_name = product_instance.productName
            station_name = single_content.stationId.station_name

        else:
            product_name = product_instance.productName_locale
            station_name = single_content.stationId.station_name_locale

        single_content_data["id"] = single_content.pk
        single_content_data["plu"] = single_content.SKU
        single_content_data["name"] = product_name
        single_content_data["quantity"] = single_content.quantity
        single_content_data["status"] = single_content.status
        single_content_data["stationId"] = single_content.stationId.pk
        single_content_data["stationName"] = station_name
        single_content_data["isRecall"] = single_content.isrecall
        single_content_data["isEdited"] = single_content.isEdited

        product_image = ""
        product_price = 0.0
        recipe_video_url = ""
        
        if product_instance:
            product_price = product_instance.productPrice
            recipe_video_url = product_instance.recipe_video_url if product_instance.recipe_video_url else ""

            product_image_instance = ProductImage.objects.filter(product=product_instance.pk).first()

            if product_image_instance:
                product_image = product_image_instance.url

        single_content_data["image"] = product_image
        single_content_data["price"] = product_price
        single_content_data["recipe_video_url"] = recipe_video_url
        
        try:
            content_assign_instance = Content_assign.objects.get(contentID = single_content.pk)

            single_content_data["chefId"] = content_assign_instance.staffId.pk
            single_content_data["assignedChef"] = content_assign_instance.staffId.last_name
        
        except Content_assign.DoesNotExist:
            single_content_data["chefId"] = 0

        single_content_data["quantityStatus"] = single_content.quantityStatus
        single_content_data["itemRemark"] = single_content.note if single_content.note else ""

        content_modifiers = Order_modifer.objects.filter(contentID = single_content.pk, status = "1")

        modifier_list = []

        for single_modifier in content_modifiers:
            if single_modifier.quantity > 0 :
                single_modifier_data = {}

                modifier_name = ""

                modifier_instance = ProductModifier.objects.filter(modifierPLU = single_modifier.SKU, vendorId = vendorId).first()
                
                if language == "English":
                    modifier_name = modifier_instance.modifierName

                else:
                    modifier_name = modifier_instance.modifierName_locale

                single_modifier_data["id"] = single_modifier.pk
                single_modifier_data["plu"] = single_modifier.SKU
                single_modifier_data["name"] = modifier_name
                single_modifier_data["quantityStatus"] = single_modifier.quantityStatus
                single_modifier_data["quantity"] = single_modifier.quantity

                try:
                    single_modifier_data["price"] = modifier_instance.modifierPrice
                
                except:
                    single_modifier_data["price"] = 0

                modifier_list.append(single_modifier_data)

        single_content_data["subItems"] = modifier_list

        if single_content.categoryName in items.keys():
            alreayList = items[single_content.categoryName]
            alreayList.append(single_content_data)
        
        else:
            items[single_content.categoryName] = [single_content_data]

    koms_order_data["items"] = items

    return koms_order_data


def allStationData(vendorId):
    date = datetime.today().strftime("%Y-%m-%d")

    koms_orders = Order.objects.filter(arrival_time__date = date, vendorId = vendorId)

    station_wise_data = {}

    for order in koms_orders:
        single_order_data = getOrder(ticketId = order.pk, vendorId = vendorId)

        if order.order_status in station_wise_data:
            temp = station_wise_data[order.order_status]
            temp[order.externalOrderId] = single_order_data

        else:
            station_wise_data[order.order_status] = {order.externalOrderId: single_order_data}

    for station in station_wise_data:
        sorted_data = []

        for key, value in station_wise_data[station].items():
            sorted_data.append((key, value))

        sorted_data.sort(key=sort_koms_orders)
        
        station_wise_data[station] = dict(sorted_data)

    return station_wise_data


def stationdata(id, vendorId):
    station_wise_data = {}

    date = datetime.today().strftime("%Y-%m-%d")

    koms_orders = Order.objects.filter(arrival_time__date = date, vendorId = vendorId)

    for single_order in koms_orders:
        external_order_id = single_order.externalOrderId

        order_content = Order_content.objects.filter(stationId = id, orderId = single_order)

        total_item_count = order_content.count()

        if order_content:
            order_data = getOrder(ticketId = single_order.pk, vendorId = vendorId)

            sorted_items = []

            for key, value in order_data['items'].items():
                if value[0]["stationId"] != int(id):
                    sorted_items.append((key, value))

            order_data['items'] = dict(sorted_items)

            processing_order_status_number = str(koms_order_status_number["Processing"])
            cancelled_order_status_number = str(koms_order_status_number["Canceled"])
            ready_order_status_number = str(koms_order_status_number["Ready"])
            onhold_order_status_number = str(koms_order_status_number["Onhold"])

            if order_content.filter(status = processing_order_status_number).exists():
                if processing_order_status_number in station_wise_data:
                    temp = station_wise_data[processing_order_status_number]

                    temp[external_order_id] = order_data 
                
                else:
                    station_wise_data[processing_order_status_number] = {external_order_id: order_data}

            elif total_item_count == order_content.filter(status = cancelled_order_status_number).count():
                if cancelled_order_status_number in station_wise_data:
                    temp = station_wise_data[cancelled_order_status_number]

                    temp[external_order_id] = order_data 

                else:
                    station_wise_data[cancelled_order_status_number] = {external_order_id: order_data}

            elif total_item_count == order_content.filter(status__in = (ready_order_status_number, cancelled_order_status_number)).count():
                if ready_order_status_number in station_wise_data:
                    temp = station_wise_data[ready_order_status_number]

                    temp[external_order_id] = order_data

                else:
                    station_wise_data[ready_order_status_number] = {external_order_id: order_data}

            elif order_content.filter(status = onhold_order_status_number).exists():
                if onhold_order_status_number in station_wise_data:
                    temp = station_wise_data[onhold_order_status_number]

                    temp[external_order_id] = order_data

                else:
                    station_wise_data[onhold_order_status_number] = {external_order_id: order_data}

            else:
                if order_content.first().status in station_wise_data:
                    temp = station_wise_data[order_content.first().status]

                    temp[external_order_id] = order_data
                
                else:
                    station_wise_data[order_content.first().status] = {external_order_id: order_data}

    for station in station_wise_data:
        sorted_data = []

        for key, value in station_wise_data[station].items():
            sorted_data.append((key, value))

        sorted_data.sort(key = sort_koms_orders)
        
        station_wise_data[station] = dict(sorted_data)

    return station_wise_data


def processStation(oldStatus, currentStatus, orderId, station, vendorId):
    single_order = Order.objects.get(pk = orderId)
    
    webSocketPush(
        message = {"oldStatus": oldStatus,"newStatus": currentStatus,"id": orderId,"orderId": single_order.externalOrderId,"UPDATE": "REMOVE"},
        room_name = f"STATION{str(station.pk)}",
        username = "CORE"
    )

    for station in Station.objects.filter(vendorId = vendorId):
        order_content = Order_content.objects.filter(stationId = station, orderId = single_order)

        if order_content:
            order_content_count = order_content.count()

            order_data = getOrder(ticketId = single_order.pk, vendorId = vendorId)

            sorted_data = {}

            for item_key, item_value in order_data['items'].items():
                if item_value[0]["stationId"] != int(station.pk):
                    sorted_data[item_key] = item_value
            
            order_data['items'] = sorted_data

            if order_content.filter(status = str(koms_order_status_number["Processing"])).exists():
                order_data['status'] = koms_order_status_number["Processing"]

            elif order_content_count == order_content.filter(status = str(koms_order_status_number["Canceled"])).count():
                order_data['status'] = koms_order_status_number["Canceled"]

            elif order_content_count == order_content.filter(status__in = (str(koms_order_status_number["Ready"]), str(koms_order_status_number["Canceled"]))).count():
                order_data['status'] = koms_order_status_number["Ready"]

            elif order_content.filter(status = str(koms_order_status_number["Onhold"])).exists():
                order_data['status'] = koms_order_status_number["Onhold"]

            webSocketPush(message = order_data, room_name = f"STATION{str(station.pk)}", username = "CORE")
            
            if int(currentStatus) == koms_order_status_number["Assign"]:
                notify(
                    type = currentStatus,
                    msg = single_order.pk,
                    desc = f"Order No {single_order.externalOrderId} is arrived",
                    stn = [station.pk],
                    vendorId = vendorId
                )


def stationQueueCount(vendorId):
    try:
        date = datetime.today().strftime("%Y-%m-%d")

        all_orders = Order.objects.filter(arrival_time__contains = date, vendorId = vendorId).values_list("id")

        stations = Station.objects.filter(isStation = True, vendorId = vendorId)

        data = {}

        for station in stations:
            station_details = {}

            for key, value in koms_order_status_number.items():
                order_content = Order_content.objects.filter(orderId__in = all_orders, stationId = station.pk, status = value)

                station_details[key] = len(order_content)

                data[station.station_name] = station_details

        return data
    
    except Exception as e:
        print(e)


def stationCategoryWise(id, vendorId):
    result = {}

    try:
        date = datetime.today().strftime("%Y-%m-%d")

        exclude_koms_order_status = (
            koms_order_status_number["Pending"],
            koms_order_status_number["Canceled"],
            koms_order_status_number["Close"],
        )

        all_orders = Order.objects.filter(arrival_time__date = date, vendorId = vendorId)\
        .exclude(order_status__in = exclude_koms_order_status).values_list("pk")
        
        filtered_order_content = Order_content.objects.filter(orderId__in = all_orders, stationId = id)\
        .exclude(status__in = (str(koms_order_status_number["Pending"]), str(koms_order_status_number["Canceled"]), str(koms_order_status_number["Close"])))
        
        order_content = (filtered_order_content.values("categoryName", "name").annotate(count=Count("name"), qty=Sum("quantity")))

        for single_content in order_content:
            if single_content["categoryName"] in result:
                content_list = result[single_content["categoryName"]]

                content_list.append(single_content)

                result[single_content["categoryName"]] = content_list

            else:
                result[single_content["categoryName"]] = [single_content]
    
    except Exception as e:
        print(e)

    return result


def CategoryWise(vendorId):
    result = {}

    try:
        date = datetime.today().strftime("%Y-%m-%d")

        exclude_koms_order_status = (
            koms_order_status_number["Pending"],
            koms_order_status_number["Canceled"],
            koms_order_status_number["Close"],
        )
        
        all_orders = Order.objects.filter(arrival_time__date = date, vendorId = vendorId)\
        .exclude(order_status__in = exclude_koms_order_status).values_list("pk")
        
        filtered_order_content = Order_content.objects.filter(orderId__in = all_orders)\
        .exclude(status__in = (str(koms_order_status_number["Pending"]), str(koms_order_status_number["Canceled"]), str(koms_order_status_number["Close"])))
        
        order_content = (filtered_order_content.values("categoryName", "name").annotate(count=Count("name"), qty=Sum("quantity")))

        for sigle_content in order_content:
            result[sigle_content["categoryName"]] = [sigle_content]

    except Exception as e:
        print(e)

    return result


def allStationWiseCategory(vendorId):
    stations = Station.objects.filter(vendorId=vendorId)

    for station in stations:
        webSocketPush(
            message = stationCategoryWise(id = station.pk, vendorId = vendorId),
            room_name = f"STATIONSIDEBAR{str(station.pk)}",
            username = "CORE"
        )

    webSocketPush(message = CategoryWise(vendorId = vendorId), room_name = "STATIONSIDEBAR", username = "CORE")
    
    return


def statuscount(vendorId):
    date = datetime.today().strftime("%Y-%m-%d")

    result = {}

    for key, value in koms_order_status_number.items():
        result[key] = Order.objects.filter(
            order_status = value, arrival_time__contains = date, vendorId = vendorId
        ).count()
    
    return result


def waiteOrderUpdate(orderid, vendorId, language="English"):
    try:
        data = getOrder(ticketId=orderid, language="English", vendorId=vendorId)

        listOrder = Order_tables.objects.filter(orderId_id=orderid)

        waiters = []

        master_order = coreOrder.objects.filter(Q(externalOrderId=str(data.get('orderId'))) | Q(pk=str(data.get('orderId')))).first()

        payment_type = OrderPayment.objects.filter(orderId=master_order.pk,masterPaymentId=None).last()
        
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
            "mode": payment_mode,
            "split_payments": [],
            "splitType": payment_type.splitType
        }
        
        split_payments_list = []

        core_orders = coreOrder.objects.filter(masterOrder = master_order.pk)
        
        for split_order in core_orders:
            split_payment = OrderPayment.objects.filter(orderId=split_order.pk).first()
            splitItems = []
            for split_item in SplitOrderItem.objects.filter(order_id=split_order.pk):
                order_content_modifer = []
                for mod in Order_modifer.objects.filter(contentID=split_item.order_content_id.pk):
                    modifier_instance = ProductModifier.objects.filter(modifierPLU = mod.SKU, vendorId = vendorId).first()
                    order_content_modifer.append({
                                    "modifer_id":mod.pk,
                                    "modifer_name":mod.name,
                                    "modifer_quantity":mod.quantity,
                                    "modifer_price":modifier_instance.modifierPrice or 0,
                                    "order_content_id": split_item.order_content_id.pk,
                                })
                product_instance = Product.objects.filter(PLU=split_item.order_content_id.plu, vendorId_id=vendorId).first()
                images = [str(instance.url) for instance in ProductImage.objects.filter(product=product_instance.pk, vendorId=vendorId) if instance is not None]
                splitItems.append(
                        {
                            "order_content_id": split_item.order_content_id.pk,
                            "order_content_name": split_item.order_content_id.name,
                            "order_content_quantity": split_item.order_content_qty,
                            "order_content_price": product_instance.productPrice or 1,
                            "order_content_images": images[0] if len(images)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
                            "order_content_modifer": order_content_modifer,
                        }  
                    )
            split_payments_list.append({
                "paymentId": split_payment.pk,
                "paymentBy": f"{split_order.customerId.FirstName or ''} {split_order.customerId.LastName or ''}",
                "customer_name": f"{split_order.customerId.FirstName or ''} {split_order.customerId.LastName or ''}",
                "customer_mobile": split_order.customerId.Phone_Number,
                "customer_email": split_order.customerId.Email if split_order.customerId.Email else "",
                "paymentKey": split_payment.paymentKey,
                "amount_paid": split_payment.paid,
                "paymentType": split_payment.type,
                "paymentSplitPer": (split_payment.paid/master_order.TotalAmount)*100,
                "paymentStatus": split_payment.status,
                "amount_subtotal": split_order.subtotal,
                "amount_tax": split_order.tax,
                "status": split_payment.status,
                "platform": split_payment.platform,
                "mode": payment_type_english[split_payment.type] if language == "English" else language_localization[payment_type_english[split_payment.type]],
                "splitType": payment_type.splitType,
                "splitItems": splitItems,
                }
            )
        
        payment_details["split_payments"] = split_payments_list
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
            "name": f"{master_order.customerId.FirstName or ''} {master_order.customerId.LastName or ''}",
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

        if data['orderType'] == order_type_number["Dinein"]:
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
        print(str(e))


def createOrderInKomsAndWoms(orderJson):
    try:
        vendor_id = orderJson.get("vendorId")

        order_data = orderJson

        order_status = koms_order_status_number["Assign"]

        is_koms_active = Platform.objects.filter(Name = "KOMS", VendorId = vendor_id).first().isActive

        if is_koms_active == True:
            order_status = koms_order_status_number["Pending"]

        is_high = order_data["isHigh"]
        
        if order_data.get('isHigh') == None:
            is_high = False

        order_data["externalOrderId"] = order_data["orderId"]
        order_data["master_order"] = order_data["master_id"]
        order_data["order_status"] = order_status
        order_data["status"] = 1 # pending order
        order_data["order_type"] = order_data["orderType"]
        order_data["arrival_time"] = order_data["arrivalTime"]
        order_data["order_note"] = order_data["note"]
        order_data["isHigh"] = is_high
        
        tablesData = []

        if order_data["tableNo"]:
            tablesData = order_data["tableNo"]
        
        guestCount = 0
        
        for guest in order_data["tableNo"]:
            guestCount = guestCount + guest.get('guestCount', 0)

        order_data["guest"] = guestCount
        order_data["tableNo"] = ''
        order_data["vendorId"] = vendor_id

        print("koms_order_data \n", order_data)

        order_serializers = OrderSerializerWriterSerializer(data = order_data, partial = True)

        if order_serializers.is_valid():
            order_save_data = order_serializers.save()
            order_data["id"] = order_save_data.id

            try:
                for table in tablesData:
                    Order_tables(orderId_id = order_data["id"], tableId_id = table["tableId"]).save()

            except Exception as err:
                print(str(err))
            
        else:
            print("order error", order_serializers._errors)

            return  {API_Messages.STATUS: API_Messages.ERROR, API_Messages.RESPONSE: order_serializers.errors}

        for key, value in order_data["items"].items():
            for singleProduct in value:
                singleProduct["orderId"] = order_save_data.id
                singleProduct["quantityStatus"] = 1  # quantityStatus
                singleProduct["stationId"] = singleProduct["tag"]
                singleProduct["stationName"] = None
                
                category = ProductCategory.objects.filter(categoryName = key, vendorId = vendor_id).first()
                
                if category and (category.categoryStation != None):
                    singleProduct["stationId"] = category.categoryStation.pk
                    singleProduct["stationName"] = category.categoryStation.station_name

                order_status = koms_order_status_number["Assign"]

                if is_koms_active == True:
                    order_status = koms_order_status_number["Pending"]

                is_high = order_data["isHigh"]
                
                if order_data.get('isHigh') == None:
                    is_high = False

                singleProduct["chefId"] = 0
                singleProduct["note"] = singleProduct["itemRemark"]
                singleProduct["SKU"] = singleProduct["plu"]
                singleProduct["status"] = str(order_status)
                singleProduct["categoryName"] = key
                
                single_product_serializer = Order_content_serializer(data=singleProduct, partial=True)

                if single_product_serializer.is_valid():
                    single_product_data = single_product_serializer.save()
                    singleProduct["id"] = single_product_data.id
                    
                    for singleModifier in singleProduct["subItems"]:
                        singleModifier["contentID"] = single_product_data.id
                        singleModifier["quantityStatus"] = 1  # original

                        if "itemRemark" in singleModifier.keys():
                            singleModifier["note"] = singleModifier["itemRemark"]

                        singleModifier["SKU"] = singleModifier["plu"]
                        singleModifier["status"] = "1" if singleModifier.get("status") else "0"
                        singleModifier["quantity"] = singleModifier["quantity"] if 'quantity' in singleModifier.keys() else 1

                        single_modifier_serializer = OrderModifierWriterSerializer(data = singleModifier, partial = True)
                        
                        if single_modifier_serializer.is_valid():
                            single_mod_data = single_modifier_serializer.save()
                            singleModifier["id"] = single_mod_data.id
                            print('modifier saved')

                        else:
                            print("invalid modifier", single_modifier_serializer.errors)
                else:
                    print(single_product_serializer.error_messages)
                    print(single_product_serializer._errors)

        webSocketPush(
            message = stationQueueCount(vendorId = vendor_id),
            room_name = f"WHEELSTATS{str(vendor_id)}",
            username = "CORE"
        )

        webSocketPush(
            message = statuscount(vendorId = vendor_id),
            room_name = f"STATUSCOUNT{str(vendor_id)}",
            username = "CORE"
        )
        
        try:
            order_tables = Order_tables.objects.filter(orderId_id = order_save_data.id)

            table_number_list = []

            for item in order_tables:
                table_number_list.append(str(item.tableId.tableNumber))

            table_number_list = ', '.join(table_number_list) 
        
        except Order_tables.DoesNotExist:
            print("Order table not found")
            table_number_list = ""
        
        wheelman_list = []

        for station in Station.objects.filter(isStation=False, vendorId=vendor_id):
            wheelman_list.append(station.pk)

        if is_koms_active:
            webSocketPush(
                message = order_data,
                room_name = f"{str(vendor_id)}-{koms_order_status_number['Pending']}",
                username = "CORE"
            )
            
            notify(
                type = 1,
                msg = order_save_data.id,
                desc = f"Order No {order_save_data.master_order.pk} on Table No {table_number_list} is arrived",
                stn = [4],
                vendorId = vendor_id
            )
        
        else :
            station_list = []

            order_content = Order_content.objects.filter(orderId = order_save_data.id)

            for instance in order_content:
                station_list.append(instance.stationId.pk)
            
            allStationWiseSingle(id = order_save_data.id, vendorId = vendor_id)
            
            notify(
                type = 1,
                msg = order_save_data.id,
                desc = f"Order No {order_save_data.master_order.pk} is arrived",
                stn = station_list,
                vendorId = vendor_id
            )
        
        language = order_data.get("language", "English")

        if language == "English":
            notify(
                type = 1,
                msg = order_save_data.id,
                desc = f"Order No {order_save_data.master_order.pk} is arrived",
                stn = ['POS'],
                vendorId = vendor_id
            )
        
        else:
            notify(
                type = 1,
                msg = order_save_data.id,
                desc = order_has_arrived_locale(order_save_data.master_order.pk),
                stn = ['POS'],
                vendorId = vendor_id
            )
            
        waiteOrderUpdate(orderid = order_save_data.id, language = language, vendorId = vendor_id)

        allStationWiseCategory(vendorId = vendor_id)
        
        invnetory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

        if invnetory_platform:
            sync_order_content_with_inventory(order_data["master_id"], vendor_id)
            
        return {API_Messages.STATUS: API_Messages.SUCCESSFUL, "id": order_save_data.id, "wheelman": wheelman_list}
    
    except Exception as e:
        print(e)
        return {API_Messages.STATUS: API_Messages.ERROR, API_Messages.RESPONSE: f"{str(e)}"}


def updateCoreOrder(order):
    try:
        koms_order_status = order.order_status

        if koms_order_status in (
            koms_order_status_number['Ready'], koms_order_status_number['Canceled'], koms_order_status_number['Close']
        ):
            vendor_id = order.vendorId_id

            core_order_status = master_order_status_number["Canceled"]

            if koms_order_status == koms_order_status_number['Ready']:
                core_order_status = master_order_status_number["Prepared"]

            if koms_order_status == koms_order_status_number['Close']:
                core_order_status = master_order_status_number["Completed"]

            order_data = getOrder(ticketId = order.pk, vendorId = vendor_id)
            
            order_id = order_data['orderId']

            order = coreOrder.objects.filter(vendorId_id = vendor_id, id = order_id).first()
            
            if not order:
                order = coreOrder.objects.filter(vendorId_id = vendor_id, externalOrderId = order_id).first()
            
            order.Status = core_order_status

            order.save()
            
    except Exception as err :
        print(f"updateCoreOrder: {str(err)}")


def singleStationWiseRemove(id, old, current, stn):
    try:
        processing_order_status_number = str(koms_order_status_number["Processing"])
        ready_order_status_number = str(koms_order_status_number["Ready"])
            
        if old == processing_order_status_number:
            if Order_content.objects.filter(orderId_id = id, status = processing_order_status_number, stationId = stn.pk).exists():
                current = processing_order_status_number

        else:
            order_content = Order_content.objects.filter(stationId = stn, orderId = id)

            if order_content:
                order_contents_count = order_content.count()

                if order_contents_count == order_content.filter(status = ready_order_status_number):
                    old = ready_order_status_number
        
        webSocketPush(
            message = {"oldStatus": old, "newStatus": current, "id": id, "orderId": Order.objects.get(pk=id).externalOrderId, "UPDATE": "REMOVE"},
            room_name = f"STATION{str(stn.pk)}",
            username = "CORE"
        )
    
    except Exception as e:
        print(e)


def removeFromInqueueAndInsertInProcessing(id, old, current, stn):
    try:
        webSocketPush(
            message = {"oldStatus": old, "newStatus": current, "id": id, "orderId": Order.objects.get(pk=id).externalOrderId, "UPDATE": "REMOVE"},
            room_name = f"STATION{str(stn.pk)}",
            username = "CORE"
        )
    
    except Exception as e:
        print(e)


def allStationWiseData(vendorId):
    stations = Station.objects.filter(vendorId = vendorId)

    for station in stations:
        webSocketPush(message = stationdata(station.pk), room_name = f"STATION{str(station.pk)}", username = "CORE")


def allStationWiseSingle(id, vendorId):
    koms_order = Order.objects.get(pk = id)

    stations = Station.objects.filter(vendorId = vendorId)

    for station in stations:
        order_content = Order_content.objects.filter(stationId = station, orderId = koms_order)

        if order_content:
            totalContentsCount = order_content.count()

            order_data = getOrder(ticketId = koms_order.pk, vendorId = vendorId)

            sorted_data = {}

            for key, value in order_data['items'].items():
                if value[0]["stationId"] != int(station.pk):
                    sorted_data[key] = value
            
            order_data['items'] = sorted_data

            assign_order_status_number = koms_order_status_number["Assign"]
            processing_order_status_number = koms_order_status_number["Processing"]
            ready_order_status_number = koms_order_status_number["Ready"]
            cancelled_order_status_number = koms_order_status_number["Canceled"]
            onhold_order_status_number = koms_order_status_number["Onhold"]

            if order_content.filter(status = str(assign_order_status_number)).exists():
                order_data['status'] = assign_order_status_number

            elif order_content.filter(status = str(processing_order_status_number)).exists():
                order_data['status'] = processing_order_status_number

            elif totalContentsCount == order_content.filter(status = str(ready_order_status_number)):
                order_data['status'] = ready_order_status_number

            elif totalContentsCount == order_content.filter(status = str(cancelled_order_status_number)):
                order_data['status'] = cancelled_order_status_number

            elif order_content.filter(status = str(onhold_order_status_number)).exists():
                order_data['status'] = onhold_order_status_number
            
            webSocketPush(message = order_data, room_name = f"STATION{str(station.pk)}", username = "CORE")


def allStationWiseRemove(id, old, current, vendorId):
    stations = Station.objects.filter(vendorId = vendorId)
    
    for station in stations:
        webSocketPush(
            message = {
                "oldStatus": old,
                "newStatus": current,
                "id": id,
                "orderId": Order.objects.get(pk=id).externalOrderId,
                "UPDATE": "REMOVE",
            },
            room_name = f"STATION{str(station.pk)}",
            username = "CORE",
        )


class StaffView(APIView):
    def get(self, request, *args, **kwargs):
        stationList = Staff.objects.filter(vendorId = request.GET.get("vendorId"))

        serializers = StaffReaderSerializer(stationList, many=True)

        return JsonResponse(serializers.data, safe=False)


class StationsStaffView(APIView):
    def get(self, request, stationId, *args, **kwargs):
        stationList = Staff.objects.filter(station_id = stationId, vendorId_id = request.GET.get("vendorId")).all()

        serializers = StaffReaderSerializer(stationList, many=True)

        return JsonResponse(serializers.data, safe=False)


@api_view(["POST"])
def koms_login(request):
    request_json = JSONParser().parse(request)

    try:
        station = Station.objects.filter(
            client_id = request_json.get('username'),
            client_secrete = request_json.get('password')
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
        
        return Response(response_data, status = status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse({"msg": "not found"}, status = status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def stationOrder(request):
    request_body = JSONParser().parse(request)

    start_date = request_body.get("start")
    end_date = request_body.get("end")
    vendor_id = request.GET.get("vendorId")

    order_ids = Order.objects.filter(
        arrival_time__date__range = (start_date, end_date),
        vendorId = vendor_id
    ).values_list("id", flat=True)

    stations = Station.objects.filter(isStation=True, vendorId=vendor_id)

    response = []

    for station in stations:
        station_id = station.pk

        test = Order_content.objects.filter(orderId__in = order_ids, stationId = station_id)
        
        station_details = {
            "id": station_id,
            "name": station.station_name,
            "count": test.count(),
            "colorCode": station.color_code,
        }

        response.append(station_details)

    return Response(response, status = status.HTTP_200_OK)


@api_view(["POST"])
def orderCount(request):
    try:
        vendor_id = request.GET.get("vendorId")

        request_data = JSONParser().parse(request)

        start_date = request_data.get("start")
        end_date = request_data.get("end")

        koms_orders = Order.objects.filter(arrival_time__date__range = (start_date, end_date), vendorId = vendor_id)

        response = []
    
        for key, value in koms_order_status_number:
            data = {
                "status": value,
                "name": key,
                "count": koms_orders.filter(order_status = value).count(),
            }

            if value == koms_order_status_number["High"]:
                data['count']  = koms_orders.filter(isHigh = True).count()
            
            response.append(data)
            
    except Exception as e:
        print(str(e))
        pass

    return Response({"total": koms_orders.count(), "data": response}, status = status.HTTP_200_OK)


@api_view(["POST"])
def ticketSearch(request):
    request_data = JSONParser().parse(request)

    ticketId = request_data.get("ticketId")

    if ticketId is not None:
        try:
            orders = Order.objects.filter(Q(externalOrderId=ticketId) | Q(id=ticketId), vendorId = request.GET.get("vendorId"))

            serializedData = Order_serializer(orders, many=True)

            return Response(serializedData.data, status = status.HTTP_400_BAD_REQUEST)

        except:
            return Response({"error": "Invalid ticket Id"}, status = status.HTTP_400_BAD_REQUEST)

    else:
        return Response({"error": "invalid arguments"}, status = status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "PUT"])
def updateTicketStatus(request):
    vendor_id = request.GET.get("vendorId")
    language = request.GET.get("language", "English")
    
    request_data = JSONParser().parse(request)

    koms_order_id = request_data.get("ticketId")
    content_id = request_data.get("contentId")
    koms_order_status = request_data.get("status")
    new_order_status = request_data.get("ticketStatus")

    if content_id:
        change_order_status = False

        try:
            content = Order_content.objects.get(pk=content_id)

            data = {"status": koms_order_status}

            old_content = content.status

            serialized_order_content = Order_content_serializer(instance=content, data=data, partial=True)

            orders = Order.objects.get(pk=koms_order_id, vendorId=vendor_id)

            old_order_status = orders.order_status

            recall = Order_content.objects.get(pk = content_id).isrecall

            if serialized_order_content.is_valid():
                serialized_order_content.save()
                
                order_content = Order_content.objects.filter(orderId=koms_order_id)
                
                Order_content.objects.filter(pk=content_id).update(status = koms_order_status, isrecall = recall)
                
                if order_content.filter(status = str(koms_order_status_number["Processing"])).count() > 0:
                    processStation(
                        oldStatus = str(old_order_status),
                        currentStatus = str(koms_order_status_number["Processing"]),
                        orderId = orders.pk,
                        station = content.stationId,
                        vendorId = vendor_id
                    )

                exclude_koms_order_status_list = (
                    str(koms_order_status_number["Ready"]),
                    str(koms_order_status_number["Onhold"]),
                    str(koms_order_status_number["Canceled"]),
                    str(koms_order_status_number["Recall"]),
                )
                
                if order_content.exclude(status__in = exclude_koms_order_status_list).count() == \
                order_content.filter(status = str(koms_order_status_number["Processing"])).count():
                    if content.orderId.order_status in (koms_order_status_number["Assign"], koms_order_status_number["Onhold"]):
                        change_order_status = True 

                        Order.objects.filter(id = content.orderId.pk, vendorId = vendor_id)\
                        .update(order_status = koms_order_status_number["Processing"]) 
                        
                        webSocketPush(
                            message = {"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",},
                            room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                            username = "CORE",
                        )
                
                if order_content.count() == order_content.filter(status = str(koms_order_status_number["Canceled"])).count():
                    change_order_status=True

                    Order.objects.filter(id = content.orderId.pk, vendorId = vendor_id)\
                    .update(order_status = koms_order_status_number["Canceled"], isHigh = False)
                    
                    webSocketPush(
                        message = {"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",},
                        room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                        username = "CORE",
                    )
                
                elif order_content.exclude(status = str(koms_order_status_number["Canceled"])).count() == \
                order_content.filter(status = str(koms_order_status_number["Ready"])).count():
                    if orders.order_status != koms_order_status_number["Ready"]:
                        change_order_status = True
                        
                        webSocketPush(
                            message = {"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",},
                            room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                            username = "CORE",
                        )
                     
                    Order.objects.filter(id = content.orderId.pk, vendorId = vendor_id)\
                    .update(order_status = koms_order_status_number["Ready"], isHigh = False)
                
                if order_content.count() == 1:
                    Order.objects.filter(id = content.orderId.pk, vendorId = vendor_id)\
                    .update(order_status = koms_order_status_number["Ready"], isHigh = False)
                    
                    change_order_status = True
                    
                    webSocketPush(
                        message = {"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",},
                        room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                        username = "CORE",
                    )                      

                if content.status == str(koms_order_status_number["Recall"]):
                    exclude_koms_order_status_list = (
                        str(koms_order_status_number["Ready"]),
                        str(koms_order_status_number["Canceled"]),
                        str(koms_order_status_number["Recall"]),
                    )

                    Order_content.objects.exclude(status__in = exclude_koms_order_status_list).filter(pk = content.pk)\
                    .update(status = str(koms_order_status_number["Processing"]), isrecall = True)
                    
                    Order.objects.filter(id = content.orderId.pk, vendorId = vendor_id)\
                    .update(order_status = koms_order_status_number["Processing"], isHigh = False)
                    
                    if old_order_status != koms_order_status_number["Processing"]:
                        change_order_status = True

                        webSocketPush(
                            message = {"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE",},
                            room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                            username = "CORE",
                        )
                        
                order_content = Order_content.objects.filter(orderId = koms_order_id)
                
                status_list = tuple(order_content.values_list("status", flat=True).distinct())

                if (str(koms_order_status_number["Onhold"]) in status_list) and \
                (str(koms_order_status_number["Assign"]) not in status_list):
                    change_order_status = True
                    
                    Order.objects.filter(id = content.orderId.pk, vendorId = vendor_id)\
                    .update(order_status = koms_order_status_number["Onhold"])
                    
                    webSocketPush(
                        message = {"id": orders.pk, "orderId": orders.externalOrderId, "UPDATE": "REMOVE"},
                        room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                        username = "CORE",
                    )
                
                if not change_order_status:
                    webSocketPush(
                        message = getOrder(ticketId = koms_order_id, vendorId = vendor_id),
                        room_name = f"{str(vendor_id)}-{str(Order.objects.get(pk = koms_order_id, vendorId = vendor_id).order_status)}",
                        username = "CORE"
                    )
                
                webSocketPush(message = stationQueueCount(vendorId = vendor_id), room_name = f"WHEELSTATS{str(vendor_id)}", username = "CORE")
                webSocketPush(message = statuscount(vendorId = vendor_id), room_name = "STATUSCOUNT", username = "CORE")
                webSocketPush(message = CategoryWise(vendorId = vendor_id), room_name = "STATIONSIDEBAR", username = "CORE")
                
                processStation(
                    oldStatus = old_content,
                    currentStatus = Order_content.objects.get(pk=content.pk).status,
                    orderId = content.orderId.pk,station=content.stationId,
                    vendorId = vendor_id
                )

                subtotal = 0

                order_content_without_cancelled_order = Order_content.objects.filter(orderId=orders.pk)\
                .exclude(status = str(koms_order_status_number["Canceled"]))

                for content_instance in order_content_without_cancelled_order:
                    product_price = Product.objects.filter(PLU = content_instance.SKU, vendorId = vendor_id).first().productPrice
                    
                    subtotal = subtotal + (product_price * content_instance.quantity)
                    
                    ordered_modifiers = Order_modifer.objects.filter(contentID = content_instance.pk)
                    
                    for modifier_instance in ordered_modifiers:
                        modifier_price = ProductModifier.objects.filter(modifierPLU = modifier_instance.SKU, vendorId = vendor_id).first().modifierPrice
                        
                        subtotal = subtotal + (modifier_price * modifier_instance.quantity)
                
                master_order_instance = coreOrder.objects.filter(pk = orders.master_order.pk).first()
                
                master_order_instance.subtotal = subtotal
                
                tax_total = 0

                vendor_taxes = Tax.objects.filter(is_active = True, vendor = vendor_id)
                
                for tax in vendor_taxes:
                    tax_total = tax_total + (master_order_instance.subtotal * (tax.percentage / 100))
                
                master_order_instance.tax = tax_total
                
                master_order_instance.TotalAmount = master_order_instance.subtotal + tax_total
                
                master_order_instance.save()
                
                waiteOrderUpdate(orderid=koms_order_id, language=language, vendorId=vendor_id)
                
                updateCoreOrder(order = Order.objects.get(pk = koms_order_id, vendorId = vendor_id))
                
                allStationWiseCategory(vendorId = vendor_id)  # all stations sidebar category wise counts
                
                return Response(serialized_order_content.data, status = status.HTTP_200_OK)
        
        except:
            return Response({"error": "Invalid ticket Id"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)

    if koms_order_id is not None:
        orders = Order.objects.filter(pk = koms_order_id, vendorId = vendor_id).first()
        
        try:
            old_order_status = orders.order_status

            if new_order_status in koms_order_status_number.values():

                koms_order_status = koms_order_status

                exclude_koms_order_status_list = (
                    str(koms_order_status_number["Ready"]),
                    str(koms_order_status_number["Canceled"]),
                    str(koms_order_status_number["Recall"])
                )

                if new_order_status == koms_order_status_number["High"]:
                    Order.objects.filter(pk = koms_order_id, vendorId = vendor_id).update(isHigh = True)
                    
                    Order_content.objects.filter(orderId = koms_order_id).update(status = koms_order_status_number["Assign"])
                
                elif new_order_status == koms_order_status_number["Assign"]:
                    if old_order_status == koms_order_status_number["Recall"]:
                        for instance in Order_content.objects.filter(orderId = koms_order_id):
                            if instance.status == str(koms_order_status_number["Recall"]):
                                instance.status = koms_order_status
                                instance.save()
                    
                    else:
                        Order_content.objects.filter(orderId = koms_order_id).update(status = koms_order_status)
                
                elif new_order_status in (koms_order_status_number["Onhold"], koms_order_status_number["Canceled"]):
                    Order_content.objects.exclude(status__in = exclude_koms_order_status_list)\
                    .filter(orderId = koms_order_id).update(status = str(koms_order_status))
                
                elif new_order_status in (koms_order_status_number["Ready"], koms_order_status_number["Canceled"]):
                    Order_content.objects.filter(orderId = koms_order_id).exclude(status = str(koms_order_status_number["Canceled"]))\
                    .update(status = str(koms_order_status))
                    
                    Order.objects.filter(id = koms_order_id).update(isHigh = False)
                
                if old_order_status == koms_order_status_number["High"]:
                    Order_content.objects.filter(orderId = koms_order_id).update(status = str(koms_order_status))
                    
                    Order.objects.filter(id = koms_order_id, vendorId = vendor_id).update(isHigh = True)
                
                elif old_order_status in (koms_order_status_number["Processing"], koms_order_status_number["Onhold"]):
                    Order_content.objects.exclude(status__in = exclude_koms_order_status_list)\
                    .filter(orderId = koms_order_id).update(status = str(koms_order_status))
                
                Order.objects.filter(id = koms_order_id, vendorId = vendor_id).update(order_status = koms_order_status)
            

            elif new_order_status == koms_order_status_number["Recall"]:
                koms_order_status = koms_order_status
                
                Order.objects.filter(id = koms_order_id, vendorId = vendor_id).update(order_status = koms_order_status)
                
                Order_content.objects.exclude(status__in = exclude_koms_order_status_list)\
                .filter(orderId=koms_order_id).update(status=koms_order_status)
          
            data = {"order_status": koms_order_status}
            
            serialized_order_content = Order_serializer(instance=orders, data=data, partial=True)
            
            if serialized_order_content.is_valid():
                serialized_order_content.save()

            koms_order_status = Order.objects.get(pk = koms_order_id, vendorId = vendor_id).order_status

            if koms_order_status == koms_order_status_number["High"]:
                Order.objects.filter(pk = koms_order_id, vendorId = vendor_id).update(isHigh = True)
                
                Order.objects.filter(pk = koms_order_id, vendorId = vendor_id).update(order_status = koms_order_status_number["Assign"])
            
            elif koms_order_status in (koms_order_status_number["Ready"], koms_order_status_number["Canceled"]):
                Order.objects.filter(id = koms_order_id, vendorId = vendor_id).update(isHigh = False)
            
            webSocketPush(
                message = {"id": orders.pk,"orderId": orders.externalOrderId, "UPDATE": "REMOVE",},
                room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                username = "CORE",
            )
            
            order_content = Order_content.objects.filter(orderId = orders.pk)
            
            for instance in order_content:
                processStation(
                    oldStatus = str(old_order_status),
                    currentStatus = str(koms_order_status),
                    orderId = orders.pk,
                    station = instance.stationId,
                    vendorId = vendor_id
                )
            
            allStationWiseRemove(id = orders.pk, old = str(old_order_status), current = str(koms_order_status), vendorId = vendor_id)
            allStationWiseSingle(id = koms_order_id, vendorId = vendor_id)
           
            waiteOrderUpdate(orderid = koms_order_id, language = language, vendorId = vendor_id)
            
            allStationWiseCategory(vendorId = vendor_id)
            
            updateCoreOrder(order = Order.objects.get(pk = koms_order_id))

            return Response(serialized_order_content.data, status = status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response( {"error": "Invalid ticket Id"}, status = status.HTTP_400_BAD_REQUEST)
        
    else:
        print("invalid arguments")
        return Response({"error": "invalid arguments"}, status = status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def assignChef(request):
    vendor_id = request.GET.get("vendorId")

    request_data = JSONParser().parse(request)

    content_id = request_data.get("contentId")
    chef_id = request_data.get("chefId")
    koms_order_id = request_data.get("ticketId")
    koms_order_status = request_data.get("orderStatus")

    change_order_status = False

    if content_id:
        data = {"staffId": chef_id, "contentID": content_id}

        try:
            content_assigned = Content_assign.objects.filter(contentID = content_id).first()

            order_content_instance = Order_content.objects.get(pk = content_id)

            koms_order_id_from_content = order_content_instance.orderId.pk

            order_content = Order_content.objects.filter(orderId = koms_order_id_from_content)

            old_order_status = order_content_instance.orderId.order_status

            if not content_assigned:
                content_assign_serializer = Content_assign_serializer(data = data)

                content_data = {"status": koms_order_status_number["Processing"]}

                order_content_serializer = Order_content_serializer(instance=order_content_instance, data=content_data, partial=True)

                if order_content_serializer.is_valid():
                    order_content_serializer.save()

                if order_content.exclude(status__in = (str(koms_order_status_number["Ready"]), str(koms_order_status_number["Canceled"]))).count() ==\
                order_content.filter(status = str(koms_order_status_number["Processing"])).count():
                    change_order_status = True
                    
                    Order.objects.filter(pk = koms_order_id_from_content, vendorId = vendor_id).update(order_status = 2)
                    
                    webSocketPush(
                        message = {"id": koms_order_id_from_content, "orderId": order_content_instance.orderId.externalOrderId, "UPDATE": "REMOVE",},
                        room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                        username = "CORE",
                    )
            
            else:
                Order_content.objects.filter(pk = content_id).update(status = 2)

                content_assign_serializer = Content_assign_serializer(instance = content_assigned, data = data)

                if order_content.exclude(status__in = (str(koms_order_status_number["Ready"]), str(koms_order_status_number["Canceled"]))).count() ==\
                order_content.filter(status = str(koms_order_status_number["Processing"])).count():
                    if Order.objects.get(pk = koms_order_id_from_content, vendorId = vendor_id).order_status != 2:
                        change_order_status = True
                        
                        Order.objects.filter(pk = koms_order_id_from_content, vendorId = vendor_id).update(order_status = 2)
                        
                        webSocketPush(
                            message = {"id": koms_order_id_from_content, "orderId": order_content_instance.orderId.externalOrderId, "UPDATE": "REMOVE",},
                            room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                            username = "CORE",
                        )

            if content_assign_serializer.is_valid():
                old_order_status = order_content_instance.orderId.order_status
                content_assign_serializer.save()

                order_content = Order_content.objects.filter(orderId = koms_order_id_from_content)
                
                status_list = tuple(order_content.values_list("status", flat=True).distinct())

                if (str(koms_order_status_number["Onhold"]) in status_list) and \
                (str(koms_order_status_number["Assign"]) not in status_list):
                    change_order_status = True

                    Order.objects.filter(pk = koms_order_id_from_content, vendorId = vendor_id).update(order_status = koms_order_status_number["Onhold"])
                    
                    webSocketPush(
                        message = {"id": koms_order_id_from_content, "orderId": order_content_instance.orderId.externalOrderId, "UPDATE": "REMOVE"},
                        room_name = f"{str(vendor_id)}-{str(old_order_status)}",
                        username = "CORE"
                    )

                elif (str(koms_order_status_number["Processing"]) in status_list) and \
                (str(koms_order_status_number["Assign"]) not in status_list):
                    webSocketPush(
                        message = {
                            "oldStatus": old_order_status,
                            "newStatus": order_content_instance.status,
                            "id": koms_order_id_from_content,
                            "orderId": order_content_instance.orderId.externalOrderId,
                            "UPDATE": "REMOVE"
                        },
                        room_name = f"STATION{str(order_content_instance.stationId.pk)}",
                        username = "CORE"
                    )

                if order_content.filter(status = str(koms_order_status_number["Processing"])).exists():
                    webSocketPush(
                        message = {
                            "oldStatus": old_order_status,
                            "newStatus": str(koms_order_status_number["Processing"]),
                            "id": koms_order_id_from_content,
                            "orderId": order_content_instance.orderId.externalOrderId,
                            "UPDATE": "REMOVE"
                        },
                        room_name = f"STATION{str(order_content_instance.stationId.pk)}",
                        username = "CORE"
                    )
                    
                    processStation(
                        oldStatus = str(old_order_status),
                        currentStatus = str(koms_order_status_number["Processing"]),
                        orderId = koms_order_id_from_content,
                        station = order_content_instance.stationId,
                        vendorId = vendor_id
                    )

                if not change_order_status:
                    webSocketPush(
                        message = getOrder(ticketId = koms_order_id, vendorId = vendor_id),
                        room_name = f"{str(vendor_id)}-{str(koms_order_status)}",
                        username = "CORE"
                    )

                    webSocketPush(
                        message = getOrder(ticketId = koms_order_id, vendorId = vendor_id),
                        room_name = f"{str(vendor_id)}-{str(Order.objects.get(pk = koms_order_id, vendorId = vendor_id).order_status)}",
                        username = "CORE"
                    )
                
                webSocketPush(
                    message = stationQueueCount(vendorId = vendor_id),
                    room_name = f"WHEELSTATS{str(vendor_id)}",
                    username = "CORE"
                )
                
                allStationWiseSingle(id = koms_order_id_from_content, vendorId = vendor_id)
                
                waiteOrderUpdate(orderid = koms_order_id_from_content, vendorId = vendor_id)
            
            else:
                return Response({"error": "Something went wrong"}, status = status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(e)
            return Response({"error": "Something went wrong"}, status = status.HTTP_400_BAD_REQUEST)
    
    webSocketPush(message = statuscount(vendorId = vendor_id), room_name = f"STATUSCOUNT{str(vendor_id)}", username= "CORE")
    
    return Response(content_assign_serializer.data, status = status.HTTP_200_OK)


@api_view(["GET"])
def chart_api(request, start_date, end_date):
    try:
        vendor_id = request.GET.get("vendorId")

        start_datetime = start_date + " 00:00:00.000000"
        end_datetime = end_date + " 23:59:59.000000"

        pending_order_status_number = koms_order_status_number["Pending"]
        processing_order_status_number = koms_order_status_number["Processing"]
        ready_order_status_number = koms_order_status_number["Ready"]
        onhold_order_status_number = koms_order_status_number["Onhold"]
        cancelled_order_status_number = koms_order_status_number["Canceled"]
        recall_order_status_number = koms_order_status_number["Recall"]
        high_order_status_number = koms_order_status_number["High"]
        assign_order_status_number = koms_order_status_number["Assign"]
        close_order_status_number = koms_order_status_number["Close"]
        
        result = {}
        realtime = {}

        total_orders = Order.objects.filter(master_order__OrderDate__range = (start_datetime, end_datetime), vendorId = vendor_id)
        
        total_order_count = total_orders.count()
        
        inqueue_order_count = total_orders.filter(order_status = pending_order_status_number).count()
        cooking_order_count = total_orders.filter(order_status__in = (
            processing_order_status_number, recall_order_status_number, high_order_status_number
        )).count()
        complete_order_count = total_orders.filter(order_status = ready_order_status_number).count()
        onhold_order_count = total_orders.filter(order_status = onhold_order_status_number).count()
        cancel_order_count = total_orders.filter(order_status = cancelled_order_status_number).count()
        assign_order_count = total_orders.filter(order_status = assign_order_status_number).count()
        close_order_count = total_orders.filter(order_status = close_order_status_number).count()

        realtime['Inqueue'] = percent(inqueue_order_count, total_order_count)
        realtime['Cooking'] = percent(cooking_order_count, total_order_count)
        realtime['Complete'] = percent(complete_order_count, total_order_count)
        realtime['OnHold'] = percent(onhold_order_count, total_order_count)
        realtime['Cancel'] = percent(cancel_order_count, total_order_count)
        realtime['Assign'] = percent(assign_order_count, total_order_count)
        realtime['Close'] = percent(close_order_count, total_order_count)
        
        result["realtime"] = dictionary_to_list(realtime)

        history = {}

        total_orders = Order.objects.filter(arrival_time__range = (start_datetime, end_datetime), vendorId = vendor_id)
        
        total_orders_count = total_orders.count()

        complete_order_count = total_orders.filter(order_status = ready_order_status_number).count()
        cancel_order_count = total_orders.filter(order_status = cancelled_order_status_number).count()
        
        history["complete"] = percent(complete_order_count, total_orders_count)
        history["cancel"] = percent(cancel_order_count, total_orders_count)

        result["orderHistory"] = history

        station_chart_data = {}
        order = 0

        total_orders = Order.objects.filter(arrival_time__range = (start_datetime, end_datetime), vendorId = vendor_id)

        for koms_order_instance in total_orders:
            order = order + Order_content.objects.filter(orderId = koms_order_instance.pk).count()
        
        stations = Station.objects.filter(isStation = True, vendorId = vendor_id)
        
        for station_instance in stations:
            content = 0

            for order_instance in total_orders:
                order_content_count = Order_content.objects.filter(orderId = order_instance.pk, stationId = station_instance.pk).count()

                if order_content_count > 0:
                    content = content + order_content_count

                    station_chart_data[station_instance.station_name] = percent(content, order)

                else:
                    station_chart_data[station_instance.station_name] = percent(order_content_count, order)
        
        result["stations"] = dictionary_to_list(station_chart_data)

        # complete_orders = OrderHistory.objects.filter(
        #     order_status = ready_order_status_number,
        #     timestamp__range = (start_datetime, end_datetime),
        #     vendorId = vendor_id
        # )
        
        # complete_order_data = {
        #     "delay": percent(complete_orders.filter(delay__gt = 10, recall = 0).count(), complete_orders.count()),
        #     "recall": percent(complete_orders.filter(recall = 1).count(), complete_orders.count()),
        # }

        result["complete"] = dictionary_to_list({"delay": 0, "recall": 0})

        # cancel_orders = OrderHistory.objects.filter(
        #     order_status = cancelled_order_status_number,
        #     timestamp__range = (start_datetime, end_datetime),
        #     vendorId = vendor_id
        # )
        
        # cancel_order_data = {
        #     "delay": percent(cancel_orders.filter(delay__gt = 10, recall = 0).count(), cancel_orders.count()),
        #     "recall": percent(cancel_orders.filter(recall = 1).count(), cancel_orders.count()),
        # }

        result["cancel"] = dictionary_to_list({"delay": 0, "recall": 0})

        result["source"] = [] # Remove this

        graph_data = []

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        orders = Order.objects.filter(
            arrival_time__date__range = (start_date, end_date),
            vendorId = vendor_id
        )

        current_date = datetime.now().date()

        if start_date == end_date:
            if (start_date == current_date) and (end_date == current_date):
                end_datetime = datetime.now().replace(minute=59, second=59, microsecond=0)
        
            elif (start_date != current_date) and (end_date != current_date):
                end_datetime = datetime.combine(start_date, time(23, 59, 59))

            current_datetime = datetime.combine(start_date, time(0, 0, 0))
            
            while current_datetime <= end_datetime:
                orders = orders.filter(
                    arrival_time__range = (current_datetime, current_datetime + timedelta(hours=1)),
                    vendorId = vendor_id
                )

                if orders.count() != 0:
                    data = {"date": str(current_datetime), "count": orders.count()}

                    graph_data.append(data)

                current_datetime = current_datetime + timedelta(hours=1)

        else:
            unique_order_dates = sorted(set(orders.values_list('arrival_time__date', flat=True)))

            for unique_date in unique_order_dates:
                filtered_orders = orders.filter(arrival_time__date = unique_date, vendorId = vendor_id)

                if filtered_orders.count() != 0:
                    data = {"date": str(datetime.combine(unique_date, time(0, 0, 0))), "count": filtered_orders.count()}

                    graph_data.append(data)

        result["date"] = graph_data

        return Response(result)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def makeunique(request, msg_type='', msg='', desc='', stn='', vendorId=0):
    for station in stn.split(','):
        notify(type = msg_type, msg = msg, desc = desc, stn = [station], vendorId = vendorId)

    return Response({"G": "G"})


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

        vendor_taxes = Tax.objects.filter(is_active = True, vendor = vendor_id)

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

        taxes = Tax.objects.filter(is_active = True, vendor = vendor_id)
        
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
        
        allStationWiseRemove(id = order.pk, old = str(old_status), current = str(current_status), vendorId = vendor_id)
        allStationWiseSingle(id = order.pk, vendorId = vendor_id)
        allStationWiseCategory(vendorId = vendor_id)
        
        return Response({"message": ""})
    
    except Exception as e:
        return Response({"message": str(e)})
