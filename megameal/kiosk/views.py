import datetime
import socket
from order import order_helper
from core.utils import API_Messages, PaymentType
from order.models import Order_Discount
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import logout
from useradmin.models import *
from core.models import *
from .models import *
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.parsers import JSONParser
from deep_translator import GoogleTranslator
from cachetools import cached, TTLCache
from .serializer import *



cache = TTLCache(maxsize=1000, ttl=3000)
l='en'

# select a language in which to translate
@api_view(["GET"])
def selectlang(request,lang='en'):
    global l
    if (lang!=l) :
        prewlang= l
        if (lang!='en') & (l!='en'):
            print('clear')
            cache.clear()
    l=lang
    # print('prew:',prewlang,'\n','current:',l,'\n')
    return JsonResponse({"kiosk":l})

# translate to selected language then caching it in RAM
@cached(cache)
def tolang(txt):
    return GoogleTranslator(source='en', target=l).translate(txt)

# translate if language is other that english
def trans(txt):
    if txt == None:
        txt = ""

    if l!='en':
        data=tolang(txt)

    else:
        data=txt
        
    return data

# to test translations
def index(request):
    text="I believe that even in the darkest of times, there is always a glimmer of hope. It may be hard to see, but it's there"
    # text="judge not thou me , as i jugde not thee. betwixt the stirrup and the ground,mercy i sought ,and mercy found"
    return JsonResponse({"text":text,"translation":trans(text)})


@api_view(["POST"])
def login(request):
    print(request.data)
    data = request.data
    try:
        user=VendorLog.objects.get(Q(password=data['password'])&(Q(userName= data['username'])|Q(email= data['username'])))
        request.session['user_id'] = user.pk
        return Response({"msg":"user found","userid":user.pk})
    except VendorLog.DoesNotExist:
        return Response({"err":"user not found"})


def logout_view(request):
    id=request.session.get('user_id')
    if id:
        logout(request)
        return JsonResponse({"msg":'user logged out'})
    return JsonResponse({"msg":'not logged in '})


# @api_view(['GET'])
def allCategory(request,id=0,vendorId=-1):
    info=ProductCategory.objects.filter(pk=id,vendorId_id=vendorId) if id!=0 else ProductCategory.objects.filter(vendorId_id=vendorId,categoryIsDeleted=False)
    data=[]  
    port = request.META.get("SERVER_PORT")
    server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
    for i in info:
        try:
            img = ProductImage.objects.filter(product=ProductCategoryJoint.objects.filter(category=i.pk).first().product.pk).first()
        except:
            img=None
        data.append({
            "categoryId": i.pk,
            "categoryPlu": i.categoryPLU,
            "name":trans(i.categoryName),
            "vendorId": i.vendorId.pk,
            "description": trans(i.categoryDescription),
            # "image":str(i.categoryImage),
            # "image": f"http://{server_ip}:{port}{i.categoryImage.url}"  if i.categoryImage else img.url if img else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
            "image": i.categoryImageUrl if i.categoryImageUrl else img.url if img else "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg",
        })
    return JsonResponse({"categories":data})


# @api_view(["GET"])
def productByCategory(request, id=0, vendorId=-1):
    # if request.session.get('user_id') is None:
    #     return Response({"kiosk":"session not found"})
    products={}

    if id != 0:
        data = ProductCategory.objects.filter(pk=id, vendorId_id=vendorId)

    else:
        data = ProductCategory.objects.filter(vendorId_id=vendorId, categoryIsDeleted=False)

    for category in data:
        listOfProducts=[]

        for product in Product.objects.filter(isDeleted=False, pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product'))):
            productVariants=[]

            if product.productType=="Variant":
                for prdVariants in Product.objects.filter(productParentId=product.pk):
                    images=[]

                    for k in ProductImage.objects.filter(product=prdVariants.pk):
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
                        "text":trans( prdVariants.productName),
                        "imagePath": str(prdVariants.productThumb),
                        "images":images,
                        "quantity": 0,
                        "cost": prdVariants.productPrice,
                        "description": trans(prdVariants.productDesc),
                        "allowCustomerNotes": True,
                        "plu":prdVariants.PLU,
                        "type":prdVariants.productType,
                        "options":options
                    })

            images=[]

            for k in ProductImage.objects.filter(product=product.pk, vendorId_id=vendorId):
                images.append(str(k.url))
            
            modGrp=[]

            for prdModGrpJnt in ProductAndModifierGroupJoint.objects.filter(product=product.pk, vendorId_id=vendorId):
                mods=[]

                for mod in ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=prdModGrpJnt.modifierGroup.pk, modifierGroup__isDeleted=False, vendor=vendorId):
                    mods.append(
                        {
                            "cost": mod.modifier.modifierPrice,
                            "modifierId": mod.modifier.pk,
                            "name": trans(mod.modifier.modifierName),
                            "description": trans(mod.modifier.modifierDesc),
                            "quantity": 0,
                            "plu": mod.modifier.modifierPLU,
                            "status": False, # Required for Flutter model
                            "active": mod.modifier.active,
                            "image": str(mod.modifier.modifierImg) if mod.modifier.modifierImg  else "https://beljumlah-11072023-10507069.dev.odoo.com/web/image?model=product.template&id=4649&field=image_128"
                        }                    
                    )

                if prdModGrpJnt.modifierGroup.isDeleted == False:
                    modGrp.append(
                    {
                        "id": prdModGrpJnt.modifierGroup.pk,
                        "name":trans(prdModGrpJnt.modifierGroup.name),
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
                "categoryName":trans(category.categoryName),
                "productId": product.pk,
                "text":trans( product.productName),
                "imagePath": str(product.productThumb),
                "images":images if len(images)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
                "quantity": 0,
                "cost": product.productPrice,
                "description": trans(product.productDesc),
                "allowCustomerNotes": True,
                "vendorId": product.vendorId.pk,
                "plu":product.PLU,
                "isTaxable":product.taxable,
                "type":product.productType,
                "variant":productVariants,
                "active":product.active,
                "tag": product.tag,
                "modifiersGroup":modGrp,
            })

        products[category.pk]=listOfProducts

    return JsonResponse({"products":products})


