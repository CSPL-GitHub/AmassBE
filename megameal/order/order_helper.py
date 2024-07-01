import threading
from core.POS_INTEGRATION.staging_pos import StagingIntegration
from core.models import POS_Settings, Platform
from order.models import Order
from core.utils import API_Messages,OrderAction, UpdatePoint
from core.POS_INTEGRATION.abstract_pos_integration import AbstractPOSIntegration
from core.POS_INTEGRATION.square_pos import SquareIntegration
from core.PLATFORM_INTEGRATION.koms_order import KomsEcom
from django.db import transaction
from core.PLATFORM_INTEGRATION.woocommerce_ecom import WooCommerce
import copy


class OrderHelper():
    def openOrder(data,vendorId):
        # +++++ response template
        coreResponse = {
            API_Messages.STATUS: API_Messages.ERROR,
            "msg": "Something went wrong"
        }
        print(data)
        order=copy.deepcopy(data)
        try:
            # ++++ pick all the channels of vendor
            try:
                platform = POS_Settings.objects.get(VendorId=vendorId)
            except POS_Settings.DoesNotExist:
                coreResponse["msg"] = "POS settings not found"
                return coreResponse,200

            # ++++++---- Stage The Order
            # stagingPos = StagingIntegration()
            with transaction.atomic():
                stageOrder = StagingIntegration().openOrder(order)
                print("stageOrder  ",order)
                data["master_id"] = order["master_id"]
                if stageOrder[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                    posService = globals()[platform.className]
                    # posResponse = posService.openOrder(data)
                    # print("posResponse   ",posResponse)
                    # if posResponse[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                    #     posResponse["response"]["core"] = stageOrder["response"]
                    for reciver in Platform.objects.filter(isActive=True,orderActionType=OrderAction.get_order_action_value("RECIEVE")): # type: ignore
                        print("reciver.Name",reciver.Name)
                        if data.get('orderPointName') == 'WOOCOMMERCE':
                            data = KomsEcom().startOrderThread(order)
                        else:
                            data = KomsEcom().startOrderThread(data)
                        
                        if order.get('points_redeemed') and  order.get('points_redeemed') != 0:
                            from pos.views import loyalty_points_redeem # placed here due to circular import error

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

                    # else:
                    #     print(posResponse)
                    #     return posResponse,500
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
            # ++++ pick all the channels of vendor
            try:
                posSettings = POS_Settings.objects.get(VendorId_id=vendorId)
            except POS_Settings.DoesNotExist:
                coreResponse["msg"] = "POS settings not found"
                return coreResponse,200

            order=Order.objects.filter(vendorId_id=vendorId,id=data.get("orderId")).first()
            if not order:
                order=Order.objects.filter(vendorId_id=vendorId,externalOrderld=data.get("orderId")).first()
            # ++++++---- Stage The Order
            stagingPos = StagingIntegration()
            stageOrder = stagingPos.updateOrderStatus(request=data)
            if stageOrder[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                # posService = globals()[posSettings.className]
                # posResponse = posService.updateOrderStatus(response=data)
                # if posResponse[API_Messages.STATUS] == API_Messages.SUCCESSFUL:
                if data.get("updatePoint")!=UpdatePoint.WOOCOMERCE:
                    if order.platform.className:
                        platformService=globals()[order.platform.className]
                        print(platformService)
                        platformResponse = platformService.updateOrderStatus(request=data,vendorId=vendorId)
                        return platformResponse,200
                    else:
                        return stageOrder,200
                    # else:
                    #     return posResponse,200
                # else:
                #     return posResponse,500
            else:
                print("Order Status Update Error in stage++++++++++++++++++")
                return stageOrder,500

        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print("Order Status Update Error+++++++++++++++++++++")
            print(f"Unexpected {err=}, {type(err)=}")
            return coreResponse,500