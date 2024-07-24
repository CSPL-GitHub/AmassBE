from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from woms.models import *
from woms.serializer import *
from static.order_status_const import *
from core.models import (
    Product, ProductCategory, ProductCategoryJoint, ProductImage, ProductAndModifierGroupJoint,
    ProductModifier, ProductModifierGroup, Product_Option_Joint, ProductModifierAndModifierGroupJoint
)
from koms.models import Order,Order_content,Order_modifer, Order_tables
import secrets
import socket



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
    from koms.views import webSocketPush
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
                room_name = f"WOMS{old_waiter_id}------{str(vendor_id)}",
                username="CORE",
            )#remove table from old waiter
        
        table_instance.waiterId = waiter_instance
        table_instance.save()

        table_data = get_table_data(hotelTable=table_instance, language=language, vendorId=vendor_id)

        webSocketPush(
            message={"result": table_data, "UPDATE": "UPDATE"},
            room_name=f"WOMS{str(waiter_id)}------{str(vendor_id)}",
            username="CORE",
        )#update table for new waiter
        
        webSocketPush(
            message={"result": table_data, "UPDATE": "UPDATE"},
            room_name=f"WOMSPOS------{language}-{str(vendor_id)}",
            username="CORE",
        ) #update table for POS
        
        for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendor_id):
            webSocketPush(
                message={"result": table_data, "UPDATE": "UPDATE"},
                room_name=f"WOMS{str(i.pk)}------{str(vendor_id)}",
                username="CORE",
            )
        
        return JsonResponse(table_data, safe=False)
    
    except Exception as e:
        print(str(e))
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST']) 
def update_table_status(request):
    from koms.views import webSocketPush

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

        webSocketPush(
            message = {"result": table_data, "UPDATE": "UPDATE"},
            room_name = WOMS+str(table_instance.waiterId.pk if table_instance.waiterId else 0)+"------"+str(vendor_id),
            username = "CORE",
        )#update table for new waiter

        webSocketPush(
            message = {"result": table_data, "UPDATE": "UPDATE"},
            room_name = f"WOMSPOS------{language}-{str(vendor_id)}",
            username = "CORE",
        ) #update table for POS
        
        for i in Waiter.objects.filter(is_waiter_head=True, vendorId=vendor_id):
            webSocketPush(
                message = {"result": table_data, "UPDATE": "UPDATE"},
                room_name = f"WOMS{str(i.pk)}------{str(vendor_id)}",
                username = "CORE",
            )

        return JsonResponse(table_data, safe=False)
    
    except Exception as e:
        print(e)
        return JsonResponse({"msg": e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_total_amount(external_order_id, vendor_id):
    if external_order_id == 0:
        return 0.0
    # Using objects.filter instead of objects.get to avoid errors
    order = Order.objects.filter(externalOrderId=external_order_id).last()

    order_content = Order_content.objects.filter(orderId=order.pk, quantityStatus=1)

    product_price_total = float(0)
    modifier_price_total = float(0)
    
    for content in order_content:
        product = Product.objects.filter(PLU=content.SKU, vendorId=vendor_id).first()

        product_price_total = product_price_total + (product.productPrice * content.quantity)

        order_modifier = Order_modifer.objects.filter(contentID=content.pk, quantityStatus=1)

        for modifier in order_modifier:
            product_modifier = ProductModifier.objects.filter(modifierPLU=modifier.SKU, vendorId=vendor_id).first()

            modifier_price_total = modifier_price_total + (product_modifier.modifierPrice * modifier.quantity)

    total_amount = product_price_total + modifier_price_total

    return float(total_amount)


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
 

@api_view(["POST"])
def showtabledetals(request):
    requestJson = JSONParser().parse(request)
    id = requestJson.get('id')
    data= gettable(id=id,vendorId=request.GET.get("vendorId"))
    return Response(data)


@api_view(["GET"])
def womsonbordingscreen(request):
    data= [
        {
        'title': 'Take Order',
        'subTitle':'Efficiently take orders from your customers with ease',
        'imageUrl':'static/womsonbording/waiter.jpg'
        },
       
       {
        'title': 'Customize Order',
        'subTitle': 'Easily customize orders according to the customers specific requirements.',
        'imageUrl': 'static/womsonbording/Chicken.jpg',
       },
       {
        'title': 'Track The Order',
        'subTitle': 'Efficiently track the status of orders at different stages.',
        'imageUrl': 'static/womsonbording/cut.jpg',
       }   
        
    ]
    return JsonResponse({"data": data})       

 
@api_view(['POST'])
def createTables(request):
    from koms.views import webSocketPush
    try:
        data = JSONParser().parse(request)
        vendorId=request.GET.get("vendorId")
        data['vendorId']=vendorId
        table=Hotal_Tables_serializers(data=data)
        if table.is_valid():
            tableData=table.save()
            res=  get_table_data(hotelTable=tableData,vendorId=vendorId)
            print("status ",status )
            webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+str(tableData.waiterId.pk)+"-----"+str(vendorId),username="CORE",)#update table for new waiter
            webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+"POS-----"+str(vendorId),username="CORE",)#update table for new waiter
            for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendorId):
                webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+str(i.pk)+"-----"+str(vendorId),username="CORE",)
            return JsonResponse({"data":tableData.pk})
        else:
            return JsonResponse(table.errors,status=400)
    except Exception as e:
        return JsonResponse({"data":str(e)},status=400)