@api_view(["GET"])
def productDetails(request,id=0,search=''):
    vendorId = request.GET.get('vendorId')
    data=Product.objects.filter(vendorId=vendorId)
    products={}
    if id!=0:
        data=Product.objects.filter(pk=id)
    if len(search)!=0:
        data=Product.objects.filter(Q(productName__icontains=search)
                                    |Q(productDesc__icontains=search)
                                    |Q(pk__in=(ProductCategoryJoint.objects.filter(category__in=(
                                        ProductCategory.objects.filter(categoryName__icontains=search)
                                    ))))).distinct()
    for category in data:
        listOfProducts=[]
        for product in Product.objects.filter(pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product'))):
            productVariants=[]
            if product.productType=="Variant":
                for prdVariants in Product.objects.filter(productParentId=product.pk):
                    images=[]
                    for k in ProductImage.objects.filter(product=prdVariants.pk):
                        images.append(str(k.image))
                    productVariants.append({
                        "text":trans( prdVariants.productName),
                        "imagePath": str(prdVariants.productThumb),
                        "images":images,
                        "quantity": 0,
                        "cost": prdVariants.productPrice,
                        "description": trans(prdVariants.productDesc),
                        "allowCustomerNotes": True,
                        "plu":prdVariants.PLU,
                        "type":prdVariants.productType,
                    })

            images=[]
            for k in ProductImage.objects.filter(product=product.pk):
                images.append(str(k.image))
            
            modGrp=[]
            for prdModGrpJnt in ProductAndModifierGroupJoint.objects.filter(product=product.pk):
                mods=[]
                for mod in ProductModifier.objects.filter(parentId=prdModGrpJnt.modifierGroup.pk):
                    mods.append(
                        {
                            "cost": mod.modifierPrice,
                            "modifierId": mod.pk,
                            "name": trans(mod.modifierName),
                            "description": trans(mod.modifierDesc),
                            "quantity": 0, # Required for Flutter model
                            "plu": mod.modifierPLU,
                            "status": False, # Required for Flutter model
                            "image": str(mod.modifierImg)
                        }                    
                    )
                modGrp.append(
                    {
                        "name":prdModGrpJnt.modifierGroup.name,
                        "plu":prdModGrpJnt.modifierGroup.PLU,
                        "min":prdModGrpJnt.min,
                        "max":prdModGrpJnt.max,
                        "type":prdModGrpJnt.modifierGroup.modGrptype,
                        "modifiers":mods
                    }
                )
                
                
            listOfProducts.append({
                "categoryId": category.pk,
                # "categoryName":trans(category.categoryName),
                "productId": product.pk,
                "text":trans( product.productName),
                "imagePath": str(product.productThumb),
                "images":images,
                "quantity": 0,
                "cost": product.productPrice,
                "description": trans(product.productDesc),
                "allowCustomerNotes": True,
                "vendorId": product.vendorId.pk,
                "plu":product.PLU,
                "isTaxable":product.taxable,
                "type":product.productType,
                "variant":productVariants,
                "modifiers":modGrp,
            })
        products[category.pk]=listOfProducts
    return JsonResponse({"products":products})

def getDiscounts(request,vendorId=-1):
    data=[]
    discount=[]
    if request.method == 'GET':
        # discount=KioskDiscount.objects.all()
        discount=Order_Discount.objects.filter(vendorId=vendorId)
    elif request.method == 'POST':
        try:
            # discount=KioskDiscount.objects.filter(discountCode=JSONParser().parse(request)['code'])
            discount=Order_Discount.objects.filter(discountCode=JSONParser().parse(request)['code'],vendorId=vendorId)
        except:
            pass
    for i in discount:
        data.append(
        {
            "id":i.pk,
            "code":i.discountCode,
            "discription":trans(i.discountName),
            "subDiscription":str(i.end),
            "discount":i.value,
            "type":i.calType
            # "total":i.discountCost
        })
    return JsonResponse({"promocodes":data})

@api_view(['POST'])
def applyDiscount(request,vendorId=-1):
    data = JSONParser().parse(request)
    print(data['code'])
    try:
        i=Order_Discount.objects.get(discountCode=data['code'],vendorId_id=vendorId)
        # i=KioskDiscount.objects.get(discountCode=data['code'])
        return JsonResponse({
            "id":i.pk,
            "code":i.discountCode,
            "discription":trans(i.discountName),
            "subDiscription":str(i.end),
            "discount":i.value,
            "type":i.calType
            # "total":i.discountCost
        })
    except:
        return JsonResponse({
            "id":0,
            "code":'',
            "discription":'',
            "subDiscription":"",
            "discount":0.0,
            "total":0.0
        })
    
@api_view((["GET","POST"]))
def addToCart(request):
    data = JSONParser().parse(request)
    for v in data:
        # print(data[v])
        if isinstance(data[v],list):
            for ind,i in enumerate( data[v]):
                for a in i:
                    print(data[v][ind][a])
    return Response({"POST":data})


def translation(request,txt=''):
    return JsonResponse({"op":trans(txt)})


@api_view(['POST'])
def createOrder(request,vendorId=1):
    try:
        print(request.data)
        orderid=str(CorePlatform.KIOSK)+datetime.datetime.now().strftime("%H%M%S")
        result = {
                "internalOrderId": orderid,
                "vendorId": vendorId,
                "externalOrderId":orderid,
                "tax": request.data.get("tax"),
                # "subtotal": request.data.get("subtotal"),
                # "finalTotal": request.data.get("finalTotal"),
                "orderType": "PICKUP" if request.data.get("type") == "Take Away" else "DINEIN" if request.data.get("type") == "Dine In" else "PICKUP",
                "pickupTime": '',
                "arrivalTime": '',
                "deliveryIsAsap": 'true',
                "note": "",
                "items": [],
                "remake": False,
                "customerName": "test",
                "status": "pending",  # Initial status will be pending
                "Platform": 'Kiosk',
                "className":"KIOSK",
                "customer": {
                    # "internalId": "1",
                    "fname": request.data.get('name') if request.data.get('name') else "Guest",
                    "lname": "",
                    "email": "",
                    "phno": request.data.get('mobileNo') if request.data.get('mobileNo') else "0",
                    "address1": "",
                    "address2": "",
                    "city": "",
                    "state": "",
                    "country": "",
                    "zip": "",
                    "vendorId": vendorId
                },
                "discount":{},
                "payment": {
                    "tipAmount": request.data.get('tip'),
                    "payConfirmation": request.data.get("paymentId") if request.data.get("paymentId") else "0000",
                    "payAmount": request.data.get("finalTotal"),
                    "payType":"",
                    "default": True,
                    "custProfileId":"",
                    "custPayProfileId":"",
                    "payData": "",
                    "CardId":"NA",
                    "expDate":"0000",
                    "transcationId":request.data.get("paymentId"),
                    "lastDigits":"123",
                    "billingZip":"",
                    "mode":PaymentType.ONLINE
                }
            }
        if request.data.get('promocodes'):
            discount=Order_Discount.objects.get(pk=request.data.get('promocodes')[0]['id'])
            result['discount']={
                            "discountCode": discount.discountCode,
                            # "discountId": discount.plu,
                            "status": True,
                            "discountName": discount.discountName,
                            "discountCost": discount.value
                        }
            # +++++++++++ Item In order
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
                    # Variation Id instead of name
                    "variantName": str(item["variation_id"]) if item.get("variation_id") else "txt",
                    "quantity": item["quantity"],
                    "tag": ProductCategoryJoint.objects.get(product=corePrd.pk).category.pk,  # Station tag will be handled in koms
                    "subItems":  [
                           {
                        "plu": ProductModifier.objects.get(pk=subItem["modifierId"]).modifierPLU,
                        "name": subItem['name'],
                        "status":subItem["status"],
                        "group": ProductModifierGroup.objects.filter(PLU=subItemGrp['plu']).first().pk,
                    } for subItemGrp in item['modifiersGroup'] for subItem in subItemGrp['modifiers']
                ] ,
                    "itemRemark": "",  # Note Unavailable
                    "unit": "qty",  # Default
                    "modifiers": [
                           {
                        "plu": ProductModifier.objects.get(pk=subItem["modifierId"]).modifierPLU,
                        "name": subItem['name'],
                        "status":subItem["status"],
                        "quantity":subItem["quantity"],
                        "group": ProductModifierGroup.objects.filter(PLU=subItemGrp['plu']).first().pk,
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
            # +++++++++++ Item In order
        result["tip"] = request.data['tip'] 
        # return JsonResponse(result)
        tokenlist=KioskOrderData.objects.filter(date=datetime.datetime.today().date()).values_list('token')
        token=1 if len(tokenlist)==0 else max(tokenlist)[0]+1
        # res=KomsEcom().openOrder(result)
        res=order_helper.OrderHelper.openOrder(result,vendorId)
        saveData=KiosK_create_order_serializer(data={'orderdata':str(result),'date':datetime.datetime.today().date(),'token':token})
        if saveData.is_valid():
            saveData.save()
            return JsonResponse({'token':token})
        return JsonResponse(
                {"msg": "Something went wrong"}, status=400
            )
    except Exception as e:
        print(e)
        return JsonResponse(
                {"msg": e}, status=400
            )        


#### Temp API's
HOST="http://151.80.237.29:8000/"
DEFAULTIMG="static/images/default/no-image-icon-23494.png"
def allCategoryTemp(request, id=0):
    info = ProductCategory.objects.filter(pk=id) if id!=0 else ProductCategory.objects.filter(categoryIsDeleted=False)
    
    data = []

    for i in info:
        data.append({
            "categoryId": i.pk,
            "categoryPlu": i.categoryPLU,
            "name":i.categoryName,
            "description": i.categoryDescription,
            "image":HOST+str(i.categoryImage) if i.categoryImage else HOST+DEFAULTIMG,
        })
    
    return JsonResponse({"categories":data})

 
def productByCategoryTemp(request,id=0):
    products={}
    data=ProductCategory.objects.filter(pk=id) if id!=0 else ProductCategory.objects.filter(categoryIsDeleted=False)   
    for category in data:
        listOfProducts=[]
        for product in Product.objects.filter(pk__in=(ProductCategoryJoint.objects.filter(category=category.pk).values('product')),isDeleted=False):
            productVariants=[]
            if product.productType=="Variant":
                for prdVariants in Product.objects.filter(productParentId=product.pk,isDeleted=False):
                    images=[]
                    for k in ProductImage.objects.filter(product=prdVariants.pk):
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
            for k in ProductImage.objects.filter(product=product.pk):
                if k is not None:
                    images.append(str(k.url))
            
            modGrp=[]
            for prdModGrpJnt in ProductAndModifierGroupJoint.objects.filter(product=product.pk):
                mods=[]
                for mod in ProductModifier.objects.filter(parentId=prdModGrpJnt.modifierGroup.pk,isDeleted=False):
                    mods.append(
                        {
                            "cost": mod.modifierPrice,
                            "modifierId": mod.pk,
                            "name": mod.modifierName,
                            "description": mod.modifierDesc,
                            "quantity": 0, # Required for Flutter model
                            "plu": mod.modifierPLU,
                            "status": False, # Required for Flutter model
                            "image": mod.modifierImg if mod.modifierImg  else HOST+mod.modifierImg

                        }                    
                    )
                modGrp.append(
                    {
                        "name":prdModGrpJnt.modifierGroup.name,
                        "plu":prdModGrpJnt.modifierGroup.PLU,
                        "min":prdModGrpJnt.min,
                        "max":prdModGrpJnt.max,
                        "type":prdModGrpJnt.modifierGroup.modGrptype,
                        "modifiers":mods
                    }
                )
                
                
            listOfProducts.append({
                "categoryId": category.pk,
                "categoryName":category.categoryName,
                "productId": product.pk,
                "text":product.productName,
                "imagePath": HOST+product.productThumb.name if product.productThumb !="" else images[0] if len(images)!=0 else HOST+DEFAULTIMG,
                "images":images if len(images)>0  else [HOST+DEFAULTIMG],
                "quantity": 1,
                "cost": product.productPrice,
                "description":product.productDesc,
                "allowCustomerNotes": True,
                "plu":product.PLU,
                "note":'',
                "isTaxable":product.taxable,
                "type":product.productType,
                "variant":productVariants,
                "modifiersGroup":modGrp,
            })
        products[category.pk]=listOfProducts
    return JsonResponse({"products":products})
##Temp APIs End
  
  


