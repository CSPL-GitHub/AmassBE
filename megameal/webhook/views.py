from datetime import datetime
import json
from django.shortcuts import render
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.parsers import JSONParser
from core.POS_INTEGRATION.staging_pos import StagingIntegration
from core.POS_INTEGRATION.square_pos import SquareIntegration
from core.PLATFORM_INTEGRATION.woocommerce_ecom import WooCommerce
from koms.views import waiteOrderUpdate
from koms.models import Order as KOMSorder
from order.models import Order, OrderPayment, OriginalOrder, Customer, Address
from order.order_helper import OrderHelper
from core.utils import API_Messages, OrderStatus, PaymentType,UpdatePoint
from core.models import POS_Settings, Vendor
from django.http import HttpResponse, JsonResponse
from rest_framework import status



def background_process(vendorId):
    try:
        stagingPos = StagingIntegration()
        return stagingPos.pullProducts({"vendorId": vendorId})
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")

def backgroundWooCommerceOrder(data,vendorId):
    response=WooCommerce.openOrder(request=data, vendorId=vendorId)
    rs=OrderHelper.openOrder(data=response,vendorId=vendorId)
    # print(rs)

@api_view(["POST"])
def RazorPayUpdate(request):
    body_data = json.loads(request.body)

    orderId = body_data.get('externalRefNumber')
    paymentBy = body_data.get('customerName')
    paymentKey = body_data.get('txnId')
    paid = body_data.get('amount')
    type = body_data.get('paymentMode')
    status = body_data.get('status')

    try:
        payment_obj = OrderPayment.objects.get(paymentKey=paymentKey)

        if payment_obj:
            if status == 'AUTHORIZED':
                status = True
            else:
                status = False
            
            payment_obj.status = status
            payment_obj.save()

            return HttpResponse("Success!", status=200)

    except Exception as e:
        print("ezetap webhook error: ", e)

        try:
            orderId = Order.objects.get(pk=orderId)

            if status == 'AUTHORIZED':
                status = True
            else:
                status = False

            if type == 'CARD':
                type = 3
            elif type == 'CASH':
                type = 1

            payment_obj = OrderPayment.objects.create(orderId=orderId, paymentBy=paymentBy, paymentKey=paymentKey, paid=paid, type=type, status=status, due=0.0, tip=0.0, platform="Ezetap Machine")

            if payment_obj:
                return HttpResponse("Success!", status=200)

        except Exception as e:
            print("ezetap webhook error: ", e)
            return HttpResponse("Failure!", status=400)
    
@api_view(["GET", "POST"])
def testjson(request):
    todaydate = datetime.today().date()
    print(str(todaydate))
    jsonData = dict(JSONParser().parse(request))
    apidist = {
        "orderId": "6246",
        "orderType": 1,
        "pickupTime": "2022-02-02T10:40:00",
        "arrivalTime": str(todaydate)+"T10:30:00",
        "deliveryIsAsap": True,
        "note": "Make it fast",
        "items": '',
        "remake": False,
        "customerName": "MD1",
        "status": "pending",
        "orderPointId": 1
    }
    print(apidist)
    res = {}
    itemslist = []
    for hotelName in jsonData:
        d = {}
        for categories in jsonData[hotelName]['items'][0]['entries']['items']:
            li = []
            for itemDetail in categories['entries']['items']:
                custdict = {
                    "plu": "CMB-02",
                    "name": itemDetail['name'],
                    "quantity": 10,
                    "tag": 1,
                    "subItems": [],
                    "itemRemark": itemDetail['description'],
                    "unit": "qty"
                }
                li.append(custdict)
            d[categories['name']] = li
        itemslist.append(d)
    res['items'] = itemslist
    newRecords = []
    for categories in res["items"]:
        apidist["items"] = categories
        sent = requests.post("http://127.0.0.1:8080/saveOrder/", json=apidist)
        newRecords.append(sent.json())
    return Response(newRecords)


