from rest_framework.decorators import api_view
from rest_framework.response import Response
from pos.views import order_data
from order.models import Address
from koms.models import Order as KOMSorder
from pos.models import StoreTiming, Banner
from nextjs.serializer import Userserializers
from order.serializer import Addressserializers, Customerserializers
from nextjs.models import *
from django.db.models import Q
from django.db import transaction
from core.utils import PaymentType
from order import order_helper
from core.models import Product, ProductModifier, ProductModifierGroup, Vendor, VendorSocialMedia
from pos.models import POSSetting
from pos.utils import get_product_by_category_data
from pos.language import (
    store_close_message_locale, product_out_of_stock_locale, modifier_group_out_of_stock_locale,
    modifier_out_of_stock_locale, product_no_longer_available_locale, modifier_no_longer_available_locale,
    valid_address_message_locale, delivery_address_validation_locale,
)
from django.http import JsonResponse
from datetime import datetime, timedelta
from rest_framework import status, viewsets
import requests
import socket



class userViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = Userserializers
    
    def update(self, request, *args, **kwargs):
        # partial = kwargs.pop('partial', False)
        # user = self.get_object()
        # serializer = self.get_serializer(user, data=request.data, partial=partial)
        # serializer.is_valid(raise_exception=True)
        
        # self.perform_update(serializer)

        data = request.data

        user = User.objects.filter(pk=data["id"]).first()

        # user.Customer.FirstName = data["FirstName"]
        # user.Customer.LastName = data["LastName"]
        # user.Customer.Email = data["Email"]
        # user.Customer.Phone_Number = data["Phone_Number"]
        user.profile_picture = request.FILES.get("profile_picture")

        user.save()
        
        userInfo = {}
        profile_picture = ""
        
        if user.profile_picture:
            port = request.META.get("SERVER_PORT")
            server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
            profile_picture = f"http://{server_ip}:{port}{user.profile_picture.url}" 
        
        userInfo["username"] = user.username
        userInfo["FirstName"] = user.Customer.FirstName
        userInfo["LastName"] = user.Customer.LastName
        userInfo["email"] = user.Customer.Email
        userInfo["Phone_Number"] = user.Customer.Phone_Number
        userInfo['profile_picture'] = profile_picture
        
        return Response({
            "id": user.pk,
            "token": user.token,
            "customer":user.Customer.pk,
            "userInfo": userInfo
        }, status=status.HTTP_200_OK)


@api_view(["POST"])
def login(request):
    try:
        vendorId=request.GET.get('vendorId')
        username = request.data.get("name")
        password = request.data.get("password")

        user = User.objects.filter(
            Q(Customer__Email=username) | Q(Customer__Phone_Number=username),
            password=password,
            vendor=vendorId
        ).first()

        if user :
            token = uuid4()

            user.token = token
            user.save()

            userInfo = {}

            profile_picture = ""

            if user.profile_picture:
                profile_picture = user.profile_picture.url
                port = request.META.get("SERVER_PORT")
                server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
                profile_picture = f"http://{server_ip}:{port}{user.profile_picture.url}" 

            userInfo['username'] = user.username
            userInfo['FirstName'] = user.Customer.FirstName
            userInfo['LastName'] = user.Customer.LastName
            userInfo['email'] = user.Customer.Email
            userInfo['Phone_Number'] = user.Customer.Phone_Number
            userInfo['profile_picture'] = profile_picture
            userInfo['loyalty_points_balance'] = user.Customer.loyalty_points_balance
            
            return Response({"id": user.pk, "token": token, "customer": user.Customer.pk, "userInfo": userInfo})
        
        else :
            return Response({"error":"Not found"}, status=400)  
    
    except:
        return Response({"error":"Not found"}, status=400)