@api_view(['POST'])
def deleteTables(request):
    from koms.views import webSocketPush
    try:
        vendorId=request.GET.get("vendorId")
        data = JSONParser().parse(request)
        tableData=HotelTable.objects.get(pk=data.get('tableId'))
        if tableData:
            res=  get_table_data(hotelTable=tableData,vendorId=vendorId)
            webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+str(tableData.waiterId.pk)+"-----"+str(vendorId),username="CORE",)#update table for new waiter
            webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+"POS-----"+str(vendorId),username="CORE",)#update table for new waiter
            for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendorId):
                webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+str(i.pk)+"-----"+str(vendorId),username="CORE",)
            HotelTable.objects.filter(pk=data.get('tableId')).delete()
            return JsonResponse({"data":tableData.pk})
        else:
            return JsonResponse({"error":'table not found'},status=400)
    except Exception as e:
        return JsonResponse({"data":str(e)},status=400)  


def allCategory(request,id=0):
    info=ProductCategory.objects.filter(pk=id,vendorId=request.GET.get("vendorId"),categoryIsDeleted=False) if id!=0 else ProductCategory.objects.filter(categoryIsDeleted=False,vendorId=request.GET.get("vendorId"))
    data=[]          
    # port = request.META.get("SERVER_PORT") 
    # server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
    for i in info:
        data.append({
            "categoryId": i.pk,
            "categoryPlu": i.categoryPLU,
            "name":i.categoryName,
            "description": i.categoryDescription,
            # "image":HOST+str(i.categoryImage) if i.categoryImage else HOST+DEFAULTIMG,
            # "image":f"http://{server_ip}:{port}{i.categoryImage.url}"  if i.categoryImage else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
            "image":i.categoryImageUrl if i.categoryImageUrl else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
        })
    data = sorted(data, key=lambda x: x["categoryId"])
    return JsonResponse({"categories":data})

 
