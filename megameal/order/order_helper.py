from core.POS_INTEGRATION.staging_pos import StagingIntegration
from core.models import Platform
from order.models import Order
from core.utils import API_Messages, OrderAction
from core.PLATFORM_INTEGRATION.koms_order import KomsEcom
from django.db import transaction
import copy



class OrderHelper():
    def openOrder(data, vendorId):
        # +++++ response template
        coreResponse = {
            API_Messages.STATUS: API_Messages.ERROR,
            "msg": "Something went wrong"
        }

        print(data)

        order=copy.deepcopy(data)

        try:
            # ++++++---- Stage The Order
            # stagingPos = StagingIntegration()
            with transaction.atomic():
                stageOrder = StagingIntegration().openOrder(order)

                print("stageOrder  ",order)

                data["master_id"] = order["master_id"]
                
                if stageOrder[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                    for reciver in Platform.objects.filter(isActive=True, orderActionType=OrderAction.get_order_action_value("RECIEVE")):
                        if (data.get('platform') == 'Website') or data.get('platform') == 'Mobile App':
                            data = KomsEcom().startOrderThread(order)
                        
                        else:
                            data = KomsEcom().startOrderThread(data)
                        
                        if order.get('points_redeemed') and  order.get('points_redeemed') != 0:
                            from pos.views import loyalty_points_redeem # placed here due to circular import error

                            order["points_redeemed"] = int(order["points_redeemed"])
                            
                            is_redeemed = loyalty_points_redeem(
                                vendorId,
                                order["customer"]["internalId"],
                                order["master_id"],
                                order["is_wordpress"],
                                order["points_redeemed"],
                                order["points_redeemed_by"]
                            )
                    
                            if is_redeemed == True:
                                pass
                            
                            else:
                                coreResponse["msg"] = stageOrder["msg"]
                                print("Order Error in stage++++++++++++++++++")
                                transaction.set_rollback(True)
                                return coreResponse,500
                            
                        return data,201
                    
                else:
                    coreResponse["msg"] = stageOrder["msg"]
                    print("Order Error in stage++++++++++++++++++")
                    transaction.set_rollback(True)
                    return coreResponse,500

        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print("Order Erroo+++++++++++++++++++++")
            print(f"Unexpected {err=}, {type(err)=}")
            return coreResponse,500

    def orderStatusUpdate(data,vendorId):
        # +++++ response template
        print("order update started ++++++++++++++++++++++++++++++++++++")
        coreResponse = {
            API_Messages.STATUS: API_Messages.ERROR,
            "msg": "Something went wrong"
        }

        try:
            order = Order.objects.filter(vendorId_id=vendorId,id=data.get("orderId")).first()
            
            if not order:
                order = Order.objects.filter(vendorId_id=vendorId,externalOrderId=data.get("orderId")).first()
            
            # ++++++---- Stage The Order
            
            stagingPos = StagingIntegration()
            
            stageOrder = stagingPos.updateOrderStatus(request=data)
            
            if stageOrder[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                return stageOrder,200
                    
            else:
                print("Order Status Update Error in stage++++++++++++++++++")
                return stageOrder,500

        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print("Order Status Update Error+++++++++++++++++++++")
            print(f"Unexpected {err=}, {type(err)=}")
            return coreResponse,500