@api_view(["POST"])
def register(request):
    vendorId=request.GET.get('vendorId')

    data_dict = {}

    data = request.data

    for key, value in data.items():
        data_dict[key] = value

    data = data_dict

    data['VendorId'] = vendorId
    data['vendor'] = vendorId
    data['loyalty_points_balance'] = 0

    customer_data = Customerserializers(data=dict(data))

    with transaction.atomic():
        if customer_data.is_valid():
            customer = customer_data.save()

            # profile_picture = request.FILES.get("profile_picture")

            data['username'] = f"{customer.FirstName or ''} {customer.LastName or ''}"
            data['token'] = uuid4()
            data['Customer'] = customer.pk
            # data['profile_picture'] = profile_picture if profile_picture else None

            user_data = Userserializers(data=data)

            if user_data.is_valid():
                user = user_data.save()
                return Response({"success": "Registered", "token": user.token})
            
            else :
                print("Could not register: ", user_data._errors)

                transaction.set_rollback(True)
                
                return Response({
                    "error message": user_data._errors,
                    "message": user_data._errors
                    },400)
            
        else :
            print("Could not register: ", customer_data._errors)

            transaction.set_rollback(True)
            
            return Response({
                "error message": customer_data._errors,
                "message": customer_data._errors
                },400)


@api_view(["POST"])
def updateUser(request):
    with transaction.atomic():
        data = request.data

        user = User.objects.filter(pk=data["id"])

        User.objects.filter(pk=data["id"]).update( username = f"{data['FirstName']} {data['LastName']}")

        customerData = Customerserializers(
            instance=user.first().Customer,
            partial=True,
            data={
                "FirstName": data["FirstName"],
                "LastName": data["LastName"],
                "Email": data["Email"],
            }
        )

        if customerData.is_valid():
            customerData.save()
            
            print(customerData._errors)

            if user.first():
                user = user.first()

                userInfo = {}

                profile_picture = ""

                if user.profile_picture:
                    profile_picture = user.profile_picture.url

                userInfo["username"] = user.username
                userInfo["FirstName"] = user.Customer.FirstName
                userInfo["LastName"] = user.Customer.LastName
                userInfo["email"] = user.Customer.Email
                userInfo["Phone_Number"] = user.Customer.Phone_Number
                userInfo['profile_picture'] = profile_picture
                
                return Response({"id": user.pk, "token": user.token,"customer":user.Customer.pk, "userInfo": userInfo})
        
        transaction.set_rollback(True)
        
        return Response("not found",400)   
    
    
