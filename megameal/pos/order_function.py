from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from datetime import datetime
from kiosk.models import KioskOrderData
from kiosk.serializer import KiosK_create_order_serializer
from django.db import transaction
from core.POS_INTEGRATION.staging_pos import StagingIntegration
from core.PLATFORM_INTEGRATION.koms_order import KomsEcom
from core.utils import API_Messages
from core.models import Vendor, Platform, Tax, Product, ProductCategory, ProductCategoryJoint, ProductModifier
from order.models import Customer, Address, Order_Discount, OrderPayment
from koms.models import Station, Order_tables, Order_content, Order_modifer, Order as KOMSOrder
from core.utils import send_order_confirmation_email
from inventory.utils import sync_order_content_with_inventory
from koms.serializers.order_serializer import OrderSerializerWriterSerializer
from koms.serializers.order_content_serializer import Order_content_serializer
from koms.serializers.order_modifer_serializer import OrderModifierWriterSerializer
from datetime import timezone, timedelta
from core.models import EmailLog
from megameal.settings import EMAIL_HOST_USER
from django.conf import settings
from django.template.loader import render_to_string
from koms.views import webSocketPush, waiteOrderUpdate,allStationWiseSingle, notify, allStationWiseCategory, statuscount, stationQueueCount, STATUSCOUNT, WHEELSTATS
from pos.views import loyalty_points_redeem
from pos.language import order_has_arrived_locale, payment_type_number
from static.order_status_const import PENDINGINT
from pos.language import order_type_number, koms_order_status_number, local_timezone
import copy
import pytz



