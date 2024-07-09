

from core.POS_INTEGRATION.abstract_pos_integration import AbstractPOSIntegration
from order.models import Order, OriginalOrder
from core.utils import API_Messages, CountyConvert, DiscountCal, OrderStatus, OrderType, TaxLevel, UpdatePoint
from core.models import POS_Settings, Product, Product_Tax, Product_Taxt_Joint, Transaction_History, Vendor
import requests
import json
from datetime import datetime
from django.db.models import Prefetch


class SquareIntegration(AbstractPOSIntegration):
    platFormName = "SQUARE"

    def pushProducts(self, VendorId, response):
        pass

    def searchImages(listOfImageIds, catlogHeaders, platform):
        responseImageList = []
        for imagePath in listOfImageIds:
            url = platform.baseUrl + "/v2/catalog/object/" + \
                imagePath+"?include_related_objects=false"
            catlogResponse = requests.request(
                "GET", url, headers=catlogHeaders, data={})
            if catlogResponse.status_code in [500, 400]:
                return []
            catlogBody = catlogResponse.json()
            responseImageList.append(catlogBody.get(
                'object').get("image_data").get("url"))
        return responseImageList

    # +++++++++++++ Helper Methods
    def convertCategory(vendorId, catalogObject):
        return {
            "categoryName": catalogObject["category_data"]["name"],
            "parentId": -1,
            "description": "",
            "status": catalogObject["is_deleted"],
            "sortOrder": 1,
            "image": "",
            "plu": catalogObject["id"],
            "vendorId": vendorId,
            "isDeleted": catalogObject["is_deleted"],
        }
    # ++++++++++++++++

    # +++++++++++++++ Helper product converter
    def convertProduct(vendorId, catalogObject, catlogHeaders, platform):
        varinats = {}
        products = {}
        taxes = {}
        modifierGroupAndProductJoint = {}
        # ----- Woking on images of Product
        imagesOfProduct = []
        if catalogObject["item_data"].get("image_ids"):
            imagesOfProduct = SquareIntegration.searchImages(
                catalogObject["item_data"]["image_ids"], catlogHeaders, platform)
        # -----------------------------------
        # ------------ Category Id for product
        if catalogObject["item_data"].get("category_id"):
            catId = catalogObject["item_data"].get("category_id")
        else:
            catId = -1
        # ------------------------------------
        coreProduct = {
            "PLU": catalogObject["id"],
            "productName": catalogObject["item_data"]["name"],
            "parentId": [catId],
            "thumbnail": "",
            "price": 0,
            "qty": 0,
            "unlimited": True,
            "productStatus": catalogObject["is_deleted"],
            "description": catalogObject["item_data"].get("description"),
            "preparationTime": 0,
            "taxable": catalogObject["item_data"]["is_taxable"],
            "type": "Regular",
            "baseProductId": -1,
            "vendorId": vendorId,
            "images": imagesOfProduct,
            "isDeleted": catalogObject["is_deleted"],
        }
        productVariations = catalogObject["item_data"].get("variations")
        if productVariations:
            if len(productVariations) == 1:
                regularProduct = catalogObject["item_data"]["variations"][0]
                coreProduct["price"] = regularProduct["item_variation_data"]["price_money"]["amount"]/100
                coreProduct["sku"] = regularProduct["item_variation_data"].get(
                    "sku")
                coreProduct["meta"] = {"variantId": regularProduct["id"]}
            else:
                coreProduct["type"] = "Variant"
                for singleVarProduct in productVariations:
                    if singleVarProduct["item_variation_data"]["pricing_type"] == "FIXED_PRICING":
                        varPrice = singleVarProduct["item_variation_data"]["price_money"].get(
                            "amount")/100
                    else:
                        varPrice = coreProduct["price"]

                    coreVarOptions = []
                    if singleVarProduct["item_variation_data"].get("item_option_values"):
                        for listOtions in singleVarProduct["item_variation_data"].get("item_option_values"):
                            coreVarOptions.append({
                                "productId": singleVarProduct["id"],
                                "productOptionId": listOtions["item_option_id"],
                                "productOptionVal": listOtions["item_option_value_id"],
                            })
                    coreVarProduct = {
                        "PLU": singleVarProduct["id"],
                        "productName": singleVarProduct["item_variation_data"]["name"],
                        "parentId": [catId],
                        "thumbnail": "",
                        "price": varPrice,
                        "qty": 0,
                        "sku": singleVarProduct["item_variation_data"].get("sku"),
                        "unlimited": True,
                        "productStatus": singleVarProduct["is_deleted"],
                        "description": singleVarProduct["item_variation_data"].get("description"),
                        "preparationTime": 0,
                        "taxable": catalogObject["item_data"]["is_taxable"],
                        "type": "Variant",
                        "baseProductId": catalogObject["id"],
                        "sortOrder": singleVarProduct["item_variation_data"]["ordinal"],
                        "option": coreVarOptions,
                        "isDeleted": singleVarProduct["is_deleted"],
                        "vendorId": vendorId
                    }
                    varinats[coreVarProduct["PLU"]] = coreVarProduct

        products[coreProduct["PLU"]] = coreProduct

        if catalogObject["item_data"].get("modifier_list_info"):
            modifierGroupAndProductJoint[catalogObject["id"]] = {}
            for modGrp in catalogObject["item_data"]["modifier_list_info"]:
                modifierGroupAndProductJoint[catalogObject["id"]][modGrp["modifier_list_id"]] = {
                    "id": modGrp["modifier_list_id"],
                    "min": modGrp.get("min_selected_modifiers") if modGrp.get("min_selected_modifiers") else 0,
                    "max": modGrp.get("max_selected_modifiers") if modGrp.get("max_selected_modifiers") else 0,
                    "enabled": modGrp["enabled"]
                }
        if catalogObject["item_data"].get("tax_ids"):
            taxes[coreProduct["PLU"]
                  ] = catalogObject["item_data"].get("tax_ids")

        return {"varinats": varinats, "products": products, "modifierGroupAndProductJoint": modifierGroupAndProductJoint, "taxes": taxes}
    # +++++++++++++++

    # +++++++++++++++ Helper Modifier Group
    def convertModifierGroup(vendorId, catalogObject):
        return {
            "id": catalogObject["id"],
            "modifierGroupName": catalogObject["modifier_list_data"]["name"],
            "modifierGroupStatus": catalogObject["is_deleted"],
            "sortOrder": catalogObject["modifier_list_data"]["ordinal"],
            "type": catalogObject["modifier_list_data"]["selection_type"],
            "vendorId": vendorId,
            "isDeleted": catalogObject["is_deleted"],
        }
    # +++++++++++++++

    # +++++++++++++++++ Helper Modifier
    def convertModifier(vendorId, catalogObject, catlogHeaders, platform):
        price = 0
        img = ""
        if catalogObject["modifier_data"].get("price_money"):
            price = catalogObject["modifier_data"].get(
                "price_money").get("amount")/100
        if catalogObject["modifier_data"].get("image_id"):
            imgs = SquareIntegration.searchImages(
                [catalogObject["modifier_data"].get("image_id")], catlogHeaders, platform)
            if len(imgs) > 0:
                img = imgs[0]
        return {
            "id": catalogObject["id"],
            "modifierName": catalogObject["modifier_data"]["name"],
            "parentId": catalogObject["modifier_data"]["modifier_list_id"],
            "image": img,
            "price": price,
            "qty": 0,
            "modifierStatus": catalogObject["is_deleted"],
            "description": "",
            "vendorId": vendorId,
            "isDeleted": catalogObject["is_deleted"]
        }
    # +++++++++++++++++

    # ++++++++++++++++++ Helper Option
    def convertOption(vendorId, catalogObject):
        return {
            "id": catalogObject["id"],
            "productOptionName": catalogObject["item_option_data"]["name"],
            "vendorId": vendorId,
            "isDeleted": catalogObject["is_deleted"]
        }
    # ++++++++++++++++++

    # +++++++++++++++++++ Helper Option Val
    def convertOptionVal(vendorId, catalogObject):
        return {
            "id": catalogObject["id"],
            "productOptionValName": catalogObject["item_option_value_data"]["name"],
            "productOptionId": catalogObject["item_option_value_data"]["item_option_id"],
            "sortOrder": catalogObject["item_option_value_data"]["ordinal"],
            "vendorId": vendorId,
            "isDeleted": catalogObject["is_deleted"]
        }
    # +++++++++++++++++++

    # +++++++++++++++++++ Helper Tax
    def convertTax(vendorId, catalogObject):
        if catalogObject["tax_data"].get("applies_to_product_set_id"):
            taxLevel = TaxLevel.ORDER.label
        else:
            taxLevel = TaxLevel.PRODUCT.label
        return {
            "id": catalogObject["id"],
            "taxName": catalogObject["tax_data"]["name"],
            "percentage": catalogObject["tax_data"]["percentage"],
            "enabled": catalogObject["tax_data"]["enabled"],
            "taxLevel": taxLevel,
            "vendorId": vendorId
        }
    # +++++++++++++++++++

    # ++++++++++++++++++ Remove Joints
    def removeTaxJoints(taxList, taxId):
        for tax in taxList:
            taxUpdateList = taxList[tax]
            try:
                taxUpdateList.remove(taxId)
                print("Tax Removed "+taxId)
            except ValueError:
                print("ValueError")
            taxList[tax] = taxUpdateList
        return taxList
    # ++++++++++++++++++ Remove Joints

    def pullProducts(VendorId):

        # +++++ response template
        coreResponse = {
            "status": "Error",
            "msg": "Something went wrong",
            "response": {}
        }

        # ++++ pick all the channels of vendor
        try:
            platform = POS_Settings.objects.get(VendorId=VendorId)

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": platform.meta["Square-Version"]
            }
            payload = {
            }
            url = platform.baseUrl + "/v2/catalog/list"+"?types=CATEGORY"
            catlogResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = catlogResponse.json()
            category = {}
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    coreCategory = SquareIntegration.convertCategory(
                        VendorId, catalogObject)
                    category[coreCategory["plu"]] = coreCategory
                coreResponse["response"]["category"] = category
                # return coreResponse
            else:
                coreResponse["msg"] = "Invalid category data received"
                return coreResponse
            # ++++ End category process

            # +++++++++ Product process
            varinats = {}
            products = {}
            modifierGroupAndProductJoint = {}
            taxes = {}
            url = platform.baseUrl + "/v2/catalog/list"+"?types=ITEM"
            productsResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if productsResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = productsResponse.json()
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    prdMap = SquareIntegration.convertProduct(
                        VendorId, catalogObject, catlogHeaders, platform)
                    varinats.update(prdMap["varinats"])
                    products.update(prdMap["products"])
                    modifierGroupAndProductJoint.update(
                        prdMap["modifierGroupAndProductJoint"])
                    taxes.update(prdMap["taxes"])
            else:
                coreResponse["msg"] = "Invalid data received"

            coreResponse["response"]["products"] = products
            coreResponse["response"]["varinats"] = varinats
            coreResponse["response"]["modGrpPrdJoint"] = modifierGroupAndProductJoint
            coreResponse["response"]["taxesJnt"] = taxes

            # ++++ End Product process

            # +++++++++ Modifier Group process
            modifiersGroup = {}
            url = platform.baseUrl + "/v2/catalog/list"+"?types=MODIFIER_LIST"
            modifiersGroupResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if modifiersGroupResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = modifiersGroupResponse.json()
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    coreModifierGroup = SquareIntegration.convertModifierGroup(
                        VendorId, catalogObject)
                    modifiersGroup[coreModifierGroup["id"]] = coreModifierGroup
            else:
                coreResponse["msg"] = "Invalid data received"
            coreResponse["response"]["modifiersGroup"] = modifiersGroup
            # ++++ End Modifier Group process

            # +++++++++ Modifier process
            modifiers = {}
            url = platform.baseUrl + "/v2/catalog/list"+"?types=MODIFIER"
            productsResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if productsResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = productsResponse.json()
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    coreModifier = SquareIntegration.convertModifier(
                        VendorId, catalogObject, catlogHeaders, platform)
                    modifiers[coreModifier["id"]] = coreModifier
            else:
                coreResponse["msg"] = "Invalid data received"
            coreResponse["response"]["modifiers"] = modifiers
            # ++++ End modifier process

            # +++++++++ Product Option process
            productOptions = {}
            url = platform.baseUrl + "/v2/catalog/list"+"?types=ITEM_OPTION"
            productOptionsResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if productOptionsResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = productOptionsResponse.json()
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    coreProductOption = SquareIntegration.convertOption(
                        VendorId, catalogObject)
                    productOptions[coreProductOption["id"]] = coreProductOption
            else:
                coreResponse["msg"] = "Invalid data received"
            coreResponse["response"]["productOptions"] = productOptions
            # ++++ End Product Option process

            # +++++++++ Product Option Value process
            productOptionsVal = {}
            url = platform.baseUrl + "/v2/catalog/list"+"?types=ITEM_OPTION_VAL"
            productOptionsValResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if productOptionsValResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = productOptionsValResponse.json()
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    coreProductOptionVal = SquareIntegration.convertOptionVal(
                        VendorId, catalogObject)
                    productOptionsVal[coreProductOptionVal["id"]
                                      ] = coreProductOptionVal
            else:
                coreResponse["msg"] = "Invalid data received"

            coreResponse["response"]["productOptionsVal"] = productOptionsVal

            # ++++ End Product Option Value process

            # +++++++++ Product Tax process
            productTax = {}
            url = platform.baseUrl + "/v2/catalog/list"+"?types=TAX"
            productTaxResponse = requests.request(
                "GET", url, headers=catlogHeaders, data=payload)
            if productTaxResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                return coreResponse

            catlogBody = productTaxResponse.json()
            if 'objects' in catlogBody:
                for catalogObject in catlogBody['objects']:
                    coreTax = SquareIntegration.convertTax(
                        VendorId, catalogObject)
                    productTax[coreTax["id"]] = coreTax

                    if coreTax["taxLevel"] == TaxLevel.ORDER.label:
                        coreResponse["response"]["taxesJnt"] = SquareIntegration.removeTaxJoints(
                            coreResponse["response"]["taxesJnt"], coreTax["id"])
            else:
                coreResponse["msg"] = "Invalid data received"

            coreResponse["response"]["taxes"] = productTax
            return coreResponse
            # ++++ End Product Tax process

        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            return coreResponse

    def openOrder(response):
        # +++++++++

        # +++++ response template
        coreResponse = {
            API_Messages.STATUS: API_Messages.ERROR,
            "msg": "Something went wrong",
            "response": {}
        }

        # ++++ pick all the channels of vendor
        try:
            vendorId = response["vendorId"]
            platform = POS_Settings.objects.get(VendorId=vendorId)
            # settings = Vendor_Settings.objects.get(VendorId=vendorId)
            posMeta = platform.meta

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": posMeta["Square-Version"]
            }

            # +++++++++ Customer In POS
            customer = SquareIntegration.getCustomer(response["customer"])
            if customer["erroCode"] == 200:
                customerId = customer["response"]["id"]
            else:
                customer = SquareIntegration.createCustomer(
                    response["customer"])
                if customer["erroCode"] == 200:
                    customerId = customer["response"]["customer"]["id"]
                else:
                    coreResponse["msg"] = "Unable to create or get customer from POS"
                    coreResponse["response"] = customer.get("response")
                    return coreResponse
            # +++++++++

            # +++
            lineItems = []
            lineTaxes = []
            for lineItem in response["items"]:
                lineItem["vendorId"] = vendorId
                squareLineItem = SquareIntegration.addLineItem(lineItem)
                if len(squareLineItem["applied_taxes"]) > 0:
                    lineTaxes.append({
                        "uid": squareLineItem["applied_taxes"][0].get("tax_uid"),
                        "percentage": str(lineItem["itemLevelTax"][0]["percentage"]),
                        "name": lineItem["itemLevelTax"][0]["name"],
                        "scope": "LINE_ITEM",
                        "type": "ADDITIVE"
                    }
                    )
                lineItems.append(squareLineItem)
            ###

            # ++++ Order Status
            fulFillment = {}
            fulFillment["state"] = "PROPOSED"

            if settings.orderPrepTime:
                prep_time_duration = "P" + str(settings.orderPrepTime) + "M"
            response["orderType"] ="PICKUP" if response["orderType"] =="DINEIN" else response["orderType"] 
            if response["orderType"] == OrderType.DELIVERY.label:
                fulFillment["type"] = "DELIVERY"
                fulFillment["delivery_details"] = {
                    "schedule_type": "ASAP",
                    "recipient": {
                        "customer_id": customerId
                    },
                    "external_delivery_id": str(response["internalOrderId"]),
                }
                if prep_time_duration:
                    fulFillment["delivery_details"]["prep_time_duration"] = prep_time_duration
            elif response["orderType"] == OrderType.PICKUP.label:
                fulFillment["type"] = "PICKUP"
                fulFillment["pickup_details"] = {
                    "schedule_type": "ASAP",
                    "recipient": {
                        "customer_id": customerId
                    }
                }
                if prep_time_duration:
                    fulFillment["pickup_details"]["prep_time_duration"] = prep_time_duration
            else:
                fulFillment["type"] = "PICKUP"
                fulFillment["pickup_details"] = {
                    "schedule_type": "ASAP",
                    "recipient": {
                        "customer_id": customerId
                    }
                }
                if prep_time_duration:
                    fulFillment["pickup_details"]["prep_time_duration"] = prep_time_duration
            print("TYPE",fulFillment["type"] )
            ######

            # ++++ Pull Taxes
            if response.get("orderLevelTax"):
                for orderTax in response.get("orderLevelTax"):
                    lineTaxes.append({
                        "uid": orderTax["posId"],
                        "percentage": str(orderTax["percentage"]),
                        "name": orderTax["name"],
                        "scope": "ORDER",
                        "type": "ADDITIVE"
                    })
            # ++++ End Pull Taxes

            # +++++++++++ Discount
            discounts = []
            if response.get("discount"):
                if response["discount"]["calType"] == DiscountCal.PERCENTAGE:
                    discounts.append({
                        "name": response["discount"]["discountName"],
                        "type": "FIXED_PERCENTAGE",
                        "scope": "ORDER",
                        "percentage": str(response["discount"]["value"])
                    })
                else:
                    discounts.append({
                        "name": response["discount"]["discountName"],
                        "type": "FIXED_AMOUNT",
                        "scope": "ORDER",
                        "amount_money": {
                            "amount": round(response["discount"]["value"]*100),
                            "currency": settings.currencyCode
                        }
                    })

            # +++++++++++

            payload = {
                "order": {
                    "reference_id": response["externalOrderId"],
                    "source": {
                        "name": response["orderPointName"],
                    },
                    "customer_id": customerId,
                    "location_id": posMeta["location_id"],
                    "line_items": lineItems,
                    "fulfillments": [
                        fulFillment
                    ],
                    "taxes": lineTaxes,
                    "discounts": discounts
                }
            }
            url = platform.baseUrl + platform.openOrder

            catlogResponse = requests.request(
                "POST", url, headers=catlogHeaders, data=json.dumps(payload))
            print("Order creation response++++++++++++++++++++++")
            print(catlogResponse.status_code)
            print(catlogResponse.json())
            originalOrder = OriginalOrder(
                orderJSON=catlogResponse.json(),
                orderId=Order.objects.get(
                    pk=response["internalOrderId"], vendorId=settings.VendorId),
                externalOrderId="NA",
                platformName=SquareIntegration.platFormName,
                vendorId=settings.VendorId
            )
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                # Api_Logs(
                #     reason="create order",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                originalOrder.save()
                return coreResponse

            # Api_Logs(
            #     reason="create order",
            #     status=catlogResponse.status_code,
            #     response=catlogResponse.json()
            # ).save()

            coreResponse["response"] = catlogResponse.json()
            if coreResponse["response"].get("order"):
                originalOrder.externalOrderId = coreResponse["response"].get(
                    "order").get("id")
            originalOrder.save()

            # +++++++++Payment In POS
            if response.get("payment"):
                payResponse = SquareIntegration.payBill(response)
                if payResponse[API_Messages.STATUS] == API_Messages.ERROR:
                    coreResponse["msg"] = payResponse["response"]
                    return coreResponse
                else:
                    coreResponse[API_Messages.STATUS] = API_Messages.SUCCESSFUL
                    return coreResponse
            else:
                print("Order Payment not found++++++++++++++++")
            # ++++++++++++

        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        # except Vendor_Settings.DoesNotExist:
        #     coreResponse["msg"] = "Vendor settings not found"
        #     return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print("POS ERR",err)
            return coreResponse

    def addLineItem(response):
        try:
            prd = Product.objects.get(
                vendorId=response["vendorId"], PLU=response["plu"])
            prdTaxes = []
            # ++++ Apply product Tax

            if len(response["itemLevelTax"]) > 0:
                prdTaxes.append({
                    "tax_uid": "Line"+str(response["orderItemId"])
                })

            # +++++++

            if prd.productType == "Regular":
                id = prd.meta["variantId"]
            else:
                id = response["plu"]
                if response["variantPlu"]:
                    id = response["variantPlu"]

            lineItem = {
                "quantity": str(response["quantity"]),
                "note": response["note"],
                "item_type": "ITEM",
                "catalog_object_id": id,
                "applied_taxes": prdTaxes
            }
            mods = []
            if response.get("modifiers"):
                for mod in response["modifiers"]:
                    mods.append(SquareIntegration.addModifier(mod))
                lineItem["modifiers"] = mods

            return lineItem
        except Exception as e:
            print(f"{e=}")

    def addModifier(response):
        modData = {
            "catalog_object_id": response["plu"],
        }
        if response.get("quantity"):
            modData["quantity"] = str(response["quantity"])
        return modData

    def applyDiscount(response):
        pass

    def getDiscount(response):
        # +++++ response template
        coreResponse = {
            "status": "Error",
            "erroCode": 1,
            "msg": "Something went wrong",
            "response": {}
        }
        try:
            vendorId = response["vendorId"]
            platform = POS_Settings.objects.get(VendorId=vendorId)

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": platform.meta["Square-Version"]
            }
            url = platform.baseUrl + "/v2/catalog/object/" + \
                response["discount"]["discountId"]
            catlogResponse = requests.request(
                "GET", url, headers=catlogHeaders)
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                # Api_Logs(
                #     reason="discount",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                return coreResponse
            else:
                # Api_Logs(
                #     reason="discount",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                catlogResponse = catlogResponse.json()
                if catlogResponse.get("object") and catlogResponse.get("object").get("type") == "DISCOUNT":
                    coreResponse["status"] = "successful"
                    coreResponse["response"] = catlogResponse.get("object")
                    coreResponse["erroCode"] = 200
                    return coreResponse
                else:
                    coreResponse["msg"] = "Discount Not found"
                    # Error code 2 for customer not found in POS
                    coreResponse["erroCode"] = 2
                    return coreResponse

        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(coreResponse["msg"])
            return coreResponse

    def payBill(response):

        # +++++ response template
        coreResponse = {
            API_Messages.STATUS: API_Messages.ERROR,
            "msg": "Something went wrong",
            "response": {}
        }

        # ++++ pick all the channels of vendor
        try:
            print("Order payment started+++++++++++++++++++++++++++++")
            vendorId = response["vendorId"]
            platform = POS_Settings.objects.get(VendorId=vendorId)
            # settings = Vendor_Settings.objects.get(VendorId=vendorId)

            originalOrder = OriginalOrder.objects.exclude(externalOrderId="NA").filter(
                vendorId=vendorId,
                platformName=SquareIntegration.platFormName,
                orderId=response["internalOrderId"]).first()

            if originalOrder.orderJSON.get("order"):
                oTotal = originalOrder.orderJSON.get(
                    "order").get("total_money").get("amount")
                print("Order Total+++++++++++++++++++++++")
                print(oTotal)
                customerId = originalOrder.orderJSON.get(
                    "order").get("customer_id")
            else:
                print("Order Json not found")
                coreResponse["msg"] = "Unable to get order from POS"
                return coreResponse

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": platform.meta["Square-Version"]
            }

            tnx = Transaction_History(
                vendorId=platform.VendorId,
                transactionData='',
                transactionType=API_Messages.PAYMENT
            ).save()

            total = (originalOrder.orderId.subtotal-originalOrder.orderId.discount+originalOrder.orderId.tax +
                     originalOrder.orderId.delivery_charge)*100

            # ++++++++++++++Updating Core Order
            try:
                posTotal = (oTotal/100)
                originalOrder.orderId.due = posTotal - \
                    float(response.get("payment").get("payAmount"))
                originalOrder.orderId.save()
            except Exception as ex:
                print("Unable to update core order")
                print(f"Unable to update core order {ex=}, {type(ex)=}")
            # +++++++++++++++End Update

            payload = {
                "idempotency_key": str(originalOrder.orderId.pk)+"-"+str(tnx.pk),
                "source_id": "EXTERNAL",
                "amount_money": {
                    "amount": oTotal if oTotal else round(total),
                    "currency": settings.currencyCode
                },
                "external_details": {
                    "source": "CORE",
                    "type": "OTHER",
                    "source_fee_money": {
                        "amount": round(oTotal + (originalOrder.orderId.tip*100)) if oTotal else round(total + (originalOrder.orderId.tip*100)),
                        "currency": settings.currencyCode
                    }
                },
                "tip_money": {
                    "currency": settings.currencyCode,
                    "amount": round((originalOrder.orderId.tip*100))
                },
                "autocomplete": True,
                "order_id": originalOrder.externalOrderId,
                "customer_id": customerId
            }

            url = platform.baseUrl + platform.payBill

            catlogResponse = requests.request(
                "POST", url, headers=catlogHeaders, data=json.dumps(payload))
            print("Payment Response=++++++++++++++++++++++++++++++")
            print(catlogResponse.status_code)
            tnx.transactionData = catlogResponse.json()
            tnx.save()
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                coreResponse["response"] = catlogResponse.json()
                return coreResponse
            coreResponse["response"] = catlogResponse.json()
            coreResponse[API_Messages.STATUS] = API_Messages.SUCCESSFUL
            return coreResponse

        except POS_Settings.DoesNotExist:
            print("Payment: POS settings not found")
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        # except Vendor_Settings.DoesNotExist:
        #     coreResponse["msg"] = "Vendor settings not found"
        #     print("Payment :Vendor settings not found")
        #     return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(f"Unexpected {err=}, {type(err)=}")
            return coreResponse

    def createCustomer(response):
        # +++++ response template
        coreResponse = {
            "status": "Error",
            "erroCode": 1,
            "msg": "Something went wrong",
            "response": {}
        }
        try:
            vendorId = response["vendorId"]
            platform = POS_Settings.objects.get(VendorId=vendorId)

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": platform.meta["Square-Version"]
            }
            country = response["countryCode"]
            if len(country) > 2:
                country = CountyConvert.country_name_to_iso3166(country)
                print(country)
            print(country)

            payload = {
                "email_address": response["email"],
                "family_name": response["fname"],
                "given_name": response["lname"],
                "reference_id": str(response["internalId"]),
                "phone_number": response["phno"],
                "address": {
                    "address_line_1": response["address1"],
                    "address_line_2": response["address2"],
                    "administrative_district_level_1": response["state"],
                    "first_name": response["fname"],
                    "last_name": response["lname"],
                    "postal_code": response["zip"],
                    "country": country,
                    "locality": response["city"]
                }
            }
            url = platform.baseUrl + "/v2/customers"
            catlogResponse = requests.request(
                "POST", url, headers=catlogHeaders, data=json.dumps(payload))
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                # Api_Logs(
                #     reason="customer",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                coreResponse["response"] = catlogResponse.json()
                return coreResponse
            else:
                # Api_Logs(
                #     reason="customer",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                catlogResponse = catlogResponse.json()
                if catlogResponse.get("customer"):
                    coreResponse["status"] = "successful"
                    coreResponse["erroCode"] = 200
                    coreResponse["response"] = catlogResponse
                    return coreResponse
                else:
                    coreResponse["msg"] = "Unable to create customer"
                    coreResponse["erroCode"] = 2
                    coreResponse["response"] = catlogResponse
                    return coreResponse

        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(f"Unexpected {err=}, {type(err)=}")
            return coreResponse

    def getCustomer(response):
        # +++++ response template
        coreResponse = {
            "status": "Error",
            "erroCode": 1,
            "msg": "Something went wrong",
            "response": {}
        }
        try:
            vendorId = response["vendorId"]
            platform = POS_Settings.objects.get(VendorId=vendorId)

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": platform.meta["Square-Version"]
            }
            payload = {
                "query": {
                    "filter": {
                        "email_address": {
                            "exact": response["email"]
                        }
                    }
                }
            }
            url = platform.baseUrl + "/v2/customers/search"
            catlogResponse = requests.request(
                "POST", url, headers=catlogHeaders, data=json.dumps(payload))
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                # Api_Logs(
                #     reason="customer",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                return coreResponse
            else:
                # Api_Logs(
                #     reason="customer",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                catlogResponse = catlogResponse.json()
                if catlogResponse.get("customers"):
                    coreResponse["status"] = "successful"
                    coreResponse["response"] = catlogResponse.get("customers")[
                        0]
                    coreResponse["erroCode"] = 200
                    return coreResponse
                else:
                    coreResponse["msg"] = "Customer Not found"
                    # Error code 2 for customer not found in POS
                    coreResponse["erroCode"] = 2
                    return coreResponse

        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(coreResponse["msg"])
            return coreResponse

    def updateOrderStatus(response):
        if response.get("updatePoint") == UpdatePoint.WOOCOMERCE:
            # +++++ response template
            coreResponse = {
                "status": "Error",
                "erroCode": 1,
                "msg": "Something went wrong",
                "response": {}
            }
            try:
                vendorId = response["vendorId"]
                platform = POS_Settings.objects.get(VendorId=vendorId)
                orderStatus=OrderStatus.get_order_status_value(response["status"])
                state="COMPLETED" if orderStatus == OrderStatus.COMPLETED else "CANCELED"
                originalOrder=OriginalOrder.objects.filter(
                    platformName=SquareIntegration.platFormName,
                    vendorId=platform.VendorId,
                    orderId_id=response["orderId"]
                ).order_by('-updateTime').first()
                ##++++ Get Order From POS
                squareOrder=SquareIntegration.getOrder({"vendorId":vendorId,"orderId":originalOrder.externalOrderId})
                if squareOrder["erroCode"]==200:
                    version=squareOrder.get("response").get("version")
                    fulfillments=[]
                    for fullfill in squareOrder.get("response").get("fulfillments"):
                        fullfill["state"]=state
                        fulfillments.append(fullfill)
                else:
                    return squareOrder
                ##++++
        
                catlogHeaders = {
                    "Authorization": "Bearer "+platform.secreateKey,
                    "Content-Type": "application/json",
                    "Square-Version": platform.meta["Square-Version"]
                }
                payload = {
                    "order": {
                        "version":version,
                        "location_id":platform.meta["location_id"],
                        "fulfillments":fulfillments,
                        "state": state,
                    }
                }
                url = platform.baseUrl + "/v2/orders/"+originalOrder.externalOrderId
                catlogResponse = requests.request("PUT", url, headers=catlogHeaders, data=json.dumps(payload))
                if catlogResponse.status_code in [500, 400]:
                    coreResponse["msg"] = "Unable to connect Square"
                    # Api_Logs(
                    #     reason="OrderStatus",
                    #     status=catlogResponse.status_code,
                    #     response=catlogResponse.json()
                    # ).save()
                    coreResponse["response"] = catlogResponse.json()
                    return coreResponse
                else:
                    # Api_Logs(
                    #     reason="OrderStatus",
                    #     status=catlogResponse.status_code,
                    #     response=catlogResponse.json()
                    # ).save()
                    catlogResponse = catlogResponse.json()
                    if catlogResponse.get("customer"):
                        coreResponse["status"] = "successful"
                        coreResponse["erroCode"] = 200
                        coreResponse["response"] = catlogResponse
                        return coreResponse

            except POS_Settings.DoesNotExist:
                coreResponse["msg"] = "POS settings not found"
                return coreResponse
            except Exception as err:
                coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
                print(f"Unexpected {err=}, {type(err)=}")
                return coreResponse
        return {API_Messages.STATUS: API_Messages.SUCCESSFUL}

    def getOrder(response):
        # +++++ response template
        coreResponse = {
            "status": "Error",
            "erroCode": 1,
            "msg": "Something went wrong",
            "response": {}
        }
        try:
            vendorId = response["vendorId"]
            platform = POS_Settings.objects.get(VendorId=vendorId)

            # +++++++++ Category process
            catlogHeaders = {
                "Authorization": "Bearer "+platform.secreateKey,
                "Content-Type": "application/json",
                "Square-Version": platform.meta["Square-Version"]
            }
            url = platform.baseUrl + "/v2/orders/"+response.get("orderId")
            catlogResponse = requests.request("GET", url, headers=catlogHeaders)
            if catlogResponse.status_code in [500, 400]:
                coreResponse["msg"] = "Unable to connect Square"
                # Api_Logs(
                #     reason="getOrder",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                return coreResponse
            else:
                # Api_Logs(
                #     reason="getOrder",
                #     status=catlogResponse.status_code,
                #     response=catlogResponse.json()
                # ).save()
                catlogResponse = catlogResponse.json()
                if catlogResponse.get("order"):
                    coreResponse["status"] = "successful"
                    coreResponse["response"] = catlogResponse.get("order")
                    coreResponse["erroCode"] = 200
                    return coreResponse
                else:
                    coreResponse["msg"] = "Order Not found"
                    # Error code 2 for customer not found in POS
                    coreResponse["erroCode"] = 2
                    return coreResponse

        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(coreResponse["msg"])
            return coreResponse
