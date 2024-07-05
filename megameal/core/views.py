from django.shortcuts import render

# Create your views here.
from core.excel_file_upload import process_excel_thread
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from datetime import datetime
from django.core.files.base import ContentFile

from django.core import files


from .POS_INTEGRATION.staging_pos import StagingIntegration
from .POS_INTEGRATION.test_pos import TestIntegration

from  .models   import  *
from .serializer import *

import requests
from woocommerce import API
import json
from .PLATFORM_INTEGRATION.woocommerce_ecom import WooCommerce



@api_view(['POST'])
def excel_file(request):
    if 'excel_file' not in request.FILES:
        return JsonResponse({"error": "No file uploaded"}, status=400)
    
    vendor_id = request.data.get("vendorId")

    if vendor_id == None:
        return JsonResponse({"error": "Vendor ID cannot be empty"}, status=400)
    
    vendor = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor:
        return JsonResponse({"error": "Vendor does not exist"}, status=400)
    
    uploaded_file = request.FILES['excel_file']

    # file_name = f"{uploaded_file.name.split('.')[0]}_Vendor{vendor_id}.{uploaded_file.name.split('.')[-1]}"

    # file_path = f"/Amass/core/media/Product Details Excel/{file_name}"

    directory = os.path.join(settings.MEDIA_ROOT, 'Product Details Excel')
    os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

    file_name = f"{uploaded_file.name.split('.')[0]}_Vendor{vendor_id}.{uploaded_file.name.split('.')[-1]}"

    relative_file_path = os.path.join('Product Details Excel', file_name)

    file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)

    print(file_path)

    with default_storage.open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    file_status = process_excel_thread(file_path, 'Sheet1', vendor_id)
    
    if file_status == 0:
        return Response({'message': 'error'}, status=400)
    else:
        return Response({'message': 'success'}, status=200)

@api_view(['post'])
def woocommerce_api(request):
    data=dict(JSONParser().parse(request))
    # print(woocommerce_key_table.objects.all())
    url="http://consociate.co.in"
    wcapi = API(
    url=url,
    consumer_key= data["consumer_key"],
    consumer_secret=data["consumer_secret"],
    version="wc/v3"
    )
    woapi=wcapi.get("products", params={"per_page": 20})
    print(woapi.status_code)
    if woapi.status_code in [500,400]:
        print('code is not run')
        return Response('stop')
    woapi=woapi.json()
    for i in woapi:
        for src in i['images']: 
            str(str(src['src']).split('/')[-1]).split('?')[0]
        for  ctg in i['categories']:
            ctg['name']
            try:
                product=Productserializers(data={
                        'productName': i["name"],
                        'SKU': i["sku"],
                        'productDesc':i['description'],
                        'productThumb':files.File(ContentFile(requests.get(src['src'], allow_redirects=True).content), str(str(src['src']).split('/')[-1]).split('?')[0]),
                        'productPrice':float(i['price']),
                        'productQty':float(0),
                    #   'Unlimited':i['purchasable'],
                    #   'vendorId':i['id'],
                    #   'preparationTime':1
                    })  
                if product.is_valid():
                    prod_Save=product.save()
                elif  product.errors.keys():
                    # prod_Save=Product.objects.get(SKU=i["sku"]).pk
                    print("pk is")
                else:
                    print("Invalid ")  
                print(product.errors)

            except:
                print(prod_Save.errors)
            try:        
                category=Categoryserializers(data={
                    'categoryName':ctg['name'],
                    # 'categoryDescription':'',
                    # 'categoryStatus':   int(1),
                    # 'categorySortOrde':'',
                    # 'categoryImgage':,
                    # 'categoryCreatedAt':'',
                    # 'categoryUpdatedAt':'',
                    # 'vendorId': 1,
                },partial=True)
                if category.is_valid():
                    catg_Save=category.save()
                else:
                    catg_Save=ProductCategory.objects.get(categoryName=ctg["name"]).pk != ctg["name"]
                print(category.errors)    
                                            
            except:
                    print(catg_Save.errors)
            try:        
                category_products=ProductCategoryserializers(data={
                        'product':prod_Save.id,
                        'category':catg_Save.id
                    },partial=True)
                if category_products.is_valid():
                        category_products.save()
            except:
                pass
    return Response(woapi, status=200)


