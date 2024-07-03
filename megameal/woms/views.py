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


# @api_view(["POST"])
# def getLoginauthkey(request):
#     requestJson = JSONParser().parse(request)
#     try:
#         Waiter.objects.filter(vendorId=requestJson.get('vendorId'),email=requestJson.get('email'),password=requestJson.get('password')).update(token=secrets.token_hex(8))
#         data=Waiter.objects.get(vendorId=requestJson.get('vendorId'),email=requestJson.get('email'),password=requestJson.get('password'))
#         server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
#         res={
#             "token":data.token,
#             "waiterId":data.pk,
#             "name":data.name,
#             "email":data.email,
#             "status":data.status,
#             "waiterHead":data.is_waiter_head,
#             "image" :f"http://{server_ip}:8000{data.image.url}",
#             }
#         return Response(res)
#     except:
#         return JsonResponse(
#             {"msg": "not found"}, status=status.HTTP_400_BAD_REQUEST
#         )
 

@api_view(["POST"])
def waiter_login(request):
    request_json = JSONParser().parse(request)

    try:
        waiter = Waiter.objects.filter(
            username=request_json.get('username'),
            password=request_json.get('password')
        ).first()

        if waiter:    
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

            response_data = {
                "waiterId": waiter.pk,
                "username": waiter.username,
                "token": waiter.token,
                "name": waiter.name,
                "email": waiter.email,
                "status": waiter.status,
                "waiterHead": waiter.is_waiter_head,
                "vendorId": waiter.vendorId.pk,
                "image": f"http://{server_ip}:{port}{waiter.image.url}",
            }

            return Response(response_data, status=status.HTTP_200_OK)
        
        else:
            return Response("Invalid user credentials", status=status.HTTP_400_BAD_REQUEST)

    except Waiter.DoesNotExist:
        return JsonResponse(
            {"msg": "not found"}, status=status.HTTP_400_BAD_REQUEST
        )
 
 