def productByCategory(request, id=0):
    vendor_id=request.GET.get("vendorId")

    products={}

    data=ProductCategory.objects.filter(pk=id, vendorId=vendor_id, categoryIsDeleted=False) if id!=0 else ProductCategory.objects.filter(categoryIsDeleted=False, vendorId=vendor_id)   
    
    for category in data:
        listOfProducts=[]

        for product in Product.objects.filter(isDeleted=False, vendorId=vendor_id, pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product'))):
            productVariants=[]

            if product.productType=="Variant":
                for prdVariants in Product.objects.filter(productParentId=product.pk, vendorId=vendor_id, isDeleted=False):
                    images=[]

                    for k in ProductImage.objects.filter(product=prdVariants.pk, vendorId=vendor_id):
                        if k is not None:
                            images.append(str(k.image))

                    options=[]

                    for varinatJoint in Product_Option_Joint.objects.filter(productId=prdVariants.pk, vendorId=vendor_id):
                        options.append(
                            {
                               "optionId":varinatJoint.optionId.optionId, 
                               "optionValueId":varinatJoint.optionValueId.itemOptionId 
                            }
                        )

                    productVariants.append({
                        "text":prdVariants.productName,
                        # "imagePath": HOST+prdVariants.productThumb.name if prdVariants.productThumb !="" else images[0] if len(images)!=0 else HOST+DEFAULTIMG,
                        # "images":images if len(images)  else [HOST+DEFAULTIMG],
                        "quantity": 0,
                        "cost": prdVariants.productPrice,
                        "description":prdVariants.productDesc,
                        "allowCustomerNotes": True,
                        "plu":prdVariants.PLU,
                        "type":prdVariants.productType,
                        "options":options
                    })

            images=[]
            
            for k in ProductImage.objects.filter(product=product.pk, vendorId=vendor_id):
                if k is not None:
                    images.append(str(k.url))
            
            modGrp=[]

            for prdModGrpJnt in ProductAndModifierGroupJoint.objects.filter(product=product.pk, vendorId=vendor_id):
                mods=[]

                for mod in ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=prdModGrpJnt.modifierGroup.pk, modifierGroup__isDeleted=False, vendor=vendor_id):
                    mods.append(
                        {
                            "cost": mod.modifier.modifierPrice,
                            "modifierId": mod.modifier.pk,
                            "name": mod.modifier.modifierName,
                            "description": mod.modifier.modifierDesc,
                            "quantity": 0, # Required for Flutter model
                            "plu": mod.modifier.modifierPLU,
                            "status": False, # Required for Flutter model
                            "image": mod.modifier.modifierImg if mod.modifier.modifierImg  else "https://beljumlah-11072023-10507069.dev.odoo.com/web/image?model=product.template&id=4649&field=image_128",
                            "active": mod.modifier.active
                        }                    
                    )
                    
                if prdModGrpJnt.modifierGroup.isDeleted ==False: 
                    modGrp.append(
                    {
                        "id": prdModGrpJnt.modifierGroup.pk,
                        "modGroupId": prdModGrpJnt.modifierGroup.pk, # required for next js site
                        "name":prdModGrpJnt.modifierGroup.name,
                        "plu":prdModGrpJnt.modifierGroup.PLU,
                        # "min":prdModGrpJnt.min,
                        # "max":prdModGrpJnt.max,
                        "min":prdModGrpJnt.modifierGroup.min,
                        "max":prdModGrpJnt.modifierGroup.max,
                        "type":prdModGrpJnt.modifierGroup.modGrptype,
                        "active":prdModGrpJnt.modifierGroup.active,
                        "modifiers":mods
                    }
                )
                
            listOfProducts.append({
                "categoryId": category.pk,
                "categoryName":category.categoryName,
                "productId": product.pk,
                "tags": product.tag or "",
                "text":product.productName,
                "imagePath": images[0] if len(images)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                "images":images if len(images)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
                "quantity": 1,
                "cost": product.productPrice,
                "active": product.active,
                "description":product.productDesc,
                "allowCustomerNotes": True,
                "totalSale":0,
                "totalSaleCount":0,
                "totalSaleQty":0,
                # "vendorId": product.vendorId.pk,
                "plu":product.PLU,
                "note":'',
                "isTaxable":product.taxable,
                "type":product.productType,
                "variant":productVariants,
                "modifiersGroup":modGrp,
            })

        products[category.pk]=listOfProducts

    return JsonResponse({"products":products})