@api_view(['POST'])
def check_order_items_status(request):
    vendor_id = request.GET.get('vendor', None)
    language = request.GET.get('language', 'English')

    if not vendor_id:
        return JsonResponse({"error": "Invalid Vendor ID"}, status=status.HTTP_400_BAD_REQUEST)
    
    order_details = request.data

    data = StoreTiming.objects.filter(vendor=vendor_id)

    slot = data.filter(is_active=True , day=datetime.now().strftime("%A")).first()

    store_status = POSSetting.objects.filter(vendor=vendor_id).first()

    if store_status.store_status == False:
        store_status = False

    else:
        if slot is None:
            store_status = True

        else:
            current_time = datetime.now().time()

            if (slot.open_time < current_time < slot.close_time) and not slot.is_holiday:
                store_status = True

            else:
                store_status = False
    
    if store_status == False:
        if language == "English":
            return JsonResponse({"msg": "Store is already closed"}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            return JsonResponse({"msg": store_close_message_locale}, status=status.HTTP_400_BAD_REQUEST)
    
    for item in order_details.get('items', []):
        product = Product.objects.filter(pk=item['productId']).first()

        if product and product.active == False:
            if language == "English":
                return JsonResponse({"msg": f"{product.productName} is out of stock"}, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                return JsonResponse({"msg": product_out_of_stock_locale(product.productName_locale)}, status=status.HTTP_400_BAD_REQUEST)

        for modifier_group in item['modifiersGroup']:
            
            modifier_group_instance = ProductModifierGroup.objects.filter(
                pk=modifier_group.get('modGroupId') or modifier_group.get('id')
            ).first()
            
            if modifier_group_instance and modifier_group_instance.active == False:
                if language == "English":
                    return JsonResponse(
                        {"msg": f"modifier group {modifier_group_instance.name} of {product.productName} is out of stock"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                else:
                    return JsonResponse(
                        {"msg": modifier_group_out_of_stock_locale(modifier_group_instance.name_locale, product.productName_locale)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            for modifier in modifier_group['modifiers']:
                if modifier["status"]:
                    modifier_instance = ProductModifier.objects.filter(pk=modifier['modifierId']).first()

                    if modifier_instance and modifier_instance.active == False:
                        if language == "English":
                            return JsonResponse(
                                {"msg": f"modifier {modifier_instance.modifierName} of {product.productName} is out of stock"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        else:
                            return JsonResponse(
                                {"msg": f"modifier {modifier_instance.modifierName} of {product.productName} is out of stock"},
                                {"msg": modifier_out_of_stock_locale(modifier_group_instance.name_locale, product.productName_locale)},
                                status=status.HTTP_400_BAD_REQUEST
                            )
    
    return Response({"success":True},status=status.HTTP_200_OK)


@api_view(['POST'])
def CreateOrder(request):
    vendorId = request.GET.get('vendorId', None)
    language = request.GET.get('language', 'English')

    if vendorId == None:
        return JsonResponse({"error": "Vendor Id cannot be empty"}, status=400, safe=False)
    
    data = StoreTiming.objects.filter(vendor=vendorId)

    slot = data.filter(day=datetime.now().strftime("%A")).first()

    store_status = False
    
    store_status_setting = POSSetting.objects.filter(vendor=vendorId).first()

    if store_status_setting:
        if store_status_setting.store_status == False:
            store_status = False

        elif slot is None:
            store_status = True

        elif slot.open_time < datetime.now().time() < slot.close_time and not slot.is_holiday:
            store_status = True

        else:
            store_status = False

    else:
        store_status = False

    if store_status == False:
        return JsonResponse({"msg": "store is already closed"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        orderid = '2' + datetime.now().strftime("%Y%m%d%H%M%S") + vendorId

        result = request.data
        
        result['internalOrderId'] = orderid
        result['externalOrderId'] = orderid
        result["platform"] = "Website"
        result["language"] = language
        result["payment"]["mode"] = PaymentType.CASH

        if result["payment"]['transcationId'] != "":
            result["payment"]['payConfirmation'] = result["payment"]['transcationId']
            result["payment"]["mode"] = PaymentType.ONLINE
            result["payment"]["platform"] = result["payment"]["payType"]
            result["payment"]["default"] = True

        for item in result['items']:
            product_instance = Product.objects.filter(pk=item['productId']).first()
            
            if (not product_instance) or (product_instance.active == False):
                if language == "English":
                    return JsonResponse(
                        {"msg": f"{product_instance.productName} is no longer available"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                else:
                    return JsonResponse(
                        {"msg": product_no_longer_available_locale(product_instance.productName_locale)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            modifiers_list = []

            for modifier_group in item['modifiersGroup']:
                for modifier in modifier_group['modifiers']:
                    modifier_instance = ProductModifier.objects.filter(pk=modifier["modifierId"], vendorId=vendorId).first()

                    if modifier_instance and modifier_instance.active == False:
                        if language == "English":
                            return JsonResponse(
                                {"msg": f"{modifier_instance.modifierName} is no longer available"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                            
                        else:
                            return JsonResponse(
                                {"msg": modifier_no_longer_available_locale(modifier_instance.modifierName_locale)},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    
                    modifier_info = {
                        "plu": modifier["plu"],
                        "name": modifier['name'],
                        "status": True,
                        "quantity": modifier["quantity"],
                        "group": modifier_group.get('modGroupId') or modifier_group.get('id')
                    }

                    modifiers_list.append(modifier_info)

            item["modifiers"] = modifiers_list
            
            item["subItems"] = item["modifiers"]
            item['itemRemark'] = 'None'

        res = order_helper.OrderHelper.openOrder(result, vendorId)
        
        if res[1] == 201:
            return JsonResponse({'token': res, "orderId": orderid})
        
        else:
            return JsonResponse({"msg": "something went wrong","res":res}, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        print(e)
        return JsonResponse({"msg": e}, status=status.HTTP_400_BAD_REQUEST)        

    
@api_view(['POST'])
def CreateOrderApp(request):
    vendorId = request.GET.get('vendorId', None)

    if vendorId == None:
        return JsonResponse({"error": "Vendor Id cannot be empty"}, status=400, safe=False)
    
    try:
        orderid = '2' + datetime.now().strftime("%Y%m%d%H%M%S") + vendorId

        result = request.data

        result['internalOrderId']  = orderid
        result['externalOrderId']  = orderid
        result["platform"] = "Mobile App"
        result["payment"]["mode"] = PaymentType.CASH
        
        if result["payment"]['transcationId'] != "":
            result["payment"]['payConfirmation'] = result["payment"]['transcationId']
            result["payment"]["mode"] = PaymentType.ONLINE
            result["payment"]["platform"] = result["payment"]["payType"]
            result["payment"]["default"] = True
        
        for item in result['items']:
            item["modifiers"] = [
                {
                    "plu": subItem["plu"],
                    "name": subItem['name'],
                    "status":True,
                    "quantity":subItem["quantity"],
                    "group": subItemGrp.get('modGroupId') or subItemGrp.get('id'),
                } for subItemGrp in item['modifiersGroup'] for subItem in subItemGrp['modifiers'] if subItem["status"]
            ]

            item["subItems"] = item["modifiers"]
            item['itemRemark'] = 'None'

        res = order_helper.OrderHelper.openOrder(result,vendorId)

        if res[1] == 201:
            return JsonResponse({'token': res, "orderId": orderid})
        
        else:
            return JsonResponse({"msg": "something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        print(e)
        return JsonResponse({"msg": e}, status=status.HTTP_400_BAD_REQUEST)        


@api_view(['GET'])
def get_timings(request):
    vendorId = request.GET.get('vendorId')

    data = StoreTiming.objects.filter(vendor=vendorId)

    slot = data.filter(day=datetime.now().strftime("%A")).first()

    delivery = []

    delivery_time = datetime.now() + timedelta(minutes=30)

    minute = delivery_time.minute

    minutes_to_add = 15 - (minute % 15)

    delivery_time = delivery_time + timedelta(minutes=minutes_to_add)
    # delivery_time = datetime.now()

    interval = 15

    close_time = slot.close_time if slot else  datetime.now().replace(hour=20, minute=0, second=0, microsecond=0).time()
    
    given_datetime = datetime.combine(datetime.today(), close_time)
    
    result_datetime = given_datetime - timedelta(minutes=interval)
    
    result_time = result_datetime.time()
    
    while delivery_time.time() < result_time:
        delivery_time = delivery_time + timedelta(minutes=interval)
        delivery.append({"time":delivery_time.strftime('%I:%M %p')})

    pickup = delivery

    # pickup = []

    # pickup_time = datetime.now()
    # while pickup_time.time() < close_time:
    #     interval = 30
    #     pickup_time += timedelta(minutes=interval)
    #     pickup.append({"time":pickup_time.strftime('%I:%M %p')})
    
    delivery_charges = 0

    delivery_settings = POSSetting.objects.filter(vendor=vendorId).first()
    
    if delivery_settings:
        delivery_charges = delivery_settings.delivery_charges_for_kilometer_limit

    return Response({"delivery": delivery, 'pickup': pickup, "flat_rate": delivery_charges})


@api_view(['POST'])
def set_customer_address(request):
    language = request.GET.get('language', 'English')
    vendorId = request.GET.get('vendorId')

    vendor = Vendor.objects.get(pk=vendorId)

    vendor_addr = f"{vendor.address_line_1} {vendor.city} {vendor.country}"

    id = request.GET.get('id', None)

    data = request.data

    addr = f"{data['address_line1']} {data['address_line2']} {data['city']} {data['state']} {data['state']}"

    distance = getDIstance(vendor_addr, addr)

    if distance == None:
        if language == "English":
            return Response(
                {"AddressError": "Please enter valid address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        else:
            return Response(
                {"AddressError": valid_address_message_locale},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    distance = getDIstance(vendor_addr, addr) / 1000

    delivery_settings = POSSetting.objects.filter(vendor=vendorId).first()

    kilometer_limit = 5
    
    if delivery_settings:
        kilometer_limit = delivery_settings.delivery_kilometer_limit
    
        if distance > kilometer_limit and kilometer_limit > 0 :
            if language == "English":
                return Response(
                    {"error": f"Delivery address is located more than {kilometer_limit} kilometers away"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            else:
                return Response(
                    {"error": delivery_address_validation_locale(kilometer_limit)},
                    status=status.HTTP_400_BAD_REQUEST
                )
    
    serealizer = Addressserializers(data=data)
    
    if id:
        serealizer = Addressserializers(data=data,instance=Address.objects.get(pk=id))

    else :
        Address.objects.filter(customer=data['customer']).update(is_selected=False)

    if serealizer.is_valid() :
        save = serealizer.save()
        instance=Address.objects.filter(customer=save.customer.pk)

        return Response(Addressserializers(instance=instance, many=True).data)
    
    else :
        return Response(serealizer._errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_customer_address(request):
    vendorId=request.GET.get('vendorId')
    id = request.GET.get('id',None)
    user = User.objects.get(pk=id)
    instance=Address.objects.filter(customer=user.Customer.pk)
    return Response(Addressserializers(instance=instance,many=True).data)


@api_view(['GET','DELETE'])
def delete_customer_address(request):
    vendorId=request.GET.get('vendorId')
    addr = Address.objects.filter(pk=request.GET.get('id',None))
    cust = addr.first().customer.pk
    addr.delete()
    instance=Address.objects.filter(customer=cust)
    return Response(Addressserializers(instance=instance,many=True).data)


@api_view(['POST'])
def select_address(request):
    vendorId=request.GET.get('vendorId')
    data =request.data
    Address.objects.filter(customer=data.get('customer')).update(is_selected=False)
    Address.objects.filter(pk=data.get('adddress_id')).update(is_selected=True)
    # return Response({"id":data.get('adddress_id')})
    return Response(Addressserializers(instance=Address.objects.get(pk=data.get('adddress_id'))).data)


@api_view(['GET'])
def getTags(request):
    vendorId=request.GET.get('vendorId')
    products = Product.objects.filter(vendorId = vendorId)
    tagSet = []
    for i in products :
        tagSet.append(i.tag)
    return Response(list(set(tagSet)))


def getDIstance(source,destination):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={source}&destinations={destination}&key=AIzaSyBpil2D8QGyYQaxh-kcy_XuYWooNYb_eiE"
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    data = response.json()
    if data['rows'][0]['elements'][0]['status'] == "OK":
        return data['rows'][0]['elements'][0]['distance']['value']
    else:
        None


@api_view(['GET'])
def getOrderData(request):
    vendorId = request.GET.get('vendorId')
    orderId = request.GET.get('orderId')
    order = KOMSorder.objects.filter(master_order__externalOrderId = orderId)
    data = order_data(vendor_id=vendorId, page_number=1, search=str(order.first().externalOrderId), order_status="All", order_type="All", platform="All", is_dashboard=0, s_date=None, e_date=None)
    return Response(data)


@api_view(['GET'])
def get_points(request):
    customer = Customer.objects.get(pk=request.GET.get('customer'))
    return Response({"loyalty_points_balance": customer.loyalty_points_balance})


@api_view(['GET'])
def verify_address(request):
    language = request.GET.get('language', 'English')
    vendorId = request.GET.get('vendorId')

    vendor = Vendor.objects.get(pk=vendorId)

    vendor_addr = f"{vendor.address_line_1}_{vendor.city}_{vendor.country}"

    addr = request.GET.get('destination')

    distance = getDIstance(vendor_addr,addr)

    if distance == None:
        if language == "English":
            return Response({"AddressError": f"Please enter valid address"})
        
        else:
            return Response({"AddressError": valid_address_message_locale})
    
    distance = getDIstance(vendor_addr, addr) / 1000

    delivery_settings = POSSetting.objects.filter(vendor=vendorId).first()
    
    kilometer_limit = 5
    
    if delivery_settings:
        kilometer_limit = delivery_settings.delivery_kilometer_limit
    
    if (distance > kilometer_limit) and (kilometer_limit > 0):
        if language == "English":
            return Response({"error": f"Delivery address is located more than {kilometer_limit} kilometers away"})
        
        else:
            return Response({"error": delivery_address_validation_locale(kilometer_limit)})
    
    return Response({"success": kilometer_limit})


@api_view(["GET"])
def get_banner(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language", "English")

        if not vendor_id:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor_id = int(vendor_id)
            
        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)
        
        banner_list = []
        
        platform_type = request.GET.get("platform_type")
        
        if platform_type:
            if platform_type == "app" or platform_type == "website":
                banners = Banner.objects.filter(is_active=True, vendor=vendor_id, platform_type=platform_type)

            else:
                return Response("Invalid platform type", status=status.HTTP_400_BAD_REQUEST)

        if banners:
            for banner in banners:
                banner_list.append(f"{banner.image}")
        
        product_type = ["recommendation", "todays_special"]

        recommendation_list = []
        todays_special_list = []

        for type in product_type:
            product_list = []

            if type == "recommendation":
                products = Product.objects.filter(is_in_recommendations=True, vendorId=vendor_id)
                
            elif type == "todays_special":
                products = Product.objects.filter(is_todays_special=True, vendorId=vendor_id)
                        
            if products:
                product_list = get_product_by_category_data(products, language, vendor_id)

                if type == "recommendation":
                    recommendation_list = product_list

                elif type == "todays_special":
                    todays_special_list = product_list
        
        return JsonResponse({
            "banners": banner_list,
            "recommendations": recommendation_list,
            "todays_special": todays_special_list
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
def get_header_footer_section(request):
    try:
        vendor_id = request.GET.get("vendorId")
        # language = request.GET.get("language")

        vendor = Vendor.objects.filter(pk=vendor_id)

        if not vendor.exists():
            return Response("vendor not found", status=status.HTTP_400_BAD_REQUEST)
        
        vendor = Vendor.objects.filter(pk=vendor_id).first()

        contact_details = {
            "phone": vendor.phone_number,
            "address": f"{vendor.address_line_1} , {vendor.city} , {vendor.country}",
            "email": vendor.Email,
        }

        languageDetails = [vendor.primary_language, vendor.secondary_language]

        social_media_icons = []

        for social in VendorSocialMedia.objects.filter(vendor=vendor_id):
            social_media_icons.append({
                "link": social.link,
                "name": social.name,
                "social_media_handle_name": social.name
            })
            
        data = {
            "logo": vendor.logo.url if vendor.logo else "",
            "contact_details": contact_details,
            "social_media_icons": social_media_icons,
            "languageDetails": languageDetails,
            "currency": vendor.currency,
            "currency_symbol": vendor.currency_symbol,
        }

        return Response(data)
    
    except Exception as e:
        return Response(f"{str(e)}", status=status.HTTP_400_BAD_REQUEST)

    
@api_view(["GET"])
def get_homepage_content(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language","English")
        if not vendor_id:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        data = AboutUsSection.objects.filter(vendor = vendor_id)
        if not data.exists():
            aboutSection = {}
        else:
            data = data.first()
            aboutSection = {
                "sectionImage": data.sectionImage,
                "sectionHeading": data.sectionHeading if language == "English" else data.sectionHeading_locale,
                "sectionSubHeading":data.sectionSubHeading if language == "English" else data.sectionSubHeading_locale,
                "sectionDescription": [data.sectionDescription if language == "English" else data.sectionDescription_locale],
            }
        
        data = SectionTwoCoverImage.objects.filter(vendor = vendor_id)
        if not data.exists():
            sectionTwoCoverImage = {}
        else:
            data = data.first()
            sectionTwoCoverImage = {
                "sectionImage":data.sectionImage,
                "sectionText": data.sectionText if language == "English" else data.sectionText_locale,
                "buttonText": data.buttonText if language == "English" else data.buttonText_locale,
            }
            
        data = FeaturesSection.objects.filter(vendor=vendor_id)
        if not data.exists():
            featuresSection = {}
        else:
            data = data.first()
            featuresSection = {
                "headingText": data.headingText if language == "English" else data.headingText_locale,
                "subHeadingText": data.subHeadingText if language == "English" else data.subHeadingText_locale,
            }
            featuresArray = []
            for item in FeaturesSectionItems.objects.filter(featuresSection=data.pk):
                featuresArray.append({
                        "featureId": item.pk,
                        "featureIcon": item.featureIcon,
                        "featureHeading": item.featureHeading if language == "English" else item.featureHeading_locale,
                        "featurePara": item.featurePara if language == "English" else item.featurePara_locale,
                    })
            featuresSection['featuresArray'] = featuresArray
            
        data = TestimonialsSection.objects.filter(vendor = vendor_id)
        if not data.exists():
            testimonialsSection = {}
        else:
            data = data.first()
            testimonialsSection = {
                "sectionHeading": data.sectionHeading if language == "English" else data.sectionHeading_locale,
                "sectionSubHeading": data.sectionSubHeading if language == "English" else data.sectionSubHeading_locale,
            }
            testimonials = []
            for item in TestimonialsSectionItems.objects.filter(testimonialsSection=data.pk):
                testimonials.append({
                        "testimonialId": item.pk,
                        "testimonialsImageUrl": item.testimonialsImageUrl,
                        "testimonialsName": item.testimonialsName if language == "English" else item.testimonialsName_locale,
                        "testimonialsReview": item.testimonialsReview if language == "English" else item.testimonialsReview_locale,
                    })
            testimonialsSection['testimonials'] = testimonials
                
        all_data = HomePageOfferSection.objects.filter(vendor = vendor_id)
        if not all_data.exists():
            homePageOffersSection =[]
        else:
            homePageOffersSection =[{
                "offerId": data.pk,
                "discountTextColor": data.discountTextColor,
                "offerDiscountText":data.offerDiscountText if language == "English" else data.offerDiscountText_locale,
                "offerImage": data.offerImage,
                "offerTitle": data.offerTitle if language == "English" else data.offerTitle_locale,
                "offerDescription": data.offerDescription if language == "English" else data.offerDescription_locale,
                "buttonLocation": data.buttonLocation,
            } for data in all_data]
        
        return Response({
            "aboutSection":aboutSection,
            "sectionTwoCoverImage":sectionTwoCoverImage,
            "featuresSection":featuresSection,
            "testimonialsSection":testimonialsSection,
            "homePageOffersSection":homePageOffersSection
        })
    except Exception as e:
        return Response(f"{e}", status=status.HTTP_400_BAD_REQUEST)