@api_view(['post'])
def squareMenuWebhook(request, vendorId=-1):
    print("Menu Sync Webhook")
    coreResponse = {
        "status": "successful",
        "msg": "successful",
        "response": {}
    }

    try:

        # ++++++++++ request data
        data = dict(JSONParser().parse(request))

        posSettings = POS_Settings.objects.get(VendorId=vendorId)
        if posSettings.meta:
            begin_time = posSettings.meta.get("begin_time")
            if not begin_time:
                current_datetime = datetime.utcnow()
                begin_time = current_datetime.isoformat() + "Z"
                posSettings.meta["begin_time"] = begin_time
                posSettings.save()
        else:
            print("No meta found for POS")
            return

        # +++++++++ Category processx
        catlogHeaders = {
            "Authorization": "Bearer "+posSettings.secreateKey,
            "Content-Type": "application/json",
            "Square-Version": "2023-06-08"
        }
        payload = {
            "begin_time": begin_time,
            "include_deleted_objects": True,
            "object_types": [
                "ITEM",
                "CATEGORY",
                "PRODUCT_SET",
                "ITEM_VARIATION",
                "MODIFIER_LIST",
                "MODIFIER",
                "ITEM_OPTION",
                "ITEM_OPTION_VAL"
            ]
        }
        payload = json.dumps(payload)
        url = posSettings.baseUrl + "/v2/catalog/search"
        catlogResponse = requests.request(
            "POST", url, headers=catlogHeaders, data=payload)
        if catlogResponse.status_code in [500, 400]:
            coreResponse["msg"] = "Unable to connect Square"
            coreResponse["response"] = catlogResponse.json()
            return Response(coreResponse, status=200)

        body = catlogResponse.json()
        print(body)
        responseBody = {
            "category": {},
            "products": {},
            "varinats": {},
            "modGrpPrdJoint": {},
            "modifiersGroup": {},
            "modifiers": {},
            "productOptions": {},
            "productOptionsVal": {}
        }

        
        stage = StagingIntegration()
        if body.get("objects"):
            listOfCatalog = body.get("objects")
            listCategory = []
            listProduct = []
            listVariant = {}
            listModGrp = []
            listModItm = []
            listModGrpPrd = {}
            listOpt = []
            listOptVal = []

            for catalog in listOfCatalog:
                if catalog["type"] == "CATEGORY":
                    listCategory.append(
                        SquareIntegration.convertCategory(vendorId, catalog))
                elif catalog["type"] == "ITEM":
                    extData = SquareIntegration.convertProduct(
                        vendorId, catalog, catlogHeaders, posSettings)
                    prd = next(iter(extData["products"].values()))
                    listProduct.append(prd)
                    listVariant.update(extData["varinats"])
                    listModGrpPrd.update(
                        extData["modifierGroupAndProductJoint"])
                elif catalog["type"] == "MODIFIER_LIST":
                    listModGrp.append(
                        SquareIntegration.convertModifierGroup(vendorId, catalog))
                elif catalog["type"] == "MODIFIER":
                    listModItm.append(
                        SquareIntegration.convertModifier(vendorId=vendorId, catalogObject=catalog, catlogHeaders=catlogHeaders, platform=posSettings))
                elif catalog["type"] == "ITEM_OPTION":
                    listOpt.append(
                        SquareIntegration.convertOption(vendorId, catalog))
                elif catalog["type"] == "ITEM_OPTION_VAL":
                    listOptVal.append(
                        SquareIntegration.convertOptionVal(vendorId, catalog))

            responseBody = {
                "listCategory": listCategory,
                "listProduct": listProduct,
                "listVariant": listVariant,
                "listModGrp": listModGrp,
                "listModItm": listModItm,
                "listModGrpPrd": listModGrpPrd,
                "listOpt": listOpt,
                "listOptVal": listOptVal
            }

            for extData in listCategory:
                if extData["isDeleted"] == True:
                    stage.deleteCategory(
                        coreCat=extData, vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateCategory(
                        coreCat=extData, vendor=posSettings.VendorId)

            for extData in listProduct:
                if extData["isDeleted"] == True:
                    stage.deleteProduct(
                        corePrd=extData, vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateProduct(
                        corePrd=extData, vendor=posSettings.VendorId)

            for extData in listOpt:
                if extData["isDeleted"] == True:
                    stage.deleteOption(corePrdOptions=extData,
                                       vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateOption(
                        corePrdOptions=extData, vendor=posSettings.VendorId)

            for extData in listOptVal:
                if extData["isDeleted"] == True:
                    stage.deleteOptionValue(
                        corePrdOptVal=extData, vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateOptionValue(
                        corePrdOptVal=extData, vendor=posSettings.VendorId)

            for value in listVariant.values():
                if value["isDeleted"] == True:
                    stage.deleteVariant(
                        coreVrt=value, vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateVariant(
                        coreVrt=value, vendor=posSettings.VendorId)

            for extData in listModGrp:
                if extData["isDeleted"] == True:
                    stage.deleteModifierGroup(
                        coreModGrp=extData, vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateModifierGroup(
                        coreModGrp=extData, vendor=posSettings.VendorId)

            for extData in listModItm:
                if extData["isDeleted"] == True:
                    stage.deleteModifierItem(
                        coreModItm=extData, vendor=posSettings.VendorId)
                else:
                    stage.saveUpdateModifierItem(
                        coreModItm=extData, vendor=posSettings.VendorId)

            for extData in listModGrpPrd:
                stage.saveUpdateDeleteModifierGroupProductJoint(
                    productId=extData, coreModGrpPrdJnt=listModGrpPrd[extData], vendor=posSettings.VendorId)

        # ++++++ After Updating the Menu Just update the update time
        current_datetime = datetime.utcnow()
        begin_time = current_datetime.isoformat() + "Z"
        posSettings.meta["begin_time"] = begin_time
        posSettings.save()
        # ++++++++

        return Response(responseBody, 200)
    except Exception as err:
        msg = f"Unexpected {err=}, {type(err)=}"
        coreResponse["status"] = "Error"
        coreResponse["msg"] = msg
        print(coreResponse)
        return Response(coreResponse, status=200)

@api_view(['post'])
def squareOrderWebhook(request,vendorId=-1):
    # +++++ response template
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }
    try:
        # ++++++++++ request data
        data = dict(JSONParser().parse(request))

        orderId=data["data"]["object"]["order_updated"]["order_id"]
        state=data["data"]["object"]["order_updated"]["state"]
        if state=="COMPLETED":
            originalOrder = OriginalOrder.objects.exclude(externalOrderId="NA").filter(
                vendorId=vendorId,
                platformName=SquareIntegration.platFormName,
                externalOrderId=orderId).first()
            rs=OrderHelper.orderStatusUpdate(data={
                "status":state,
                "orderId":originalOrder.orderId.pk,
                "vendorId":vendorId,
                "updatePoint":UpdatePoint.POS
                },vendorId=vendorId)
            return Response({API_Messages.STATUS:API_Messages.SUCCESSFUL},200)
    except Exception as err:
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=200)

@api_view(['post'])
def wooComerceOrderWebhook(request,vendorId=-1):
    # +++++ response template
    print("WOOCOMMERCE Order++++++++++++++++++++++++++++++")
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }
    try:
        # ++++++++++ request data
        data = dict(JSONParser().parse(request))
        import threading
        wooOrderThread = threading.Thread(target=backgroundWooCommerceOrder, args=(), kwargs={"vendorId":vendorId,"data":data})
        wooOrderThread.setDaemon(True)
        wooOrderThread.start()
        return Response({API_Messages.STATUS:API_Messages.SUCCESSFUL},200)
        #return Response(rs[0], status=200)
    except Exception as err:
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=200)

@api_view(['post'])
def wooComerceOrderUpdateWebhook(request,vendorId=-1):
    # +++++ response template
    print("WOOCOMMERCE Order update++++++++++++++++++++++++++++++")
    print(request.data)
    print(vendorId)
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }
    try:
        # ++++++++++ request data
        # data = json.loads(request.body)
        print("status 1")
        data = request.data
        print("status 1")
        
        if data.get("status"):
            if data.get("status") != "completed":
                order = Order.objects.get(vendorId_id=vendorId,externalOrderld=data.get("id"))
                # if data.get("status")=="completed" or data.get("status")=="cancelled" or data.get("status")=="failed":
                # if data.get("status") in ("completed", "cancelled", "processing", "failed"):
                if data.get("status") in ("cancelled", "processing", "failed"):
                    print(data.get("status"))

                    status = OrderStatus.CANCELED.label
                    
                    # if data.get("status") == "completed":
                    #     status = OrderStatus.COMPLETED.label
                    if data.get("status") == "processing":
                        status = OrderStatus.OPEN.label
                    
                    rs=OrderHelper.orderStatusUpdate(data={
                    "status":status,
                    "orderId":order.pk,
                    "vendorId":vendorId,
                    "updatePoint":UpdatePoint.WOOCOMERCE
                    },vendorId=vendorId)

                    print(rs)

                payment = OrderPayment.objects.filter(orderId=order.pk)

                if payment:
                    payment.update(paymentKey=request.data.get("transaction_id"))
                    if request.data.get("transaction_id"):
                        payment.update(type=PaymentType.ONLINE, status=True)
                    else:
                        if request.data.get("payment_method") == "cod":
                            payment.update(type=PaymentType.CASH, status=True)

                koms_orderId = KOMSorder.objects.get(externalOrderId=order.pk)
                
                waiteOrderUpdate(orderid=koms_orderId.pk,vendorId=vendorId)

        return Response({API_Messages.STATUS:API_Messages.SUCCESSFUL},200)
    
    except Order.DoesNotExist:
        print("not found order")
        coreResponse["msg"] = "Order not found of given Id"
        return Response(coreResponse, status=200)
    
    except Exception as err:
        print(err)
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=200)
    

