import json
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from core.POS_INTEGRATION.abstract_pos_integration import AbstractPOSIntegration
from core.POS_INTEGRATION.staging_pos import StagingIntegration
from core.POS_INTEGRATION.square_pos import SquareIntegration
from core.PLATFORM_INTEGRATION.koms_order import KomsEcom
from koms.views import createOrderInKomsAndWoms
from core.utils import CorePlatform, OrderStatus, UpdatePoint
from order.models import Order, Customer, OrderPayment, LoyaltyProgramSettings, LoyaltyPointsCreditHistory, LoyaltyPointsRedeemHistory
from order import order_helper
from core.utils import API_Messages
from core.models import POS_Settings, Vendor, Product, ProductCategoryJoint, ProductModifier, ProductModifierGroup
from koms.models import Station
from koms.models import Order as KOMSOrder
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import status
import pytz
import requests


@api_view(['post'])
def openOrder(request):
    # +++++ response template
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }
    try:
        # ++++++++++ request data
        data = dict(JSONParser().parse(request))
        vendorId = data["vendorId"]
        # ++++ pick all the channels of vendor
        rs=order_helper.OrderHelper.openOrder(data=data,vendorId=vendorId)
        return Response(rs[0], status=rs[1])
    except Exception as err:
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=500)


@api_view(['post'])
def addLineItem(request):
    # +++++ response template
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }

    try:
        # ++++++++++ request data
        data = dict(JSONParser().parse(request))
        vendorId = data["vendorId"]

        # ++++ pick all the channels of vendor
        try:
            platform = POS_Settings.objects.get(VendorId=vendorId)
        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return Response(coreResponse, status=200)

        # ++++++---- Stage The Order
        stagingPos = StagingIntegration()
        stageOrder = stagingPos.addLineItem(data)
        if stageOrder[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
            posService = globals()[platform.className]
            posResponse = posService.addLineItem(data)
            if posResponse[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                posResponse["response"]["core"] = stageOrder["response"]
                return Response(posResponse, status=201)
            else:
                coreResponse["msg"] = "Unable to create order on POS"
                return Response(coreResponse, status=500)
        else:
            coreResponse["msg"] = "Unable to update product"
            return Response(coreResponse, status=500)

    except Exception as err:
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=500)


@api_view(['post'])
def addModifier(request):
    stagingPos = StagingIntegration()
    return stagingPos.addModifier(request)


def applyDiscount(request):
    pass


@api_view(['post'])
def payBill(request):
    # +++++ response template
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }

    try:
        # ++++++++++ request data
        data = dict(JSONParser().parse(request))
        vendorId = data["vendorId"]

        # ++++ pick all the channels of vendor
        try:
            platform = POS_Settings.objects.get(VendorId=vendorId)
        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return Response(coreResponse, status=404)

        # ++++++---- Stage The Order
        stagingPos = StagingIntegration()
        stageOrder = stagingPos.payBill(data)
        if stageOrder[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
            posService = globals()[platform.className]
            posResponse = posService.payBill(data)
            if posResponse[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                posResponse["response"]["core"] = stageOrder["response"]
                return Response(posResponse, status=201)
            else:
                return Response(posResponse, status=500)
        else:
            coreResponse["msg"] = stageOrder["msg"]
            return Response(coreResponse, status=500)

    except Exception as err:
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=500)


def createTicket(request):
    pass


@api_view(["POST"])
def updateOrderStatusFromKOMS(request):
     # +++++ response template
    coreResponse = {
        API_Messages.STATUS: API_Messages.ERROR,
        "msg": "Something went wrong"
    }
    try:
        # ++++++++++ request data
        data = dict(JSONParser().parse(request))
        vendorId = data["vendorId"]
        data["updatePoint"]=UpdatePoint.KOMS
        # ++++ pick all the channels of vendor
        rs=order_helper.OrderHelper.orderStatusUpdate(data=data,vendorId=vendorId)
        return Response(rs[0], status=rs[1])
    except Exception as err:
        coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return Response(coreResponse, status=500)
    

@api_view(['post'])
def womsCreateOrder2(request):
    vendorId=request.GET.get("vendorId")
    data = JSONParser().parse(request)
    print(json.dumps(data))
    res = {
        "orderId": "1234" + datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H%M%S"),
        "orderType": 1,
        "arrivalTime": f"{str(datetime.today().date())}T{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')}",
        "pickupTime": f"{str(datetime.today().date())}T{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')}",
        "deliveryIsAsap": True,
        "note": "",
        "tableNo": data['tables'],
        "items": {},
        "remake": False,
        "customerName": "MD1",
        "status": 1,
        "server": ', '.join(str(item['waiterName']) for item in data['tables']),
        "orderPointId": 1,
        "isHigh": True if data["priority"] else False,
        "note":  data["productNote"] if data["productNote"] else "note" 
    }

    #########
    totalPrepTime=0
    for index,itemData in enumerate(data['products']):
        timeData=getPrepTime(plu=itemData["plu"],vendorId=vendorId)
        data['products'][index]["prepTime"]=timeData["prepTime"]
        data['products'][index]["tag"]=timeData["tag"]
        totalPrepTime= totalPrepTime+data['products'][index]["prepTime"]
    res["totalPrepTime"]=totalPrepTime
    
    if totalPrepTime>0:
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        new_time = current_time + timedelta(minutes=totalPrepTime)
        res["pickupTime"]=f"{str(datetime.today().date())}T{new_time.strftime('%H:%M:%S')}"
    ##############

    itemCategories = list(set(i['categoryName'] for i in data['products']))
    for item in itemCategories:
        res['items'][item] = [
            {
                "plu": i['plu'],
                "name": i['text'],
                "quantity": i['quantity'],
                "tag": i['tag'],
                "subItems": [
                    {
                        "plu": subItem['plu'],
                        "name": subItem['name'],
                        "status":subItem["status"]
                    } for subItemGrp in i['modifiersGroup'] for subItem in subItemGrp['modifiers']
                ],
                "itemRemark": i["note"],
                "unit": 'qty',
                "prepTime": i['prepTime']
            } for i in data['products'] if i['categoryName'] == item
        ]

    try:
        res["vendorId"]=vendorId
        response=createOrderInKomsAndWoms(res)
        return JsonResponse(response,status= status.HTTP_200_OK if response[API_Messages.STATUS]==API_Messages.SUCCESSFUL else status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        return JsonResponse(
            {   API_Messages.STATUS:API_Messages.ERROR,
                API_Messages.RESPONSE: f"Unexpected {e=}, {type(e)=}" }, 
                status=status.HTTP_400_BAD_REQUEST
        )



def getPrepTime(plu,vendorId):
    try:
        prd=ProductCategoryJoint.objects.get(product=Product.objects.get(PLU=plu,vendorId=vendorId))
        return {"prepTime":prd.product.preparationTime,"tag":prd.category.categoryStation.pk if prd.category.categoryStation else 1}
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        prd=ProductCategoryJoint.objects.get(product=Product.objects.filter(PLU=plu).first())
        # return {"prepTime":0,"tag":}[]
        stn=Station.objects.filter(station_name=prd.category.categoryStation.station_name,vendorId=vendorId).first()
        return {"prepTime":prd.product.preparationTime,"tag":stn.pk}
    
@api_view(['post'])
def womsCreateOrder(request):
    vendorId = request.GET.get('vendorId', None)

    if vendorId == None:
        return JsonResponse({"error": "Vendor Id cannot be empty"}, status=400, safe=False)
    
    try:
        orderid=str(CorePlatform.POS)+datetime.now().strftime("%H%M%S")
        result = {
                "internalOrderId": orderid,
                "vendorId": vendorId,
                "externalOrderId":orderid,
                # "orderType": request.data.get("type", "DINEIN" ),
                "orderType":"DINEIN",
                "pickupTime": '',
                "arrivalTime": '',
                "deliveryIsAsap": 'true',
                "note": request.data.get('productNote'),
                "tables": request.data.get('tables'),
                "items": [],
                "remake": False,
                "customerName": request.data.get('name') if request.data.get('name') else "test",
                "status": "pending",
                "orderPointId": CorePlatform.WOMS,
                "orderPointName": CorePlatform.WOMS.label,
                "className":"WomsEcom",
                "points_redeemed":request.data.get('points_redeemed') or 0,
                "customer": {
                    # "internalId": "1",
                    "fname": request.data.get('name') if request.data.get('name') else "",
                    "lname": " ",
                    "email": request.data.get('email') if request.data.get('email') else "",
                    "phno": request.data.get('mobileNo') if request.data.get('mobileNo') else "",
                    "address1": " ",
                    "address2": "",
                    "city": "",
                    "state": "",
                    "country": "",
                    "zip": "",
                    "vendorId": vendorId
                },
                # "discount":{
                #     "value":0.0,
                #     "calType":2
                #     },
                "payment": {
                    "tipAmount": request.data.get('tip',0.0),
                    "payConfirmation": request.data.get("paymentId") if request.data.get("paymentId") else "0000",
                    "payAmount": request.data.get("finalTotal",0.0),
                    "payType":"",
                    "default": False,
                    "custProfileId":"",
                    "custPayProfileId":"",
                    "payData": "",
                    "CardId":"NA",
                    "expDate":"0000",
                    "transcationId":request.data.get("paymentId"),
                    "lastDigits":"123",
                    "billingZip":""
                }
            }
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
                    "variantName": str(item["variation_id"]) if item.get("variation_id") else "txt",
                    "quantity": item["quantity"],
                    "tag": ProductCategoryJoint.objects.get(product=corePrd.pk).category.pk, 
                    "subItems":  [
                           {
                        "plu": ProductModifier.objects.get(pk=subItem["modifierId"]).modifierPLU,
                        "name": subItem['name'],
                        "status":subItem["status"],
                        "group":  ProductModifierGroup.objects.filter(PLU=subItemGrp['plu']).first().pk,
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
                        # "group":  subItemGrp['id']
                        "group":  ProductModifierGroup.objects.filter(PLU=subItemGrp['plu']).first().pk,
                    } for subItemGrp in item['modifiersGroup'] for subItem in subItemGrp['modifiers'] if subItem["status"]
                ]  # TODO
                }
                
                if corePrd.productParentId != None:
                    itemData["variant"] = {
                        "plu": corePrd.PLU
                    }
                #####++++++++ Modifiers
                items.append(itemData)
        result["items"] = items
        result["tip"] = request.data.get('tip',0.0)
        res=order_helper.OrderHelper.openOrder(result,vendorId)
        return JsonResponse({'token':res})
    except Exception as e:
        print(e)
        return JsonResponse(
                {"msg": e}, status=400
            )


# For testing purpose of create_loyalty_points_credit_history signal
@api_view(['POST'])
def create_loyalty_points_credit_history(request):
    data = request.data
    master_id = data['id']

    master_order_instance = Order.objects.get(pk=master_id)

    if (master_order_instance.customerId.FirstName != "Guest") and (master_order_instance.customerId.Phone_Number != "0"):
        if master_order_instance.Status == 2:
            try:
                loyalty_settings = LoyaltyProgramSettings.objects.get(vendor=vendor_instance.pk)

                if loyalty_settings.is_active == True:
                    vendor_instance = Vendor.objects.get(pk=master_order_instance.vendorId.pk)
                    customer_instance = Customer.objects.get(pk=master_order_instance.customerId.pk)
                    koms_order = KOMSOrder.objects.get(master_order=master_order_instance.pk)
                    order_payment = OrderPayment.objects.get(orderId=master_order_instance.pk, status=True)

                    if koms_order.order_status == 10 and order_payment.status:
                        credit_points = int(master_order_instance.subtotal / loyalty_settings.amount_spent_in_rupees_to_earn_unit_point)

                        expiry_date = timezone.now() + timedelta(days=loyalty_settings.points_expiry_days)

                        credit_history_instance = LoyaltyPointsCreditHistory.objects.create(
                            customer=customer_instance,
                            order=master_order_instance,
                            points_credited=credit_points,
                            expiry_date=expiry_date,
                            is_expired=False,
                            total_points_redeemed=0,
                            balance_points=credit_points,
                            vendor=vendor_instance
                        )

                        if credit_history_instance:
                            existing_points_balance = customer_instance.loyalty_points_balance
                            customer_instance.loyalty_points_balance = existing_points_balance + credit_history_instance.points_credited
                            customer_instance.save()

                        return Response("Points credited", status=201)
                    
                    else:
                        return Response("Payment not done or order not closed", status=400)

            except Exception as e:
                return Response(f"{e}", status=400)
        
        else:
            return Response("Order not complete", status=400)
        

# For testing purpose of create_loyalty_points_credit_history signal
@api_view(['POST'])
def complete_order(request):
    data = json.loads(request.body)
    
    master_id = data.get('master_id')
    staging_id = data.get('staging_id')
    payment_id = data.get('payment_id')

    master_order_instance = Order.objects.get(pk=master_id)
    koms_order_instance = KOMSOrder.objects.get(pk=staging_id)
    payment_instance = OrderPayment.objects.get(pk=payment_id)

    master_order_instance.Status = 2
    master_order_instance.save()

    koms_order_instance.order_status = 10
    koms_order_instance.save()

    payment_instance.status = True
    payment_instance.save()

    return Response(status=200)


@api_view(['PUT'])
def change_customer_id_of_order(request):
    body_data = request.data

    vendor_id = body_data.get('vendor_id')
    customer_id = body_data.get('customer_id')
    order_id = body_data.get('order_id')

    if not all((vendor_id, customer_id, order_id)):
        return Response("Vendor ID, Customer ID or Order ID is empty", status=status.HTTP_400_BAD_REQUEST)

    try:
        vendor_id, customer_id, order_id = map(int, (vendor_id, customer_id, order_id))
    except ValueError:
        return Response("Invalid Vendor ID, Customer ID or Order ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()
    customer = Customer.objects.filter(pk=customer_id).first()
    master_order = Order.objects.filter(pk=order_id).first()

    if not all((vendor, customer, master_order)):
        return Response("Vendor, Customer, or Order does not exist", status=status.HTTP_400_BAD_REQUEST)

    master_order.customerId = customer
    master_order.save()

    return Response("Order mapped to Customer", status=status.HTTP_200_OK)
