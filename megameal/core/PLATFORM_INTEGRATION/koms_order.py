from core.models import Product, ProductCategoryJoint
from datetime import datetime,timedelta
from core.utils import API_Messages
from koms.models import Station
from pos.language import local_timezone, order_type_number
import threading



class KomsEcom():
    def openOrder(self, order):
        from koms.views import createOrderInKomsAndWoms

        try:
            data = order

            vendor_id = data["vendorId"]

            language = data.get("language", "English")

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

            #########
            totalPrepTime = 0

            for index,itemData in enumerate(data['items']):
                data['items'][index]["prepTime"] = self.getPrepTime(itemData["plu"])
                
                totalPrepTime = totalPrepTime+data['items'][index]["prepTime"]

            res["totalPrepTime"] = totalPrepTime
            
            if totalPrepTime > 0:
                current_time = datetime.now(local_timezone)

                new_time = current_time + timedelta(minutes=totalPrepTime)

                res["pickupTime"] = f"{str(datetime.today().date())}T{new_time.strftime('%H:%M:%S')}"
            #############
           
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