@api_view(['GET'])
def get_waiters(request):
    try:
        vendor_id = request.GET.get("vendorId")
        language = request.GET.get("language", "en")

        if not vendor_id:
            return JsonResponse({"message": "Invalid Vendor ID", "waiters": []}, status=status.HTTP_400_BAD_REQUEST)
        
        waiters = Waiter.objects.filter(is_active=True, vendorId=vendor_id)
        
        waiter_list = []

        waiter_name = ""
        
        for waiter in waiters:
            waiter_name = waiter.name

            if language == "ar":
                waiter_name = waiter.name_ar

            waiter_info = {
                "id": waiter.pk,
                "name": waiter_name,
                "image": waiter.image.name,
                "is_waiter_head": waiter.is_waiter_head
            }

            waiter_list.append(waiter_info)

        return JsonResponse({"message": "", "waiters": waiter_list}, status=status.HTTP_200_OK)
    
    except Exception as e:
        return JsonResponse({"message": str(e), "waiters": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
 
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


def getTableData(hotelTable,vendorId):
    data={ 
                "tableId":hotelTable.pk, 
                "tableNumber": hotelTable.tableNumber,
                "waiterId":hotelTable.waiterId.pk if hotelTable.waiterId else 0,
                "status":hotelTable.status,
                "waiterName":hotelTable.waiterId.name if hotelTable.waiterId else "",
                "tableCapacity":hotelTable.tableCapacity, 
                "guestCount":hotelTable.guestCount,
                "floorId":hotelTable.floor.pk,
                "floorName":hotelTable.floor.name
        }
    
    try:
        test=Order_tables.objects.filter(tableId_id=hotelTable.pk).values_list("orderId_id",flat=True)
        latest_order = Order.objects.filter(id__in=test,vendorId=vendorId).order_by('-arrival_time').first()
        data["order"]=latest_order.externalOrderId if latest_order else 0
        data["total_amount"] = latest_order.master_order.subtotal
    except Order_tables.DoesNotExist:
        print("Table not found")
        data["order"]=0
        data["total_amount"] = 0.0
    except Order.DoesNotExist:
        print("Order not found")
        data["order"]=0
        data["total_amount"] = 0.0
    except Exception as e:
        data["order"]=0
        data["total_amount"] = 0.0
        print(f"Unexpected {e=}, {type(e)=}")
    return data


def  gettable(id,vendorId):
    try:
        data=Hotal_Tables.objects.filter(vendorId=vendorId) if Waiter.objects.get(pk =id,vendorId=vendorId).is_waiter_head  else Hotal_Tables.objects.filter(waiterId = id,vendorId=vendorId)
        data=data.order_by('tableNumber')
        return[ getTableData(i) for i in data ] 
    except Exception as e :
            print(e)
            return []
 
def filterTables(waiterId, filter, search, status, waiter, floor, vendorId):
    try:
        if waiterId == "POS" or Waiter.objects.get(pk=waiterId, vendorId=vendorId).is_waiter_head:
            data = Hotal_Tables.objects.filter(vendorId=vendorId)
            # print(data.count())
        else:
            data = Hotal_Tables.objects.filter(waiterId=waiterId, vendorId=vendorId)

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
            table_data.append(getTableData(hotelTable=table, vendorId=vendorId))
        
        # print(len(table_data))
        
        return table_data
    except Exception as e:
        print(e)
        return []

    
@api_view(["POST"])
def showtabledetals(request):
    requestJson = JSONParser().parse(request)
    id = requestJson.get('id')
    data= gettable(id=id,vendorId=request.GET.get("vendorId"))
    return Response(data)


def websockettable(massase):
    pass

@api_view(["post"])
def assinTableupdate(request):
    from koms.views import webSocketPush
    requestJson = JSONParser().parse(request)
    id = requestJson.get('tableId')
    floorId = requestJson.get('floorId')
    waiterId = requestJson.get('waiterId')
    vendorId=request.GET.get("vendorId")
    # filter=requestJson.get('filter') if requestJson.get('filter') else ''
    # search=requestJson.get('search') if requestJson.get('search') else ''
    
    try:
        updatetable=Hotal_Tables.objects.get(pk=id, vendorId=vendorId)
        
        if Hotal_Tables.objects.get(pk=id,  vendorId=vendorId).waiterId!=None:
            result=  getTableData(hotelTable=updatetable,vendorId=vendorId)
            oldWaiter=str(Hotal_Tables.objects.get(pk=id, vendorId=vendorId).waiterId.pk)
            webSocketPush(message={"result":result,"UPDATE": "REMOVE",},room_name=WOMS+str(oldWaiter)+"------"+str(vendorId),username="CORE",)#remove table from old waiter
        
        Hotal_Tables.objects.filter(pk=id, vendorId=vendorId).update(waiterId = waiterId)
        
        updatetable=Hotal_Tables.objects.get(pk=id,  vendorId=vendorId)
        res=getTableData(hotelTable=updatetable,vendorId=vendorId)

        webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name=WOMS+str(waiterId)+"------"+str(vendorId),username="CORE",)#update table for new waiter
        webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name=WOMS+"POS------"+str(vendorId),username="CORE",)#update table for new waiter
        
        for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendorId):
            webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name=WOMS+str(i.pk)+"------"+str(vendorId),username="CORE",)
        
        return JsonResponse(res,safe=False)
    
    except Exception as e:
        return JsonResponse({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
        
    



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
            res=  getTableData(hotelTable=tableData,vendorId=vendorId)
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
        tableData=Hotal_Tables.objects.get(pk=data.get('tableId'))
        if tableData:
            res=  getTableData(hotelTable=tableData,vendorId=vendorId)
            webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+str(tableData.waiterId.pk)+"-----"+str(vendorId),username="CORE",)#update table for new waiter
            webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+"POS-----"+str(vendorId),username="CORE",)#update table for new waiter
            for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendorId):
                webSocketPush(message={"result":res,"UPDATE": "REMOVE"},room_name=WOMS+str(i.pk)+"-----"+str(vendorId),username="CORE",)
            Hotal_Tables.objects.filter(pk=data.get('tableId')).delete()
            return JsonResponse({"data":tableData.pk})
        else:
            return JsonResponse({"error":'table not found'},status=400)
    except Exception as e:
        return JsonResponse({"data":str(e)},status=400)  
 