@api_view(["POST"])
def create_customer_webhook(request):
    vendor_id = request.GET.get('vendorId', None)
    print(vendor_id)
    
    if vendor_id is None:
        return JsonResponse({"error": "Vendor ID empty"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    vendor_id = int(vendor_id)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return JsonResponse({"error": "Vendor does not exist"}, status=status.HTTP_400_BAD_REQUEST, safe=False)

    data = request.data
    print(data)

    billing_details = data.get("billing", None)

    if not billing_details:
        return JsonResponse({"error": "'billing' key not found in requst body"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    phone_number = billing_details.get("phone", None)

    if not phone_number:
        return JsonResponse({"error": "'phone' key not found in requst body"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    existing_customer = Customer.objects.filter(Phone_Number=phone_number, VendorId=vendor_id).first()

    if existing_customer:
        return JsonResponse({"error": "Customer with this mobile number already exists"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    first_name = data.get("first_name", None)
    last_name = data.get("last_name", None)
    email = data.get("email", None)

    customer_instance = Customer.objects.create(
        FirstName=first_name,
        LastName=last_name,
        Email=email,
        Phone_Number=phone_number,
        VendorId=vendor
    )
    
    address_line_1 = billing_details.get("address_1", None)
    address_line_2 = billing_details.get("address_2", None)
    city = billing_details.get("city", None)
    state = billing_details.get("state", None)
    country = billing_details.get("country", None)
    zipcode = billing_details.get("postcode", None)

    if any((address_line_1, address_line_2, city, state, country, zipcode)):
        Address.objects.create(
            address_line1=address_line_1,
            address_line2=address_line_2,
            city=city,
            state=state,
            country=country,
            zipcode=zipcode,
            type="shipping_address",
            is_selected=True,
            customer=customer_instance
        )

    return JsonResponse({"success": "Customer created"}, status=status.HTTP_200_OK, safe=False)


@api_view(["POST"])
def update_customer_webhook(request):
    vendor_id = request.GET.get('vendorId', None)
    print(vendor_id)
    
    if vendor_id is None:
        return JsonResponse({"error": "Vendor ID empty"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    vendor_id = int(vendor_id)

    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return JsonResponse({"error": "Vendor does not exist"}, status=status.HTTP_400_BAD_REQUEST, safe=False)

    data = request.data
    print(data)

    billing_details = data.get("billing", None)

    if not billing_details:
        return JsonResponse({"error": "'billing' key not found in requst body"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    phone_number = billing_details.get("phone", None)

    if not phone_number:
        return JsonResponse({"error": "'phone' key not found in requst body"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    customer = Customer.objects.filter(Phone_Number=phone_number, VendorId=vendor_id).first()

    if not customer:
        return JsonResponse({"error": "Customer with this mobile number does not exist"}, status=status.HTTP_400_BAD_REQUEST, safe=False)
    
    first_name = data.get("first_name", None)
    last_name = data.get("last_name", None)
    email = data.get("email", None)

    customer.FirstName = first_name
    customer.LastName = last_name
    customer.Email = email
    customer.Phone_Number = phone_number

    customer.save()

    address_line_1 = billing_details.get("address_1", None)
    address_line_2 = billing_details.get("address_2", None)
    city = billing_details.get("city", None)
    state = billing_details.get("state", None)
    country = billing_details.get("country", None)
    zipcode = billing_details.get("postcode", None)

    if any((address_line_1, address_line_2, city, state, country, zipcode)):
        address_instance = Address.objects.filter(customer=customer.pk, type="shipping_address", is_selected=True).first()

        if address_instance:
            address_instance.address_line1 = address_line_1
            address_instance.address_line2 = address_line_2
            address_instance.city = city
            address_instance.state = state
            address_instance.country = country
            address_instance.zipcode = zipcode

            address_instance.save()

        else:
            Address.objects.create(
                address_line1=address_line_1,
                address_line2=address_line_2,
                city=city,
                state=state,
                country=country,
                zipcode=zipcode,
                type="shipping_address",
                is_selected=True,
                customer=customer
            )

    return JsonResponse({"success": "Customer details updated"}, status=status.HTTP_200_OK, safe=False)