@api_view(['GET',])
def search_Prod_categ(request,id=0,search=''):#TODO
    vendorId=request.GET.get("vendorId")
    data = Product.objects.filter(vendorId=vendorId)
    li=[]
    if id!=0:
        data = Product.objects.filter(pk=id,vendorId=vendorId)
    if len(search)!=0:    
        data=Product.objects.filter(
            Q(vendorId=vendorId) &
            (Q(name__icontains=search) | 
            Q(des__icontains=search) | 
            Q(pk__in=ProductCategoryJoint.objects.filter(category__in=(ProductCategory.objects.filter(name__icontains=search)))))
            ).distinct()
    for j in data:
        images = []
        for k in Product.objects.filter(image=j.pk,vendorId=vendorId):
                images.append(str(k.image.path))
        mod = []
        for m in ProductModifier.objects.filter(pk__in=(ProductModifierGroup.objects.value('modifire'))):
                mod.append(
                    {
                        "modifierId": m.pk,
                        "description": m.description,
                        "quantity": m.qty,
                        "sku": m.sku,
                        "status":m.status,
                        "image":m.image.path,
                    }
                )
                li.append(
                    {
                    "productId": j.pk,
                    "text": j.name,
                    "imagePath":str(j.tumbnail),
                    "images":images,
                    "quantity": j.quantity,
                    "cost": j.price,
                    "description": j.description,
                    "allowCustomerNotes": True,
                    "min":0,
                    "max":0,
                    "modifiers":mod  
                    }
                )
    return JsonResponse({'product':li})


@api_view(['POST']) 
def switchOrderTables(request):
    try:
        requestJson = JSONParser().parse(request)
        orderId = requestJson.get('orderId')
        tableId= requestJson.get('tableId')
        vendorId=request.GET.get("vendorId")
        order=Order.objects.get(externalOrderId=orderId,vendorId=vendorId)
        Order_tables.objects.filter(orderId_id=order.pk).delete()
        for table in tableId:
            Order_tables(
                orderId_id=order.pk,
                tableId_id=table
            ).save()
        return JsonResponse(requestJson,safe=False)
    except Exception as e:
        return JsonResponse({"msg": f"Unexpected {e=}, {type(e)=}"})


@api_view(['GET'])
def searchProduct(request, search):
    vendor_id = request.GET.get("vendorId")

    products={}

    data= ProductCategory.objects.filter(vendorId=vendor_id)

    listOfProducts=[]

    for category in data:
        for product in Product.objects.filter(vendorId=vendor_id, productName__icontains=search, pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product'))):
        # for product in Product.objects.filter(pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product'))):
            productVariants=[]

            if product.productType=="Variant":
                for prdVariants in Product.objects.filter(vendorId=vendor_id, productParentId=product.pk):
                    images=[]

                    for k in ProductImage.objects.filter(product=prdVariants.pk, vendorId=vendor_id):
                        if k is not None:
                            images.append(str(k.image))

                    options=[]

                    for varinatJoint in Product_Option_Joint.objects.filter(productId=prdVariants.pk):
                        options.append(
                            {
                               "optionId":varinatJoint.optionId.optionId, 
                               "optionValueId":varinatJoint.optionValueId.itemOptionId 
                            }
                        )
                    productVariants.append({
                        "text":prdVariants.productName,
                        "imagePath": HOST+prdVariants.productThumb.name if prdVariants.productThumb !="" else images[0] if len(images)!=0 else HOST+DEFAULTIMG,
                        "images":images if len(images)  else [HOST+DEFAULTIMG],
                        "quantity": 0,
                        "cost": prdVariants.productPrice,
                        "description":prdVariants.productDesc,
                        "allowCustomerNotes": True,
                        "plu":prdVariants.PLU,
                        "type":prdVariants.productType,
                        "options":options
                    })

            images=[]

            for k in ProductImage.objects.filter(product=product.pk, vendorId=vendor_id):
                if k is not None:
                    images.append(str(k.url))
            
            modGrp=[]

            for prdModGrpJnt in ProductAndModifierGroupJoint.objects.filter(product=product.pk, vendorId=vendor_id):
                mods=[]

                for mod in ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=prdModGrpJnt.modifierGroup.pk, modifierGroup__isDeleted=False, vendor=vendor_id):
                    mods.append(
                        {
                            "cost": mod.modifier.modifierPrice,
                            "modifierId": mod.modifier.pk,
                            "name": mod.modifier.modifierName,
                            "description": mod.modifier.modifierDesc,
                            "quantity": 0, # Required for Flutter model
                            "plu": mod.modifier.modifierPLU,
                            "status": False, # Required for Flutter model
                            "image": mod.modifier.modifierImg if mod.modifier.modifierImg  else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
                            "active": mod.modifier.active
                        }                    
                    )

                modGrp.append(
                    {
                        "name":prdModGrpJnt.modifierGroup.name,
                        "plu":prdModGrpJnt.modifierGroup.PLU,
                        "min":prdModGrpJnt.modifierGroup.min,
                        "max":prdModGrpJnt.modifierGroup.max,
                        "type":prdModGrpJnt.modifierGroup.modGrptype,
                        "active":prdModGrpJnt.modifierGroup.active,
                        "modifiers":mods
                    }
                )
                
            listOfProducts.append({
                "categoryId": category.pk,
                "categoryName":category.categoryName,
                "productId": product.pk,
                "tags": product.tag if product.tag else "",
                "text":product.productName,
                "imagePath": HOST+product.productThumb.name if product.productThumb !="" else images[0] if len(images)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                "images":images if len(images)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
                "quantity": 1,
                "cost": product.productPrice,
                "description":product.productDesc,
                "allowCustomerNotes": True,
                # "vendorId": product.vendorId.pk,
                "plu":product.PLU,
                "note":'',
                "isTaxable":product.taxable,
                "type":product.productType,
                "variant":productVariants,
                "active":product.active,
                "modifiersGroup":modGrp,
            })

        products[category.pk] = listOfProducts

    # return JsonResponse({"products":products})
    return JsonResponse({"products":{"1": listOfProducts}})