@api_view(['POST']) 
def Table_update_api(request):
    from koms.views import webSocketPush
    try:
        requestJson = JSONParser().parse(request)
        id = requestJson.get('id')
        floorId = requestJson.get('floor')
        vendorId=request.GET.get("vendorId")
        # filter=requestJson.get('filter')
        # search=requestJson.get('search')

        oldTableData=Hotal_Tables.objects.get(pk=id, vendorId=vendorId)
        status = oldTableData.status if requestJson.get('tableStatus')==None  else requestJson.get('tableStatus')
        guestCount = oldTableData.guestCount if requestJson.get('guestCount')==None else requestJson.get('guestCount') 
        floor = oldTableData.floor if requestJson.get('floor')==None else floorId
        data=Hotal_Tables.objects.filter(pk =id, vendorId=vendorId).update(status=status,guestCount=guestCount)
        updatetable=Hotal_Tables.objects.get(pk=id, vendorId=vendorId)
        res=getTableData(hotelTable=updatetable,vendorId=vendorId)
        print("status ",status )

        # webSocketPush({"result":res,"UPDATE": "UPDATE"},WOMS+str(updatetable.waiterId.pk)+"-"+filter+"-"+search+"--","CORE",)#update table for new waiter
        webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name=WOMS+str(updatetable.waiterId.pk if updatetable.waiterId else 0)+"------"+str(vendorId),username="CORE",)#update table for new waiter
        webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name=WOMS+"POS------"+str(vendorId),username="CORE",)#update table for new waiter
        
        for i in Waiter.objects.filter(is_waiter_head=True,vendorId=vendorId):
            # webSocketPush({"result":res,"UPDATE": "UPDATE"},WOMS+str(i.pk)+"-"+filter+"-"+search+"--","CORE",)
            webSocketPush(message={"result":res,"UPDATE": "UPDATE"},room_name=WOMS+str(i.pk)+"------"+str(vendorId),username="CORE",)

        return JsonResponse(res,safe=False)
    except Exception as e:
        print(e)
        return JsonResponse(
            {"msg": e}
        )
 
 
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
            "sortOrder": i.categorySortOrder,
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
                        "quantity": prdVariants.productQty,
                        "cost": prdVariants.productPrice,
                        "description":prdVariants.productDesc,
                        "allowCustomerNotes": True,
                        "plu":prdVariants.PLU,
                        "type":prdVariants.productType,
                        "sortOrder":product.sortOrder,
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
                            "cost":mod.modifier.modifierPrice,
                            "modifierId": mod.modifier.pk,
                            "name":mod.modifier.modifierName,
                            "description": mod.modifier.modifierDesc,
                            "quantity": mod.modifier.modifierQty,
                            "plu": mod.modifier.modifierPLU,
                            "status":mod.modifier.modifierStatus,
                            "image":mod.modifier.modifierImg if mod.modifier.modifierImg  else "https://beljumlah-11072023-10507069.dev.odoo.com/web/image?model=product.template&id=4649&field=image_128",
                            # "image":mod.modifier.modifierImg,
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
                        "sortOrder":prdModGrpJnt.modifierGroup.sortOrder,
                        "type":prdModGrpJnt.modifierGroup.modGrptype,
                        "active":prdModGrpJnt.modifierGroup.active,
                        "modifiers":mods
                    }
                )
                
            listOfProducts.append({
                "categoryId": category.pk,
                "categoryName":category.categoryName,
                "prdouctId": product.pk,
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
                "sortOrder":product.sortOrder,
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
                    "prdouctId": j.pk,
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
def show_tableCapacity(request, id=0):
    vendorId=request.GET.get("vendorId")
    try:
        data=Hotal_Tables.objects.filter(vendorId=vendorId) if Waiter.objects.get(pk =id,vendorId=vendorId).is_waiter_head  else Hotal_Tables.objects.filter(waiterId = id,vendorId=vendorId)
        tableCapacity =list(set([ i.tableCapacity for i in data]))
        table = [str(i) for i in tableCapacity]
        return JsonResponse({ "tableCapacity": table}, safe=False)
    except Exception as e:
        return JsonResponse({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)


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
                        "quantity": prdVariants.productQty,
                        "cost": prdVariants.productPrice,
                        "description":prdVariants.productDesc,
                        "allowCustomerNotes": True,
                        "plu":prdVariants.PLU,
                        "type":prdVariants.productType,
                        "sortOrder":product.sortOrder,
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
                            "cost":mod.modifier.modifierPrice,
                            "modifierId": mod.modifier.pk,
                            "name":mod.modifier.modifierName,
                            "description": mod.modifier.modifierDesc,
                            "quantity": mod.modifier.modifierQty,
                            "plu": mod.modifier.modifierPLU,
                            "status":mod.modifier.modifierStatus,
                            "image":mod.modifier.modifierImg if mod.modifier.modifierImg  else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
                            "active": mod.modifier.active
                        }                    
                    )

                modGrp.append(
                    {
                        "name":prdModGrpJnt.modifierGroup.name,
                        "plu":prdModGrpJnt.modifierGroup.PLU,
                        "min":prdModGrpJnt.modifierGroup.min,
                        "max":prdModGrpJnt.modifierGroup.max,
                        "sortOrder":prdModGrpJnt.modifierGroup.sortOrder,
                        "type":prdModGrpJnt.modifierGroup.modGrptype,
                        "active":prdModGrpJnt.modifierGroup.active,
                        "modifiers":mods
                    }
                )
                
            listOfProducts.append({
                "categoryId": category.pk,
                "categoryName":category.categoryName,
                "prdouctId": product.pk,
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
                "sortOrder":product.sortOrder,
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
                    "sortOrder":prdModGrpJnt.modifierGroup.sortOrder,
                    "type":prdModGrpJnt.modifierGroup.modGrptype,
                    "count":len(count),
                    "modifiers":mods
                }
            )
                    
                    
        listOfProducts={
                    "prdouctId": product.pk,
                    "text":product.productName,
                    "plu":product.PLU,
                    "quantity":content.quantity,
                    "modifiersGroup":modGrp,
                    "note":content.note
                }

        return JsonResponse(listOfProducts)
    except Exception as e:
        return JsonResponse({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
