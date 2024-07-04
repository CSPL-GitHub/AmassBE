import threading
from core.models import  Platform, Product, ProductCategoryJoint
import pytz
import requests
from datetime import datetime,timedelta
from core.utils import * 

class KomsEcom():
    def openOrder(self,order):
        from koms.views import createOrderInKomsAndWoms 
        try:
            data=order
            res = {
                "orderId": data.get('internalOrderId') ,
                "master_id":data.get('master_id'),
                "externalOrderId":data.get('externalOrderId'),
                "orderType":OrderType.get_order_type_value( data['orderType']),
                "arrivalTime": data['arrivalTime'] if data['arrivalTime']!= ""  else f"{str(datetime.today().date())}T{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')}",
                "pickupTime": data['pickupTime'] if data['pickupTime']!= ""  else f"{str(datetime.today().date())}T{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')}",
                "deliveryIsAsap": data['deliveryIsAsap'],
                "tableNo": data['tables'] if data.get('tables') else [] ,
                "items": {},
                "remake": data['remake'] if 'remake' in data else False,
                "customerName": f"{data['customer']['fname']} {data['customer']['lname']}",
                "status": 1,
                "server": ', '.join(str(item['waiterName']) if item.get('waiterName') else 'none'  for item in data['tables']) if data.get('tables') else '',
                # "orderPointId": Platform.objects.filter(Name=data['orderPointName']).first().pk,
                "isHigh": True if "priority" in  data else False,
                "note":  data["note"] if data["note"] else "None",
                "vendorId":data["vendorId"] 
            }
            try:
                res['orderPointId']=Platform.objects.filter(Name=data['orderPointName']).first().pk
            except Exception as e:
                print(e)
                res['orderPointId']=1
            #########
            totalPrepTime=0
            for index,itemData in enumerate(data['items']):
                data['items'][index]["prepTime"]=self.getPrepTime(itemData["plu"])
                totalPrepTime= totalPrepTime+data['items'][index]["prepTime"]
            res["totalPrepTime"]=totalPrepTime
            
            if totalPrepTime>0:
                current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
                new_time = current_time + timedelta(minutes=totalPrepTime)
                res["pickupTime"]=f"{str(datetime.today().date())}T{new_time.strftime('%H:%M:%S')}"
            #############
            # itemCategories = list(set(ProductCategoryJoint.objects.get(product=Product.objects.filter(PLU=i['plu'],vendorId_id=data["vendorId"]).first().pk).category.categoryName for i in data['items']))
            
            itemCategoriesSet = set()

            for i in data['items']:
                product = Product.objects.filter(PLU=i['plu'], vendorId_id=data["vendorId"]).first()
                if product is not None:
                    productCategoryJoint = ProductCategoryJoint.objects.get(product=product.pk)
                    itemCategoriesSet.add(productCategoryJoint.category.categoryName)

            itemCategories = list(itemCategoriesSet)
            
            for item in itemCategories:
                prods=[]
                for i in data['items'] :
                    print(i)
                    categoryJoint=ProductCategoryJoint.objects.get(product=Product.objects.filter(PLU=i['plu'],vendorId=data["vendorId"]).first().pk)
                    if categoryJoint.category.categoryName == item:
                        sub=[]
                        for subItem in i['modifiers']:
                            sub.append({
                                "plu": subItem['plu'],
                                "name": subItem['name'],
                                "status":subItem["status"] if subItem.get("status") else False,
                                "quantity":subItem['quantity'],
                                "group":subItem['group']
                            } )
                        prods.append({
                        "plu": i['plu'],
                        "name": i.get('productName') or  i.get('name'),
                        "quantity": i['quantity'],
                        "tag":  1,
                        "subItems": sub,
                        "itemRemark": i.get('itemRemark'),
                        "prepTime": i['prepTime']
                        })
                        # print(prods)
                    res['items'][item] = prods
            # print("KomsEcom OpenOrder",res)
            return createOrderInKomsAndWoms(orderJson=res)
        except Exception as e:
            print("Error", e)
            return {API_Messages.STATUS:API_Messages.ERROR,API_Messages.ERROR:str(e)}

    def startOrderThread(self,order):
        print("Starting koms thread...")
        thr = threading.Thread(
                 target=self.openOrder,
                 args=(),
                 kwargs={
                     "order":order
                     }
                 )
        thr.setDaemon(True)
        thr.start()

    def getPrepTime(self,plu):
     #TODO vendor ID
     try:
        prd=Product.objects.get(PLU=plu)
        return prd.preparationTime
     except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        return 0