@api_view(["POST"])
def createOrder(request):
    data=dict(JSONParser().parse(request))
    return JsonResponse(data)


@api_view(["GET"])
def singleProdMod(request,prod=None,order=None):
    try:
        vendorId=request.GET.get("vendorId")
        # product = Order_content.objects.get(pk=prod)
        content=Order_content.objects.get(pk=prod)
        product = Product.objects.filter(PLU=content.SKU).first()
        # content=Order_content.objects.get(orderId=order,SKU=product.PLU)
        modifier=[i.SKU for i in Order_modifer.objects.filter(contentID=content.pk,status=1)]
        count=[i.SKU for i in Order_modifer.objects.filter(contentID=content.pk,status=1,quantity__gt=0)]
        print(modifier)
        modGrp=[]
        for prdModGrpJnt in ProductAndModifierGroupJoint.objects.filter(product=product.pk):
            mods=[]
            for mod in ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=prdModGrpJnt.modifierGroup.pk,modifierGroup__isDeleted=False):
                mods.append(
                    {
                        "cost":mod.modifier.modifierPrice,
                        "modifierId": mod.modifier.pk,
                        "name":mod.modifier.modifierName,
                        "description": mod.modifier.modifierDesc,
                        "quantity": Order_modifer.objects.get(contentID=content.pk,SKU=mod.modifier.modifierPLU).quantity if mod.modifier.modifierPLU in modifier else 0,
                        "plu": mod.modifier.modifierPLU,
                        "status":True if mod.modifier.modifierPLU in modifier else False,
                        "image":mod.modifier.modifierImg if mod.modifier.modifierImg  else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg"
                    }                    
                )
            modGrp.append(
                {
                    "name":prdModGrpJnt.modifierGroup.name,
                    "plu":prdModGrpJnt.modifierGroup.PLU,
                    "min":prdModGrpJnt.modifierGroup.min,
                    "max":prdModGrpJnt.modifierGroup.max,
                    "type":prdModGrpJnt.modifierGroup.modGrptype,
                    "count":len(count),
                    "modifiers":mods
                }
            )
                    
                    
        listOfProducts={
                    "productId": product.pk,
                    "text":product.productName,
                    "plu":product.PLU,
                    "quantity":content.quantity,
                    "modifiersGroup":modGrp,
                    "note":content.note
                }

        return JsonResponse(listOfProducts)
    except Exception as e:
        return JsonResponse({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