@api_view(['post'])
def pull_menu_from_pos(request):
   stagingPos=StagingIntegration()
   data=JSONParser().parse(request)
   return stagingPos.pullProducts(data)



@api_view(['post'])
def sync_menu_to_all_channels(request):
    ###++++++++++ request data
    data=dict(JSONParser().parse(request))

    ###+++++ response template
    coreResponse={
        "status":"Error",
        "msg":"Something went wrong",
        "response":{}
    }

    ####++++ pick all the channels of vendor
    try:
        platforms = Platform.objects.filter(VendorId=data['vendorId'],isActive=True)
        oldMenu = Transaction_History.objects.filter(vendorId_id=data['vendorId'], transactionType="MENU").order_by("-createdAt").first()
        for platform in platforms:
            try:
                platformOBJ = globals()[platform.className]
                response = platformOBJ.pushMenu(platform,oldMenu)
                coreResponse["response"][platform.Name]=response
            except:
                pass
        coreResponse["msg"]="Successfull"
        return Response(coreResponse, status=200)
    except Platform.DoesNotExist:
        coreResponse["msg"]="Channel Not Found"
        return Response(coreResponse, status=400)
    except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            return Response(coreResponse, status=500)
    
    

@api_view(['post'])
def wordpress_api2(request):
    data = JSONParser().parse(request)
    oredrid ="18"+datetime.datetime.now().strftime("%d%H%M%S")
    wordpress_api={
            "orderId":int(oredrid),
            "orderType": 1,
            "arrivalTime":str(datetime.datetime.today().date()) + "T10:30:00" ,
            "pickupTime": str(datetime.datetime.today().date()) + "T10:30:00",
            "deliveryIsAsap": True,
            "note": "Make it fast",
            "tableNo": 21,
            "items": {},
            "remake": False,
            "customerName":data["billing"]["first_name"],
            "status":data["status"],
            "orderPointId": 1,
    }
    orederlist = []
    for i in data["line_items"]:
        try:
            cat=ProductCategory.objects.get(pk = ProductCategoryJoint.objects.get(product=Product.objects.get(productName = i['name']).pk ).category.pk).categoryName
        except:
            cat='other category'
        if cat not in orederlist:
            orederlist.append(cat)
    dict ={} 
    for i in orederlist:
        dict[i]=[]
        for singlep in data['line_items']:
            try:
                category =ProductCategoryJoint.objects.get(product=Product.objects.get(productName = singlep['sku']).pk).category.categoryName
            except:
                category='other category'
            sub=[]
            for subitem in singlep["unifyaddondata"]:
                    for si in subitem:
                        sub.append({"plu":si['group_title'], "name": si['value_title']})
            if category == i:
                dict[i].append(
                    {
                        "plu": singlep['sku'],
                        "name": singlep['name'],
                        "quantity": singlep['quantity'],
                        "tag": 1,
                        "subItems": sub,
                        "itemRemark": singlep['price'],
                        "unit": "qtyjhasjh",
                        })  
    wordpress_api['items']=dict
    pay=Paymentserializers(data={
        "PaymentName":data["payment_method"],
        "PaymentDescription":data["payment_method_title"],
        "paymentGateway":data["is_editable"]
    })
    if pay.is_valid():
        pay_save=pay.save()
    order=Orderserializers(data={
        'Status':data["status"],
        'TotalAmount':float(data["total"]),
        'OrderDate':data["date_created"],
        'externalOrderld':data["id"],
        'arrivalTime':data["date_created"],
        'tax':float(data["total_tax"]),
        'discount':float(data["discount_total"]),
        'tip':0,
        'delivery_charge':float(data["shipping_total"]),
        'subtotal':float(data["total"]),
        'paymentMethodID':pay_save.id
    },partial=True) 
    if order.is_valid():
        orderSave=order.save()
    print(order.errors)
    original_order=OriginalOrderserializers(data={
        'OrderJSON':str(wordpress_api),
        'update_time':data['date_created'],
        'externalOraderld':data['id'],
        'parentid':data['parent_id'], 
        'Oderid':orderSave.id
    },partial=True)
    if original_order.is_valid():
        original_order.save()       
    # sent = requests.post("http://151.80.237.29:8000/saveOrder/", json=wordpress_api)
    # return Response(sent.json())
    return Response(wordpress_api) 







        
   
           
      