@api_view(['POST'])
def createOrder(request):
    try:
        vendor_id = request.GET.get('vendorId', None)
        language = request.GET.get("language", "English")

        if vendor_id is None:
            return JsonResponse({"message": "Vendor Id cannot be empty"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
        platform = Platform.objects.filter(Name=request.data.get('platform'), VendorId=vendor_id).first()

        if (not platform) or (platform.isActive == False):
            return JsonResponse({"message": "Contact your administrator to activate the platform"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
        
        orderid = vendor_id + str(platform.pk) + datetime.now().strftime("%H%M%S%f")[:15]

        payment_type_string = request.data.get("payment_details").get("paymentType")

        if payment_type_string:
            payment_type_string = payment_type_string.capitalize()

        payment_type = payment_type_number[payment_type_string] if payment_type_string else payment_type_number["Cash"]

        result = {
            "language": language,
            "internalOrderId": orderid,
            "vendorId": vendor_id,
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
            "platform": request.data.get('platform'),
            "customer": {
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
            },
            "discount":{
                "value":request.data.get('discount'),
                "calType":2
            },
            "payment": {
                "tipAmount": request.data.get('tip',0.0),
                "payConfirmation": request.data.get("payment_details").get("paymentKey") if request.data.get("payment_details").get("paymentKey") else "",
                "payAmount": request.data.get("finalTotal",0.0),
                "payType": payment_type,
                "mode": payment_type,
                "default": request.data.get("payment_details").get("paymentStatus") if request.data.get("payment_details").get("paymentStatus") else  False,
                "platform": request.data.get("payment_details").get("platform") if request.data.get("payment_details").get("platform") else "N/A",
                "custProfileId": "",
                "custPayProfileId": "",
                "payData": "",
                "CardId": "NA",
                "expDate": "",
                "transcationId": request.data.get("payment_details").get("paymentKey"),
                "lastDigits": "",
                "billingZip": ""
            },
            "tax": request.data.get("tax"),
            "subtotal": request.data.get("subtotal"),
            "finalTotal": request.data.get("finalTotal"),
            "is_wordpress": request.data.get("is_wordpress"),
            "points_redeemed": request.data.get("points_redeemed"),
            "points_redeemed_by": request.data.get("points_redeemed_by"),
        }
        
        # if request.data.get('promocodes'):
        #     discount = Order_Discount.objects.get(pk=request.data.get('promocodes')[0]['id'])

        #     result['discount'] = {
        #         "discountCode": discount.discountCode,
        #         "discountId": discount.plu,
        #         "status": True,
        #         "discountName": discount.discountName,
        #         "discountCost": discount.value
        #     }
        
        items = []

        for item in request.data["products"]:
            product_instance = Product.objects.get(pk=item['productId'], vendorId=vendor_id)
            
            modifier_list_1 = []
            modifier_list_2 = []
            
            for modifier_group in item['modifiersGroup']:
                for modifier in modifier_group['modifiers']:
                    modifier_data = {
                        "plu": ProductModifier.objects.get(pk=modifier["modifierId"]).modifierPLU,
                        "name": modifier['name'],
                        "status": modifier["status"],
                        "group": modifier_group['id']
                    }

                    modifier_list_1.append(modifier_data)

            for modifier_group in item['modifiersGroup']:
                for modifier in modifier_group['modifiers']:
                    if modifier["status"]:
                        modifier = {
                            "plu": ProductModifier.objects.get(pk=modifier["modifierId"]).modifierPLU,
                            "name": modifier['name'],
                            "status": modifier["status"],
                            "quantity": modifier["quantity"],
                            "group": modifier_group['id']
                        }

                        modifier_list_2.append(modifier)
            
            itemData = {
                "plu": product_instance.productParentId.PLU if product_instance.productParentId != None else product_instance.PLU,
                "sku": item.get("sku"),
                "productName": product_instance.productName,
                "quantity": item["quantity"],
                "subItems": modifier_list_1,
                "itemRemark": item["note"],  # Note Unavailable
                "unit": "qty",  # Default
                "modifiers": modifier_list_2
            }
            
            items.append(itemData)

        result["items"] = items

        tokenlist = KioskOrderData.objects.filter(date=datetime.today().date()).values_list('token')

        token = 1 if len(tokenlist)==0 else max(tokenlist)[0] + 1

        # response = order_helper.OrderHelper.openOrder(result, vendor_id)

        #########################################order_helper.OrderHelper.openOrder########################################
        order = copy.deepcopy(result)

        try:
            with transaction.atomic():
                # stageOrder = StagingIntegration().openOrder(order)

                ##################################StagingIntegration().openOrder(order)#####################################
                data = order

                try:
                    coreCustomer = Customer.objects.filter(Phone_Number=data["customer"]["phno"], VendorId=vendorId).first()
                    
                    customer_address = data["customer"]

                    if (data["platform"] == "Website") or (data["platform"] == "Mobile App"):
                        if not coreCustomer:
                            coreCustomer = Customer.objects.create(
                                FirstName = data["customer"]["fname"],
                                LastName = data["customer"]["lname"],
                                Email = data["customer"]["email"],
                                Phone_Number = data["customer"]["phno"],
                                VendorId = vendor_instance
                            )

                            addrs = Address.objects.create(
                                address_line1 = customer_address["address1"],
                                address_line2 = customer_address["address2"],
                                city = customer_address["city"],
                                state = customer_address["state"],
                                country = customer_address["country"],
                                zipcode = customer_address["zip"],
                                type = "shipping_address",
                                is_selected = True,
                                customer = coreCustomer
                            )

                        else:
                            addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first()

                            if not addrs:
                                addrs = Address.objects.create(
                                address_line1 = customer_address["address1"],
                                address_line2 = customer_address["address2"],
                                city = customer_address["city"],
                                state = customer_address["state"],
                                country = customer_address["country"],
                                zipcode = customer_address["zip"],
                                type = "shipping_address",
                                is_selected = True,
                                customer = coreCustomer
                            )
                    
                    else:
                        if coreCustomer and ((coreCustomer.Phone_Number != '0') or (coreCustomer.FirstName != 'Guest')):
                            addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first()

                            if not addrs:
                                addrs = Address.objects.create(
                                    address_line1 = customer_address["address1"],
                                    address_line2 = customer_address["address2"],
                                    city = customer_address["city"],
                                    state = customer_address["state"],
                                    country = customer_address["country"],
                                    zipcode = customer_address["zip"],
                                    type = "shipping_address",
                                    is_selected = True,
                                    customer = coreCustomer
                                )
                    
                except Exception as e:
                    print(e)
                
                data["customer"]["internalId"] = coreCustomer.pk
                
                try:
                    platform_instance = Platform.objects.get(Name=data.get("Platform"), VendorId=vendor_id)
                
                except Exception as ex:
                    print(f"Unexpected {ex=}, {type(ex)=}")
                    platform_instance = None
                
                discount=0.0

                if data.get("discount"):
                    if data.get("discount").get('value'):
                        discount=data.get("discount").get('value')

                order_type = (data.get("orderType")).capitalize()

                order_type = order_type_number[order_type]
                
                order = Order(
                    Status = master_order_status_number["Open"],
                    TotalAmount = 0.0,
                    OrderDate = timezone.now(),
                    Notes = data.get("note"),
                    externalOrderId = data.get("externalOrderId"),
                    orderType = order_type,
                    arrivalTime = timezone.now(),
                    tax = 0.0,
                    discount = discount,
                    tip = 0.0,
                    delivery_charge = 0.0,
                    subtotal = 0.0,
                    customerId = coreCustomer,
                    vendorId = vendor_instance,
                    platform = platform_instance
                ).save()

                request["internalOrderId"] = order.pk
                request["master_id"] = order.pk

                if data.get("discount"):
                    try:
                        discount = Order_Discount.objects.get(vendorId=vendor_id, discountCode=data["discount"].get("discountCode"))
                        
                        data["discount"] = discount.to_dict()

                    except Order_Discount.DoesNotExist:
                        print("Invalid Discount")

                order_details = []

                subtotal = 0.0
                productTaxes = 0.0
                discount = 0.0

                for index, lineItm in enumerate(data["items"]):
                    data["item"] = lineItm

                    lineRes = StagingIntegration.addLineItem(data)

                    if lineRes[API_Messages.STATUS] == API_Messages.ERROR:
                        return lineRes
                    
                    order_details.append(lineRes.get("item"))
                    
                    subtotal = subtotal + lineRes["item"].get("subtotal")
                    productTaxes = productTaxes+lineRes["item"].get("tax")
                    discount = discount+lineRes["item"].get("discount")

                    data["items"][index] = lineRes["item"]

                tax = 0

                if 'total_tax' in data['payment']: 
                    tax = data.get("payment").get("total_tax")

                elif 'tax' in data:
                    tax = data.get("tax")

                else:
                    taxes = Tax.objects.filter(is_active = True, vendor = vendor_id)

                    if taxes.exists():
                        tax = order.tax+productTaxes

                order.tax = tax
                order.subtotal = subtotal
                order.discount = discount
                order.tip = data["tip"]
                data["subtotal"] = subtotal
                order.TotalAmount=(order.subtotal - order.discount + order.tax + order.delivery_charge)

                if order.platform.Name == "Mobile App" or order.platform.Name == "Website":
                    order.TotalAmount = data["payment"]["payAmount"]
                    order.delivery_charge = data["payment"]["shipping_total"]
                    order.tax = data["payment"]["total_tax"]

                order = order.save()

                print("++++ Payment")

                if data.get("payment"):
                    print("++++ Payment Started")

                    OrderPayment(
                        orderId=order,
                        paymentBy=coreCustomer.Email,
                        paymentKey=data["payment"]["payConfirmation"],
                        paid=data["payment"]["payAmount"],
                        due=0.0,
                        tip=data["payment"]["tipAmount"],
                        status=data["payment"].get('default', False),
                        type=data["payment"].get('mode', "Cash"),
                        platform=data["payment"].get('platform', "")
                    ).save()

                if ((coreCustomer.Phone_Number != '0') or (coreCustomer.FirstName != 'Guest')) and \
                ((order.platform.Name == 'Website') or (order.platform.Name == 'Mobile App')):
                    tax_details = []
                    
                    taxes = Tax.objects.filter(is_active = True, vendor = vendor_id)

                    if taxes:
                        for tax in taxes:
                            tax_details.append({
                                'name': tax.name,
                                'percentage': tax.percentage,
                                'amount': round(order.subtotal * (tax.percentage / 100), 2)
                            })

                    product_details = []
                    counter = 1

                    for product in order_details:
                        modifiers = product.get("modifiers")

                        modifier_details = []

                        for modifier in modifiers:
                            modifier_details.append({
                                "name": modifier.get("name"),
                                "price": modifier.get("price"),
                                "quantity": modifier.get("quantity"),
                                "amount": round((modifier.get("quantity") * modifier.get("price")), 2),
                            })

                        product_details.append({
                            "counter": counter,
                            "name": product.get("productName"),
                            "price": product.get("price"),
                            "quantity": product.get("quantity"),
                            "amount": round((product.get("quantity") * product.get("price")), 2),
                            "modifiers": modifier_details
                        })

                        counter = counter + 1
                    
                    # local_ips = []

                    # host_name = socket.gethostname()

                    # host_ip_info = socket.gethostbyname_ex(host_name)

                    # for ip in host_ip_info[2]:
                    #     if not ip.startswith("127."):
                    #         local_ips.append(ip)

                    # external_ip = None

                    # external_ip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                    # port = request.META.get("SERVER_PORT")

                    # try:
                    #     external_ip_socket.connect(('8.8.8.8', 53))

                    #     external_ip = external_ip_socket.getsockname()[0]

                    # finally:
                    #     external_ip_socket.close()

                    # if local_ips:
                    #     server_ip = local_ips[0]

                    # else:
                    #     server_ip = external_ip
                    
                    sender = EMAIL_HOST_USER
                    receiver = coreCustomer.Email

                    subject = "Your order is confirmed"
                    email_body_type = "html"
                    
                    context = {
                        "order_id": order.pk,
                        "order_type": data.get("orderType"),
                        "first_name": coreCustomer.FirstName,
                        "full_name": coreCustomer.FirstName + " " + coreCustomer.LastName,
                        "phone_number": coreCustomer.Phone_Number,
                        "email": coreCustomer.Email,
                        "shipping_address": addrs,
                        "product_details": product_details,
                        "subtotal": round(order.subtotal, 2),
                        "discount": round(order.discount, 2),
                        "delivery_charge": round(order.delivery_charge, 2),
                        "tax_details": tax_details,
                        "total_amount": round(order.TotalAmount, 2),
                        "logo_url": f"{vendor_instance.logo.url}" if vendor_instance.logo else "",
                        "currency": vendor_instance.currency_symbol,
                    }
                    
                    email_body = render_to_string('email.html', context)
                    
                    email_status = send_order_confirmation_email(sender, receiver, subject, email_body_type, email_body)

                    email_log = EmailLog.objects.create(
                        order=order,
                        sender=sender,
                        receiver=receiver,
                        subject=subject,
                        email_body_type=email_body_type,
                        email_body=email_body,
                        status=email_status,
                        customer=coreCustomer,
                        vendor=vendor_instance
                    )

                    email_log.save()
                ##################################StagingIntegration().openOrder(order)#####################################

                print("stageOrder  ", order)

                result["master_id"] = order["master_id"]
                
                if coreResponse[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                    for reciver in Platform.objects.filter(isActive=True, orderActionType=2):
                        # if (result.get('Platform') == 'Website') or result.get('Platform') == 'Mobile App':
                        #     result = KomsEcom().startOrderThread(order)
                        
                        # else:
                        #     result = KomsEcom().startOrderThread(result)

                        ##################################KomsEcom().startOrderThread(result)#####################################
                        try:
                            if (result.get('Platform') == 'Website') or result.get('Platform') == 'Mobile App':
                                data = order

                            else:
                                data = result

                            waiter_ids = ""
            
                            if data.get('tables'):
                                waiter_id_list = []

                                for item in data['tables']:
                                    if item.get('waiterId'):
                                        waiter_id_list.append(str(item['waiterId']))

                                waiter_ids = ','.join(waiter_id_list)

                            order_type = (data['orderType']).capitalize()

                            order_type = order_type_number[order_type]
                            
                            res = {
                                "language": language,
                                "orderId": data.get('internalOrderId'),
                                "master_id": data.get('master_id'),
                                "externalOrderId": data.get('externalOrderId'),
                                "orderType": order_type,
                                "arrivalTime": data['arrivalTime'] if data['arrivalTime']!= ""  else f"{str(datetime.today().date())}T{datetime.now(local_timezone).strftime('%H:%M:%S')}",
                                "pickupTime": data['pickupTime'] if data['pickupTime']!= ""  else f"{str(datetime.today().date())}T{datetime.now(local_timezone).strftime('%H:%M:%S')}",
                                "deliveryIsAsap": data['deliveryIsAsap'],
                                "tableNo": data['tables'] if data.get('tables') else [] ,
                                "items": {},
                                "remake": data['remake'] if 'remake' in data else False,
                                "customerName": f"{data['customer']['fname']} {data['customer']['lname']}",
                                "status": 1,
                                "server": waiter_ids,
                                "isHigh": True if "priority" in  data else False,
                                "note": data["note"] if data["note"] else None,
                                "vendorId": vendor_id 
                            }

                            totalPrepTime = 0

                            for index,itemData in enumerate(data['items']):
                                data['items'][index]["prepTime"] = KomsEcom.getPrepTime(itemData["plu"])
                                
                                totalPrepTime = totalPrepTime + data['items'][index]["prepTime"]

                            res["totalPrepTime"] = totalPrepTime
                            
                            if totalPrepTime > 0:
                                current_time = datetime.now(pytz.timezone('Asia/Kolkata'))

                                new_time = current_time + timedelta(minutes=totalPrepTime)

                                res["pickupTime"] = f"{str(datetime.today().date())}T{new_time.strftime('%H:%M:%S')}"
                        
                            itemCategoriesSet = set()

                            for i in data['items']:
                                product = Product.objects.filter(PLU=i['plu'], vendorId_id=vendor_id).first()

                                if product is not None:
                                    productCategoryJoint = ProductCategoryJoint.objects.get(product=product.pk)
                                    itemCategoriesSet.add(productCategoryJoint.category.categoryName)

                            itemCategories = list(itemCategoriesSet)
                            
                            for item in itemCategories:
                                prods = []

                                for i in data['items'] :
                                    print(i)

                                    product_id = Product.objects.filter(PLU=i['plu'], vendorId=vendor_id).first().pk
                                    
                                    categoryJoint = ProductCategoryJoint.objects.filter(product=product_id, vendorId=vendor_id).first()

                                    station_id = 1
                                
                                    if categoryJoint:
                                        if categoryJoint.category.categoryStation:
                                            station_id = categoryJoint.category.categoryStation.pk

                                        else:
                                            station = Station.objects.filter(vendorId=vendor_id).first()

                                            if station:
                                                station_id = station.pk
                                    
                                    if categoryJoint.category.categoryName == item:
                                        sub = []
                                        
                                        for subItem in i['modifiers']:
                                            sub.append({
                                                "plu": subItem['plu'],
                                                "name": subItem['name'],
                                                "status": subItem["status"] if subItem.get("status") else False,
                                                "quantity": subItem['quantity'],
                                                "group": subItem['group']
                                            })
                                        
                                        prods.append({
                                            "plu": i['plu'],
                                            "name": i.get('productName') or  i.get('name'),
                                            "quantity": i['quantity'],
                                            "tag": station_id,
                                            "subItems": sub,
                                            "itemRemark": i.get('itemRemark'),
                                            "prepTime": i['prepTime']
                                        })

                                    res['items'][item] = prods
                            
                            # return createOrderInKomsAndWoms(orderJson=res)

                            ##################################createOrderInKomsAndWoms#####################################
                            try:
                                order_data = res

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
                                
                                order_data["guest"]=guestCount
                                order_data["tableNo"]=''
                                order_data["vendorId"]=vendor_id
                                
                                print("koms_order_data \n",order_data)
                                
                                order_serializers = OrderSerializerWriterSerializer(data=order_data, partial=True)

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
                                    return {
                                        API_Messages.STATUS:API_Messages.ERROR,
                                        API_Messages.RESPONSE: order_serializers.errors
                                    }

                                #  product section
                                for key, value in order_data["items"].items():
                                    for singleProduct in value:
                                        # print(singleProduct)
                                        singleProduct["orderId"] = order_save_data.id
                                        singleProduct["quantityStatus"] = 1  # quantityStatus
                                        singleProduct["stationId"] = singleProduct["tag"]
                                        singleProduct["stationName"] = None
                                        
                                        category = ProductCategory.objects.filter(categoryName = key,vendorId = order_data["vendorId"])
                                        
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
                                                
                                                single_modifier_serializer = OrderModifierWriterSerializer(data=singleModifier, partial=True)
                                                
                                                if single_modifier_serializer.is_valid():
                                                    single_mod_data = single_modifier_serializer.save()
                                                    singleModifier["id"] = single_mod_data.id
                                                    print('modifier saved')
                                                
                                                else:
                                                    print("invalid modifier   ",single_modifier_serializer.errors)
                                        else:
                                            print(single_product_serializer.error_messages)
                                            print(single_product_serializer._errors)
                                
                                webSocketPush(message=stationQueueCount(vendorId=vendor_id),room_name= WHEELSTATS+str(vendor_id), username="CORE")  # wheel man left side
                                webSocketPush(message=statuscount(vendorId=vendor_id),room_name= STATUSCOUNT+str(vendor_id),username= "CORE")  # wheel man status count
                                
                                try:
                                    orderTables = Order_tables.objects.filter(orderId_id=order_save_data.id)
                                    
                                    values_list = [str(item.tableId.tableNumber) for item in orderTables]
                                    values_list = ', '.join(values_list) 
                                
                                except Order_tables.DoesNotExist:
                                    print("Order table not found")
                                    values_list=""
                                
                                wheelman=[i.pk for i in Station.objects.filter(isStation=False,vendorId=vendor_id) ]
                                
                                if Platform.objects.filter(Name="KOMS",VendorId= vendor_id).first().isActive :
                                    webSocketPush(message=order_data, room_name=str(vendor_id)+"-"+str(PENDINGINT), username="CORE")  # wheelMan Pending section
                                    notify(type=1,msg=order_save_data.id,desc=f"Order No { order_save_data.externalOrderId } on Table No {values_list} is arrived",stn=[4],vendorId=vendor_id)
                                
                                else :
                                    stnlist=[i.stationId.pk for i in Order_content.objects.filter(orderId=order_save_data.id)]
                                    allStationWiseSingle(id=order_save_data.id,vendorId=vendor_id)
                                    notify(type=1,msg=order_save_data.id,desc=f"Order No { order_save_data.externalOrderId } is arrived",stn=stnlist,vendorId=vendor_id)
                                
                                language = order_data.get("language", "English")

                                if language == "English":
                                    notify(type=1, msg=order_save_data.id, desc=f"Order No {order_save_data.externalOrderId} is arrived", stn=['POS'], vendorId=vendor_id)
                                
                                else:
                                    notify(type=1, msg=order_save_data.id, desc=order_has_arrived_locale(order_save_data.externalOrderId), stn=['POS'], vendorId=vendor_id)
                                    
                                waiteOrderUpdate(orderid=order_save_data.id, language=language, vendorId=vendor_id)
                                allStationWiseCategory(vendorId=vendor_id)  # all stations sidebar category wise counts
                                
                                platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

                                if platform:
                                    sync_order_content_with_inventory(order_data["master_id"], vendor_id)
                                    
                                return {API_Messages.STATUS:API_Messages.SUCCESSFUL, "id": order_save_data.id,"wheelman":wheelman}
                            
                            except Exception as e:
                                print(e)
                                return {API_Messages.STATUS:API_Messages.ERROR, API_Messages.RESPONSE: f"Unexpected {e=}, {type(e)=}" }
                            ##################################createOrderInKomsAndWoms#####################################

                        
                        except Exception as e:
                            print("Error", e)
                        ##################################KomsEcom().startOrderThread(result)#####################################
                        
                        if order.get('points_redeemed') and  order.get('points_redeemed') != 0:
                            from pos.views import loyalty_points_redeem # placed here due to circular import error

                            is_redeemed = loyalty_points_redeem(
                                vendor_id,
                                order["customer"]["internalId"],
                                order["master_id"],
                                order["is_wordpress"],
                                order["points_redeemed"],
                                order["points_redeemed_by"]
                            )
                    
                            if is_redeemed == True:
                                pass
                            
                            else:
                                print("Order Error in stage++++++++++++++++++")
                                transaction.set_rollback(True)
                    
                else:
                    print("Order Error in stage++++++++++++++++++")
                    transaction.set_rollback(True)

        except Exception as err:
            print("Order Erroo+++++++++++++++++++++")
            print(f"Unexpected {err=}, {type(err)=}")
        ###########################################order_helper.OrderHelper.openOrder####################################
        
        saveData = KiosK_create_order_serializer(data={
            'orderdata': str(result),
            'date': datetime.today().date(),
            'token': token
        })
        
        if saveData.is_valid():
            saveData.save()

            if Order.objects.filter(externalOrderId=orderid).exists():
                return JsonResponse({'token': token, "external_order_id": orderid})
            
            else:
                return JsonResponse({'token': token, "external_order_id": ""})
        
        return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        print(e)
        return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def place_order(request):
    with transaction.atomic():
        try:
            vendor_id = request.GET.get("vendorId")
            platform_name = request.GET.get("platform")
            language = request.GET.get("language", "English")

            if (not vendor_id) or (not platform_name):
                return JsonResponse({"message": "Invalid vendor ID or Platform"}, status=status.HTTP_400_BAD_REQUEST)
        
            try:
                vendor_id = int(vendor_id)

            except ValueError:
                return JsonResponse({"message": "Invalid vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            vendor_instance = Vendor.objects.filter(pk=vendor_id).first()
            
            platform_instance = Platform.objects.filter(Name=platform_name, VendorId=vendor_id).first()

            if not vendor_instance:
                return JsonResponse({"message": "Vendor does not exist"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not platform_instance:
                return JsonResponse({"message": "Platform does not exist"}, status=status.HTTP_400_BAD_REQUEST)

            if platform_instance.isActive == False:
                return JsonResponse({"message": "Contact your administrator to activate the platform"}, status=status.HTTP_400_BAD_REQUEST)
            
            request_data = request.data

            if not request_data:
                return JsonResponse({"message": "Invalid request data"}, status=status.HTTP_400_BAD_REQUEST)

            # if request.data.get('promocodes'):
            #     discount = Order_Discount.objects.get(pk=request.data.get('promocodes')[0]['id'])

            #     result['discount'] = {
            #         "discountCode": discount.discountCode,
            #         "discountId": discount.plu,
            #         "status": True,
            #         "discountName": discount.discountName,
            #         "discountCost": discount.value
            #     }
            
            first_name = request_data.get("first_name")
            last_name = request_data.get("last_name", None)
            phone_number = request_data.get("phone_number")
            email = request_data.get("email", None)
            address = request_data.get("address")
            city = request_data.get("city")
            state = request_data.get("state")
            country = request_data.get("country")
            zipcode = request_data.get("zip")
            order_note = request_data.get("order_note", None)
            order_type = request_data.get("order_type")
            sub_total = request_data.get("sub_total")
            tax = request_data.get("tax")
            discount = request_data.get("discount")
            final_total = request_data.get("final_total")
            payment_type = request_data.get("payment_type")
            transaction_id = request_data.get("transaction_id")
            amount_paid = request_data.get("amount_paid")
            due_amount = request_data.get("due_amount")
            payment_status = request_data.get("payment_status")
            payment_platform = request_data.get("payment_platform")
            products = request_data.get("products")
            points_redeemed = request_data.get("points_redeemed")
            points_redeemed_by = request_data.get("points_redeemed_by")
            tables = request_data.get("tables")
            is_high_priority = request_data.get("is_high_priority")

            if not all((
                first_name, phone_number, address, city, state, country,
                zipcode, order_type, sub_total, tax, discount, final_total, payment_type, transaction_id,
                amount_paid, due_amount, payment_status, payment_platform, products,
            )):
                return JsonResponse({"message": "Invalid request data"}, status=status.HTTP_400_BAD_REQUEST)

            order_type = order_type_number[order_type]

            if phone_number is None:
                customer_instance = Customer.objects.filter(
                    Phone_Number = "0",
                    VendorId = vendor_id,
                ).first()
                
            else:
                customer_instance = Customer.objects.filter(
                    Phone_Number = phone_number,
                    VendorId = vendor_id,
                ).first()

            if customer_instance:
                if (customer_instance.Phone_Number != '0') or (customer_instance.FirstName != 'Guest'):
                    addrs = Address.objects.filter(customer=customer_instance.pk, type="shipping_address", is_selected=True).first() 
                    
                    if not addrs:
                        if all((address, city, state, country, zipcode)):
                            addrs = Address.objects.create(
                                address_line1 = address,
                                city = city,
                                state = state,
                                country = country,
                                zipcode = zipcode,
                                type = "shipping_address",
                                is_selected = True,
                                customer = customer_instance
                            )
            
            else:
                customer_instance = Customer.objects.create(
                    FirstName = first_name,
                    LastName = last_name,
                    Email = email,
                    Phone_Number = phone_number,
                    VendorId = vendor_instance
                )

                if customer_instance.Phone_Number != '0' or customer_instance.FirstName != 'Guest':    
                    if all((address, city, state, country, zipcode)):
                        addrs = Address.objects.create(
                            address_line1 = address,
                            city = city,
                            state = state,
                            country = country,
                            zipcode = zipcode,
                            type = "shipping_address",
                            is_selected = True,
                            customer = customer_instance
                        )

            platform_instance = Platform.objects.filter(Name=platform_name, VendorId=vendor_id).first()
            
            external_order_id = vendor_id + str(platform_instance.pk) + datetime.now().strftime("%H%M%S%f")[:15]
            
            master_order_instance = Order.objects.create(
                externalOrderId = external_order_id,
                OrderDate = timezone.now(),
                arrivalTime = timezone.now(),
                orderType = order_type,
                Status = 1,
                Notes = order_note,
                subtotal = sub_total,
                tax = tax,
                discount = discount,
                delivery_charge = 0.0,
                TotalAmount = final_total,
                customerId = customer_instance,
                vendorId = vendor_instance,
                platform = platform_instance
            )

            OrderCreationHistory.objects.create(
                order = master_order_instance,
                content = products,
                vendor = vendor_instance
            )

            OrderPayment.objects.create(
                orderId = master_order_instance,
                paymentBy = f"{customer_instance.FirstName} {customer_instance.LastName}",
                paymentKey = transaction_id,
                paid = amount_paid,
                due = due_amount,
                status = payment_status,
                type = payment_type,
                platform = payment_platform
            )
                    
            total_preparation_time = 0

            for product in products:
                total_preparation_time = total_preparation_time + KomsEcom.getPrepTime(product["plu"])

            if total_preparation_time > 0:
                current_datetime = datetime.now(pytz.timezone('Asia/Kolkata')).replace(minute = total_preparation_time, second = 0)

                pickup_time = f"{str(current_datetime.date())}T{current_datetime.strftime('%H:%M:%S')}"

            if (points_redeemed > 0) and ((customer_instance.Phone_Number != '0') or (customer_instance.FirstName != 'Guest')):
                is_redeemed = loyalty_points_redeem(
                    vendor_id = vendor_id,
                    customer_id = customer_instance.pk,
                    master_order_id = master_order_instance.pk,
                    points_redeemed = points_redeemed,
                    points_redeemed_by = points_redeemed_by
                )
        
                if is_redeemed == False:
                    transaction.set_rollback(True)

            order_status = koms_order_status_number["Assign"]

            koms_platform = Platform.objects.filter(Name="KOMS", isActive=True, VendorId=vendor_id).first()

            if koms_platform:
                order_status = koms_order_status_number["Pending"]
            
            table_list = []
            waiter_ids = ""
            guest_count = 0

            if tables:
                waiter_id_list = []

                for table in tables:
                    guest_count = guest_count + table.get('guest_count', 0)

                    waiter_id = table.get('waiterId')
                    
                    if waiter_id:
                        waiter_id_list.append(str(waiter_id))

                waiter_ids = ','.join(waiter_id_list)
            
            koms_order_instance = KOMSOrder.objects.create(
                vendorId = vendor_instance,
                externalOrderId = external_order_id,
                pickupTime = pickup_time,
                arrival_time = f"{str(datetime.today().date())}T{datetime.now(local_timezone).strftime('%H:%M:%S')}",
                order_status = order_status,
                order_note = order_note,
                order_type = order_type,
                guest = guest_count,
                server = waiter_ids,
                isHigh = is_high_priority,
                master_order = master_order_instance
            )

            if tables:
                for table in tables:
                    table_instance = Order_tables.objects.create(orderId_id = koms_order_instance.pk, tableId_id = table["tableId"])

                    table_list.append(str(table_instance.tableId.tableNumber))

                table_list = ', '.join(table_list)

            else:
                table_list = ""
                    
            for product in products:
                product_category_joint = ProductCategoryJoint.objects.filter(
                    product = product.get("id"),
                    category = product.get("category_id"),
                    vendorId = vendor_id
                ).first()

                order_content_instance = Order_content.objects.create(
                    orderId = koms_order_instance,
                    name = product.get("name"),
                    quantity = product.get("quantity"),
                    quantityStatus = 1,
                    note = product.get("note"),
                    SKU = product_category_joint.product.PLU,
                    tag = product_category_joint.product.tag,
                    categoryName = product.get("category_name"),
                    stationId = product_category_joint.category.categoryStation,
                    status = order_status,
                )

                for modifier in product.get("modifiers"):
                    Order_modifer.objects.create(
                        contentID = order_content_instance.pk,
                        name = modifier.get("name"),
                        quantityStatus = 1,
                        unit = "units",
                        SKU = modifier.get("plu"),
                        quantity = modifier.get("quantity"),
                        group = modifier.get("group_name"),
                    )
            
            webSocketPush(message = stationQueueCount(vendorId = vendor_id), room_name = f"WHEELSTATS{str(vendor_id)}", username = "CORE")
            
            webSocketPush(message = statuscount(vendorId = vendor_id), room_name = f"STATUSCOUNT{str(vendor_id)}", username = "CORE")
            
            wheelman_list = []

            wheelmen = Station.objects.filter(isStation = False, vendorId = vendor_id)

            for wheelman in wheelmen:
                wheelman_list.append(wheelman.pk)
            
            if koms_platform:
                webSocketPush(message = res, room_name = f"{str(vendor_id)}-1", username = "CORE") #obtain res
                
                notify(
                    type = 1,
                    msg = koms_order_instance.pk,
                    desc = f"Order No {koms_order_instance.externalOrderId} on Table No {table_list} is arrived",
                    stn = [4],
                    vendorId = vendor_id
                )
            
            else :
                station_list = []

                order_contents = Order_content.objects.filter(orderId = koms_order_instance.pk)

                for i in order_contents:
                    station_list.append(i.stationId.pk)

                allStationWiseSingle(id = koms_order_instance.pk, vendorId = vendor_id)

                notify(
                    type = 1,
                    msg = koms_order_instance.pk,
                    desc = f"Order No {koms_order_instance.externalOrderId} is arrived",
                    stn = station_list,
                    vendorId = vendor_id
                )
            
            if language == "English":
                notify(
                    type = 1,
                    msg = koms_order_instance.pk,
                    desc = f"Order No {koms_order_instance.externalOrderId} is arrived",
                    stn = ['POS'],
                    vendorId = vendor_id
                )
            
            else:
                notify(
                    type = 1,
                    msg = koms_order_instance.pk,
                    desc = order_has_arrived_locale(koms_order_instance.externalOrderId),
                    stn = ['POS'],
                    vendorId = vendor_id
                )
                
            waiteOrderUpdate(orderid = koms_order_instance.pk, language = language, vendorId = vendor_id)

            allStationWiseCategory(vendorId = vendor_id)
            
            inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

            if inventory_platform:
                sync_order_content_with_inventory(master_order_instance.pk, vendor_id)
                
            return JsonResponse({"external_order_id": external_order_id})
        
            # For sending email to customers who ordered from website or app
            if ((customer_instance.Phone_Number != '0') or (customer_instance.FirstName != 'Guest')) and \
            ((master_order_instance.platform.Name == 'Website') or (master_order_instance.platform.Name == 'Mobile App')):
                tax_details = []
                
                taxes = Tax.objects.filter(is_active = True, vendor = vendorId)

                if taxes:
                    for tax in taxes:
                        tax_details.append({
                            'name': tax.name,
                            'percentage': tax.percentage,
                            'amount': round(master_order_instance.subtotal * (tax.percentage / 100), 2)
                        })

                product_details = []
                counter = 1

                for product in products:
                    modifiers = product.get("modifiers")

                    modifier_details = []

                    for modifier in modifiers:
                        modifier_details.append({
                            "name": modifier.get("name"),
                            "price": modifier.get("price"),
                            "quantity": modifier.get("quantity"),
                            "amount": round((modifier.get("quantity") * modifier.get("price")), 2),
                        })

                    product_details.append({
                        "counter": counter,
                        "name": product.get("productName"),
                        "price": product.get("price"),
                        "quantity": product.get("quantity"),
                        "amount": round((product.get("quantity") * product.get("price")), 2),
                        "modifiers": modifier_details
                    })

                    counter = counter + 1
                
                # local_ips = []

                # host_name = socket.gethostname()

                # host_ip_info = socket.gethostbyname_ex(host_name)

                # for ip in host_ip_info[2]:
                #     if not ip.startswith("127."):
                #         local_ips.append(ip)

                # external_ip = None

                # external_ip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                # port = request.META.get("SERVER_PORT")

                # try:
                #     external_ip_socket.connect(('8.8.8.8', 53))

                #     external_ip = external_ip_socket.getsockname()[0]

                # finally:
                #     external_ip_socket.close()

                # if local_ips:
                #     server_ip = local_ips[0]

                # else:
                #     server_ip = external_ip
                
                sender = EMAIL_HOST_USER
                receiver = customer_instance.Email

                subject = "Your order confirmed"
                email_body_type = "html"
                
                context = {
                    "order_id": master_order_instance.pk,
                    "first_name": customer_instance.FirstName,
                    "full_name": customer_instance.FirstName + " " + customer_instance.LastName,
                    "phone_number": customer_instance.Phone_Number,
                    "email": customer_instance.Email,
                    "shipping_address": addrs,
                    "product_details": product_details,
                    "subtotal": round(master_order_instance.subtotal, 2),
                    "discount": round(master_order_instance.discount, 2),
                    "delivery_charge": round(master_order_instance.delivery_charge, 2),
                    "tax_details": tax_details,
                    "total_amount": round(master_order_instance.TotalAmount, 2),
                    "logo_url": f"{vendor_instance.logo.url}" if vendor_instance.logo else "",
                    "currency": vendor_instance.currency_symbol,
                }
                
                email_body = render_to_string('email.html', context)
                
                email_status = send_order_confirmation_email(sender, receiver, subject, email_body_type, email_body)

                email_log = EmailLog.objects.create(
                    order = master_order_instance,
                    sender = sender,
                    receiver = receiver,
                    subject = subject,
                    email_body_type = email_body_type,
                    email_body = email_body,
                    status = email_status,
                    customer = customer_instance,
                    vendor = vendor_instance
                )

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
