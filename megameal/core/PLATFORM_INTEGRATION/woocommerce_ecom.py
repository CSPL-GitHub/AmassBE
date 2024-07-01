import json
import socket
from urllib import response
import requests
from django.template.defaultfilters import slugify
from woocommerce import API
from order.models import Order_Discount, LoyaltyProgramSettings
from core.utils import API_Messages, ModifierType, OrderType, PaymentType, Short_Codes,ClassNames
from core.models import *
from django.db.models import Subquery, OuterRef


class WooCommerce():
    def pushMenu(platform, oldMenu):
        # +++++ response template
        coreResponse = {
            "status": "Error",
            "msg": "Something went wrong"
        }

        try:
            # ++++ wooCommerce plugin init
            wCatPrdMapping = {}
            mainResponse = []

            print("Category Sync started +++++++++++++")
            # ++++++++++++++ Category Insert and Update in WooComerce
            productCategory = ProductCategory.objects.filter(
                vendorId=platform.VendorId)
            for coreCategory in productCategory:
                response = WooCommerce.getCategoryUsingSlug(
                    coreCategory.categorySlug, platform.VendorId)
                if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
                    if not coreCategory.categoryIsDeleted:
                        catCreateRes = WooCommerce.createCategory(
                            coreCategory, platform.VendorId)
                        mainResponse.append(catCreateRes)
                        wCatPrdMapping[coreCategory.pk] = catCreateRes["response"].get(
                            "id")
                    else:
                        mainResponse.append(response)
                elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                    if coreCategory.categoryIsDeleted:
                        catCreateRes = WooCommerce.deleteCategoryUsingId(
                            response["response"].get("id"), platform.VendorId)
                        mainResponse.append(catCreateRes)
                    else:
                        mainResponse.append(response)
                        catCreateRes = WooCommerce.updateCategory(
                            coreCategory,response["response"].get("id"), platform.VendorId)
                        wCatPrdMapping[coreCategory.pk] = response["response"]["id"]
                else:
                    mainResponse.append(response)
            # ++++++++++++++ End Category Insert and Update in WooComerce
            print("Category Sync ended +++++++++++++")
            print(wCatPrdMapping)

            print("Product Sync started +++++++++++++")
            # ++++++++++++++ Product
            testList = []
            wPrdMapping= {}
            corePrds = Product.objects.filter(
                vendorId=platform.VendorId, productType="Regular")
            for corePrd in corePrds:
                response = WooCommerce.getProductUsingSku(
                    corePrd.SKU, platform.VendorId)
                if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
                    if not corePrd.isDeleted:
                        prdCreateRes = WooCommerce.createProduct(corePrd, platform.VendorId, wCatPrdMapping)
                        if prdCreateRes["code"]==Short_Codes.CONNECTED_AND_CREATED:
                            wPrdMapping[corePrd.pk]=prdCreateRes["response"].get("id")
                        testList.append(prdCreateRes)
                    else:
                        testList.append(response)
                elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                    wPrdMapping[corePrd.pk]=response["response"].get("id")
                    if  corePrd.isDeleted:
                        prdCreateRes = WooCommerce.deleteProductUsingId(
                            response["response"].get("id"), platform.VendorId, None)
                        testList.append(prdCreateRes)
                    else:
                        prdCreateRes = WooCommerce.updateProduct(response["response"].get(
                            "id"), corePrd, platform.VendorId, wCatPrdMapping)
                        if prdCreateRes["code"]==Short_Codes.CONNECTED_AND_UPDATED:
                            wPrdMapping[corePrd.pk]=prdCreateRes["response"].get("id")
                        testList.append(prdCreateRes)
                else:
                    testList.append(response)
            # ++++++++++++++++ Product
            print("Product Sync ended +++++++++++++")

            print(wPrdMapping)

            print("Varinat Sync started +++++++++++++")
            # ++++++++++++++++ Variant
            testVarList = []
            corePrds = Product.objects.filter(
                vendorId=platform.VendorId, productType="Variant", productParentId=None)
            for corePrd in corePrds:
                print(corePrd.productName + " -- "+str(corePrd.pk))
                response = WooCommerce.getProductUsingSku(
                    corePrd.SKU, platform.VendorId)
                if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
                    if not corePrd.isDeleted:
                        prdCreateRes = WooCommerce.createProduct(corePrd, platform.VendorId, wCatPrdMapping)
                        testVarList.append(prdCreateRes)
                        try:
                            varCreateRes = WooCommerce.createVarinatFromProduct(
                                corePrd, platform.VendorId, prdCreateRes["response"]["id"])
                            testVarList.append(varCreateRes)
                        except KeyError:
                            print("Key Error")
                    else:
                        testVarList.append(response)
                elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                    if corePrd.isDeleted:
                        prdCreateRes = WooCommerce.deleteProductUsingId(
                            response["response"].get("id"), platform.VendorId, None)
                        testVarList.append(prdCreateRes)
                    else:
                        prdCreateRes = WooCommerce.updateProduct(response["response"].get(
                            "id"), corePrd, platform.VendorId, wCatPrdMapping)
                        testVarList.append(prdCreateRes)
                        WooCommerce.updateVariatFromProduct(
                            response["response"].get("id"), corePrd, platform.VendorId)
                else:
                    testVarList.append(response)
            # ++++++++++++++++ Variant
            print("Varinat Sync ended +++++++++++++")

            print("Modifier Group Sync started +++++++++++++")
            # +++++++++++++++++ Modifier Group
            testModGrpList = []
            wooModGrpMapping={}
            coreModGrps = ProductModifierGroup.objects.filter(vendorId=platform.VendorId)
            for coreModGrp in coreModGrps:
                print(coreModGrp.name + " -- "+str(coreModGrp.pk)+" -- "+str(coreModGrp.slug))
                response = WooCommerce.getModifierGroupUsingSlug(coreModGrp.slug, platform.VendorId)
                if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
                    if not coreModGrp.isDeleted:
                        modGrpCrtRes = WooCommerce.createModifierGroup(coreModGrp, platform.VendorId, wooModGrpMapping)
                        testModGrpList.append(modGrpCrtRes)
                    else:
                        testModGrpList.append(response)
                elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                    if coreModGrp.isDeleted:
                        modGrpCrtRes = WooCommerce.deleteModifierGroupUsingId(response["response"].get("id"), platform.VendorId)
                        testModGrpList.append(modGrpCrtRes)
                    else:
                        modGrpCrtRes = WooCommerce.updateModifierGroup(response["response"].get("id"), coreModGrp, platform.VendorId, wooModGrpMapping)
                        testModGrpList.append(modGrpCrtRes)
                        # WooCommerce.updateVariatFromProduct(response["response"].get("id"), corePrd, platform.VendorId)
                else:
                    testModGrpList.append(response)
            # +++++++++++++++++ Modifier Group
            print("Modifier Group Sync ended +++++++++++++")

            print(wooModGrpMapping)
            
            print("Modifier Sync started +++++++++++++")
            # +++++++++++++++++ Modifier Item
            testModItmList = []
            # coreModItms = ProductModifier.objects.filter(vendorId=platform.VendorId)
            coreModItms = ProductModifierAndModifierGroupJoint.objects.filter(vendor=platform.VendorId)
            for coreModItm in coreModItms:
                print(coreModItm.modifier.modifierName + " -- "+str(coreModItm.modifier.pk)+" -- "+coreModItm.modifier.modifierPLU)
                # response = WooCommerce.getModifierUsingSKU(coreModItm.modifier.modifierSKU, platform.VendorId)
                response = WooCommerce.getModifierUsingGroupSKU(coreModItm.modifier.modifierSKU, wooModGrpMapping.get(coreModItm.modifierGroup.pk), platform.VendorId)
                # print(response)
                if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
                    if not coreModItm.modifier.isDeleted:
                        modItmCrtRes = WooCommerce.createModifier(coreModItm.modifier, platform.VendorId, wooModGrpMapping.get(coreModItm.modifierGroup.pk))
                        # print("Modifier created ,",modItmCrtRes)
                        testModItmList.append(modItmCrtRes)
                    else:
                        testModItmList.append(response)
                elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                    if coreModItm.modifier.isDeleted:
                        modItmCrtRes = WooCommerce.deleteModifierUsingId(coreModItm.modifier, platform.VendorId)
                        testModItmList.append(modItmCrtRes)
                    else:
                        modItmCrtRes = WooCommerce.updateModifier(coreModItm.modifier, platform.VendorId,wooModGrpMapping.get(coreModItm.modifierGroup.pk))
                        testModItmList.append(modItmCrtRes)
                else:
                    testModItmList.append(response)
            # +++++++++++++++++ Modifier Item
            print("Modifier Sync ended +++++++++++++")

            print("Joint Sync started +++++++++++++")
            #+++++++++++++++ Modifier Group and Product
            testPrdModGrp=[]
            corePrds = Product.objects.filter(vendorId=platform.VendorId, productType="Regular")
            for corePrd in corePrds:
                jointList=ProductAndModifierGroupJoint.objects.filter(product_id=corePrd.pk)
                if len(jointList)==0:
                    print("Joint length is Empty")
                    continue
                updateLink=WooCommerce.updateProductModifierGroupJoint(jointList=jointList,woProductId=wPrdMapping.get(corePrd.pk),woModGrpDict=wooModGrpMapping, vendorId=platform.VendorId)
                testPrdModGrp.append(updateLink)
            #+++++++++++++++ Modifier Group and Product
            print("Joint Sync ended +++++++++++++") 
            
            coreResponse["status"] = API_Messages.SUCCESSFUL
            coreResponse["msg"] = API_Messages.SUCCESSFUL
            coreResponse["response"] = {
                "cat": mainResponse, "prd": testList, "var": testVarList,"modGrp":testModGrpList,"modItm":testModItmList,"testPrdModGrp":testPrdModGrp}

        except ProductCategory.DoesNotExist:
            print("ProductCategory")
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            return coreResponse
        return coreResponse

    def getCategoryUsingSlug(slug, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.get(
                "products/categories", params={"slug": slug})
            if response.status_code == 200:
                data = response.json()
                if len(data) == 0:
                    coreResponse["code"] = Short_Codes.CONNECTED_BUT_NOTFOUND
                    return coreResponse
                if len(data) == 1:
                    coreResponse["response"] = data[0]
                    coreResponse["code"] = Short_Codes.CONNECTED_AND_FOUND
                    return coreResponse
                else:
                    coreResponse["msg"] = "Invalid number of categories : getCategoryUsingSlug"
                    coreResponse["response"] = response.json()
                    return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : getCategoryUsingSlug"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while finding WooCommerce category"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected getCategoryUsingSlug {err=}, {type(err)=}"
            return coreResponse

    def createCategory(categoryObj, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            payload = {
                "name": categoryObj.categoryName,
                "slug": categoryObj.categorySlug,
                "menu_order": categoryObj.categorySortOrder
            }
            if categoryObj.categoryImageUrl:
                payload["image"] = {
                    "src": categoryObj.categoryImageUrl
                }
            # elif categoryObj.categoryImage:
            #     server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
            #     payload["image"] = {
            #         "src":f"{server_ip}{categoryObj.categoryImage.url}" 
            #     }
            else:
                try:
                    prdImg=ProductImage.objects.filter(product=ProductCategoryJoint.objects.filter(category=categoryObj.pk).first().product.pk).first().url
                    if prdImg:
                        payload["image"] = {
                            "src": prdImg
                        }
                    else:
                        payload["image"] = {
                            "src": "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg"
                        }
                # except ProductCategoryJoint.DoesNotExist:
                #     print("Product category joint is not found for image")
                # except ProductImage.DoesNotExist:
                #     print("Image is not found for product")
                except Exception as e:
                        payload["image"] = {
                            "src": "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg"
                        }


            response = woocommerce_api.post(
                "products/categories", data=payload)
            if response.status_code == 201:
                coreResponse["msg"] = "Category Created in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createCategory"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce category"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createCategory {err=}, {type(err)=}"
            return coreResponse


    def updateCategory(categoryObj, id, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            payload = {
                "name": categoryObj.categoryName
            }
            if categoryObj.categoryImageUrl:
                payload["image"] = {
                    "src": categoryObj.categoryImageUrl
                }
            # elif categoryObj.categoryImage:
                
            #     server_ip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
            #     payload["image"] = {
            #         "src":f"{server_ip}{categoryObj.categoryImage.url}" 
            #     }
            else:
                try:
                    prdImg=ProductImage.objects.filter(product=ProductCategoryJoint.objects.filter(category=categoryObj.pk).first().product.pk).first().url
                    if prdImg:
                        payload["image"] = {
                            "src": prdImg
                        }
                    else:
                        payload["image"] = {
                            "src": "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg"
                        }
                except ProductCategoryJoint.DoesNotExist:
                    print("Product category joint is not found for image")
                except:
                    payload["image"] = {
                        "src": "https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg"
                    }
                    print("Image is not found for product")

            response = woocommerce_api.put(
                "products/categories/"+str(id), data=payload)
            if response.status_code == 201:
                coreResponse["msg"] = "Category Updated in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : updateCategory"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce category"
            return coreResponse
        except Exception as err:
            print("\nError", err)
            coreResponse["msg"] = f"Unexpected updateCategory {err=}, {type(err)=}"
            return coreResponse

    def deleteCategoryUsingId(id, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.delete(
                "products/categories/"+str(id), params={"force": True})
            if response.status_code == 200 or response.status_code == 404:
                coreResponse["msg"] = "Category is deleted"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.SUCCESS
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : deleteCategoryUsingId"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while deleting WooCommerce category"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected deleteCategoryUsingId {err=}, {type(err)=}"
            return coreResponse

    def getProductUsingSku(sku, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            woocommerce_api.timeout = 30
            response = woocommerce_api.get("products", params={"sku": sku})
            if response.status_code == 200:
                data = response.json()
                if len(data) == 0:
                    coreResponse["code"] = Short_Codes.CONNECTED_BUT_NOTFOUND
                    coreResponse["response"] = data
                    return coreResponse
                if len(data) == 1:
                    coreResponse["response"] = data[0]
                    coreResponse["code"] = Short_Codes.CONNECTED_AND_FOUND
                    return coreResponse
                else:
                    coreResponse["msg"] = "Invalid number of products : getProductUsingSku"
                    coreResponse["response"] = response.json()
                    return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : getProductUsingSku"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while finding WooCommerce product"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected getProductUsingSku {err=}, {type(err)=}"
            return coreResponse

    def createProduct(prdObj, vendorId, catPrd):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            # +++++++Images
            images = []
            try:
                imgs = ProductImage.objects.filter(product=prdObj)
                for img in imgs:
                    images.append({
                        "src": img.url
                    })
            except ProductImage.DoesNotExist:
                print("images")
            # +++++++

            # +++++++ Categories
            categories = []
            if catPrd:
                try:
                    catPrdJnts = ProductCategoryJoint.objects.filter(
                        product=prdObj)
                    for catPrdJnt in catPrdJnts:
                        if catPrd.get(catPrdJnt.category.pk):
                            categories.append({
                                "id": catPrd.get(catPrdJnt.category.pk)
                            })
                except ProductCategoryJoint.DoesNotExist:
                    print("ProductCategoryJoint")
            # +++++++

            # +++++++++++ Options
            attributes = []
            if prdObj.productType == "Variant":
                try:
                    # Subquery to get the ids of products where productParentId_id = 51
                    subquery_products = Product.objects.filter(
                        productParentId_id=prdObj.pk).values('id')
                    # Main query using Django ORM
                    distinct_option_ids = Product_Option_Joint.objects.filter(
                        productId_id__in=Subquery(subquery_products)
                    ).values_list('optionId_id', flat=True).distinct()

                    # Get the Option objects corresponding to the distinct_option_ids
                    distinct_option_objects = Product_Option.objects.filter(
                        id__in=distinct_option_ids)

                    for distinct_option in distinct_option_objects:
                        values = Product_Option_Value.objects.filter(
                            optionId_id=distinct_option.pk, isDeleted=False)
                        valueList = []
                        for val in values:
                            valueList.append(val.optionsName)
                        attributes.append({
                            "name": distinct_option.name,
                            "position": 0,
                            "visible": True,
                            "variation": True,
                            "options": valueList
                        })
                except Product_Option_Joint.DoesNotExist:
                    print("No options available")

            payload = {
                "name": prdObj.productName,
                "type": "simple" if prdObj.productType == "Regular" else "variable",
                "regular_price": str(prdObj.productPrice),
                "description": prdObj.productDesc,
                "categories": categories,
                "images": images,
                "sku": prdObj.SKU,
                "tax_status": "taxable" if prdObj.taxable else "none",
                "attributes": attributes,
                "tags": [
                        {
                        "name":slugify(tag) 
                        } for tag in str(prdObj.tag).split(',') if prdObj.tag
                        ]
            }
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.post("products", data=payload)
            if response.status_code == 201:
                coreResponse["msg"] = "Product Created in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createProduct"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce product"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createProduct {err=}, {type(err)=}"
            return coreResponse

    def deleteProductUsingId(wPrdId, vendorId, wVrtPrd):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            woocommerce_api.timeout = 30
            if wVrtPrd:
                response = woocommerce_api.delete(
                    "products/"+str(wPrdId)+"/variations/"+str(wVrtPrd), params={"force": True})
            else:
                response = woocommerce_api.delete(
                    "products/"+str(wPrdId), params={"force": True})
            if response.status_code == 200 or response.status_code == 404:
                coreResponse["msg"] = "Product is deleted"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.SUCCESS
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : deleteProductUsingId"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while deleting WooCommerce product"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected deleteProductUsingId {err=}, {type(err)=}"
            return coreResponse
        
    def disalbeProductUsingId(sku,active, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            prod = WooCommerce.getProductUsingSku(sku=sku, vendorId=vendorId)
            if prod.get("response"):
                data = requests.get(f"{platform.baseUrl}wp-json/custom/v1/update-product-visibility/{prod['response']['id']}/{active}").json()
                coreResponse["msg"] = data
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected deleteProductUsingId {err=}, {type(err)=}"
            return coreResponse

    def updateProduct(id, prdObj, vendorId, catPrd):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            woocommerce_api.timeout = 30
            # +++++++Images
            images = []
            try:
                imgs = ProductImage.objects.filter(product=prdObj)
                for img in imgs:
                    images.append({
                        "src": img.url
                    })
                print(images)
            except ProductImage.DoesNotExist:
                print("images")
            # +++++++

            # +++++++ Categories
            categories = []
            if catPrd:
                try:
                    catPrdJnts = ProductCategoryJoint.objects.filter(
                        product=prdObj)
                    for catPrdJnt in catPrdJnts:
                        if catPrd.get(catPrdJnt.category.pk):
                            categories.append({
                                "id": catPrd.get(catPrdJnt.category.pk)
                            })
                except ProductCategoryJoint.DoesNotExist:
                    print("ProductCategoryJoint")
            # +++++++

            # +++++++++++ Options
            attributes = []
            if prdObj.productType == "Variant":
                try:
                    # Subquery to get the ids of products where productParentId_id = 51
                    subquery_products = Product.objects.filter(
                        productParentId_id=prdObj.pk).values('id')
                    # Main query using Django ORM
                    distinct_option_ids = Product_Option_Joint.objects.filter(
                        productId_id__in=Subquery(subquery_products)
                    ).values_list('optionId_id', flat=True).distinct()

                    # Get the Option objects corresponding to the distinct_option_ids
                    distinct_option_objects = Product_Option.objects.filter(
                        id__in=distinct_option_ids)

                    for distinct_option in distinct_option_objects:
                        values = Product_Option_Value.objects.filter(
                            optionId_id=distinct_option.pk, isDeleted=False)
                        valueList = []
                        for val in values:
                            valueList.append(val.optionsName)
                        attributes.append({
                            "name": distinct_option.name,
                            "position": 0,
                            "visible": True,
                            "variation": True,
                            "options": valueList
                        })
                except Product_Option_Joint.DoesNotExist:
                    print("No options available")

            payload = {
                "name": prdObj.productName,
                "type": "simple" if prdObj.productType == "Regular" else "variable",
                "regular_price": str(prdObj.productPrice),
                "description": prdObj.productDesc,
                "categories": categories,
                "images": images,
                "sku": prdObj.SKU,
                "tax_status": "taxable" if prdObj.taxable else "none",
                "attributes": attributes,
                "tags": [
                        {
                        "name":slugify(tag) 
                        } for tag in str(prdObj.tag).split(',') if prdObj.tag
                        ]
            }                
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.put("products/"+str(id), data=payload)
            if response.status_code == 200:
                coreResponse["msg"] = "Product Updated in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : updateProduct"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce product"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateProduct {err=}, {type(err)=}"
            return coreResponse

    def createVarinatFromProduct(prdObj, vendorId, wPrdId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            try:
                subquery_products = Product.objects.filter(
                    productParentId_id=prdObj.pk)
            except Product.DoesNotExist:
                print("No variant found")
                coreResponse["msg"] = "No variant found"
                return coreResponse

            # ++++ Creating Variation List
            variationList = []
            for subquery_product in subquery_products:
                # +++++++Images
                images = []
                try:
                    imgs = ProductImage.objects.filter(
                        product=subquery_product)
                    for img in imgs:
                        images.append({
                            "src": img.url
                        })
                except ProductImage.DoesNotExist:
                    print("images")
                # +++++++

                # +++++++++++ Options
                attributes = []
                try:
                    distinct_option_ids = Product_Option_Joint.objects.filter(
                        productId_id=subquery_product.pk)
                    for distinct_option_id in distinct_option_ids:
                        attributes.append(
                            {
                                "name": distinct_option_id.optionId.name,
                                "option": distinct_option_id.optionValueId.optionsName
                            }
                        )
                except Product_Option_Joint.DoesNotExist:
                    print("No options available")

                variationList.append({
                    "regular_price": str(subquery_product.productPrice),
                    "attributes": attributes,
                    "description": subquery_product.productDesc,
                    "images": images,
                    "sku": subquery_product.SKU
                })
            # +++++++++++++++++ Variation List created

            payload = {
                "create": variationList
            }
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.post(
                "products/"+str(wPrdId)+"/variations/batch", data=payload)
            if response.status_code == 200:
                coreResponse["msg"] = "Variations Created in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createVarinatFromProduct"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce variations"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createVarinatFromProduct {err=}, {type(err)=}"
            return coreResponse

    def updateVariatFromProduct(wPrdId, prdObj, vendorId):
        # +++++ response template
        coreResponse = {
            "status": "Error",
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            woocommerce_api.timeout = 30
            # ++++++++++++++ Product
            testList = []
            try:
                corePrds = Product.objects.filter(productParentId_id=prdObj.pk)
            except Product.DoesNotExist:
                print("No variant found")
                coreResponse["msg"] = "No variant found"
                return coreResponse

            for corePrd in corePrds:
                response = WooCommerce.getProductUsingSku(
                    corePrd.SKU, platform.VendorId)
                if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
                    if not corePrd.isDeleted:
                        prdCreateRes = WooCommerce.createVariation(wPrdId,
                                                                   corePrd, platform.VendorId)
                        testList.append(prdCreateRes)
                    else:
                        testList.append(response)
                elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                    if corePrd.isDeleted:
                        prdCreateRes = WooCommerce.deleteProductUsingId(
                            wPrdId=wPrdId, vendorId=platform.VendorId, wVrtPrd=response["response"].get("id"))
                        testList.append(prdCreateRes)
                    else:
                        prdCreateRes = WooCommerce.updateVariation(wPrdId,
                                                                   response["response"].get("id"), corePrd, platform.VendorId)
                        testList.append(prdCreateRes)
                else:
                    testList.append(response)
                coreResponse["response"] = testList
            # ++++++++++++++++ Product
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce variations"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateVariatFromProduct {err=}, {type(err)=}"
            return coreResponse

    def createVariation(wPrdId, prdObj, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            woocommerce_api.timeout = 30
            # +++++++Images
            images = []
            try:
                imgs = ProductImage.objects.filter(product=prdObj)
                for img in imgs:
                    images.append({
                        "src": img.url
                    })
            except ProductImage.DoesNotExist:
                print("images")
            # +++++++

            # +++++++++++ Options
            attributes = []
            try:
                distinct_option_ids = Product_Option_Joint.objects.filter(
                    productId_id=prdObj.pk)
                for distinct_option_id in distinct_option_ids:
                    attributes.append(
                        {
                            "name": distinct_option_id.optionId.name,
                            "option": distinct_option_id.optionValueId.optionsName
                        }
                    )
            except Product_Option_Joint.DoesNotExist:
                print("No options available")

            payload = {
                "regular_price": str(prdObj.productPrice),
                "attributes": attributes,
                "description": prdObj.productDesc,
                "images": images,
                "sku": prdObj.SKU
            }
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.post(
                "products/"+str(wPrdId)+"/variations", data=payload)
            if response.status_code == 201:
                coreResponse["msg"] = "Variation Created in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createVariation"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce Variation"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createVariation {err=}, {type(err)=}"
            return coreResponse

    def updateVariation(wPrdId, wVrtId, prdObj, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True
            woocommerce_api.timeout = 30
            # +++++++Images
            images = []
            try:
                imgs = ProductImage.objects.filter(product=prdObj)
                for img in imgs:
                    images.append({
                        "src": img.url
                    })
            except ProductImage.DoesNotExist:
                print("images")
            # +++++++

            # +++++++++++ Options
            attributes = []
            try:
                distinct_option_ids = Product_Option_Joint.objects.filter(
                    productId_id=prdObj.pk)
                for distinct_option_id in distinct_option_ids:
                    attributes.append(
                        {
                            "name": distinct_option_id.optionId.name,
                            "option": distinct_option_id.optionValueId.optionsName
                        }
                    )
            except Product_Option_Joint.DoesNotExist:
                print("No options available")

            payload = {
                "regular_price": str(prdObj.productPrice),
                "attributes": attributes,
                "description": prdObj.productDesc,
                "images": images,
                "sku": prdObj.SKU
            }
            woocommerce_api.timeout = 30
            woocommerce_api.query_string_auth = True
            response = woocommerce_api.post(
                "products/"+str(wPrdId)+"/variations/"+str(wVrtId), data=payload)
            if response.status_code == 201:
                coreResponse["msg"] = "Variation Created in WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createVariation"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce Variation"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createVariation {err=}, {type(err)=}"
            return coreResponse


    def getModifierGroupUsingSlug(slug, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(
                VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            url = platform.baseUrl + "/wp-json/v1/getModifierGroup/"+slugify(slug)
            wooResponse = requests.request("GET", url, headers=catlogHeaders)
            if wooResponse.status_code == 200:
                data = wooResponse.json()
                if data.get("message") and data.get("message") == "Record not found":
                    coreResponse["code"] = Short_Codes.CONNECTED_BUT_NOTFOUND
                    coreResponse["response"] = data
                    return coreResponse
                if data.get("id"):
                    coreResponse["response"] = data
                    coreResponse["code"] = Short_Codes.CONNECTED_AND_FOUND
                    return coreResponse
                else:
                    coreResponse["msg"] = "Invalid modifier group : getModifierGroupUsingSlug"
                    coreResponse["response"] = wooResponse.json()
                    return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : getModifierGroupUsingSlug"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while finding WooCommerce modifier group"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected getModifierGroupUsingSlug {err=}, {type(err)=}"
            return coreResponse

    def createModifierGroup(modGrpObj, vendorId, wooModGrpMapping):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            payload = {
                "slug": slugify(modGrpObj.name),
                "title": modGrpObj.name,
                "type": "checkbox" if modGrpObj.modGrptype==ModifierType.MULTIPLE else "radio",
                "priority": modGrpObj.sortOrder
            }

            url = platform.baseUrl + "/wp-json/v1/saveModifierGroup"
            wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
            jsonData=wooResponse.json()
            if wooResponse.status_code == 200 and jsonData.get("id"):
                wooModGrpMapping[modGrpObj.pk]=jsonData.get("id")
                coreResponse["msg"] = "Modifier Group Created in WooCommerce"
                coreResponse["response"] = wooResponse.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createModifierGroup"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce createModifierGroup"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createModifierGroup {err=}, {type(err)=}"
            return coreResponse

    def deleteModifierGroupUsingId(wModGrpId, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            url = platform.baseUrl + "/wp-json/v1/deleteModifierGroup/"+str(wModGrpId)
            wooResponse = requests.request("POST", url, headers=catlogHeaders)
            jsonData=wooResponse.json()
            if wooResponse.status_code == 200 and jsonData.get("message") and jsonData.get("message")=="Record deleted successfully.":
                coreResponse["msg"] = "Modifier Group is deleted"
                coreResponse["response"] = wooResponse.json()
                coreResponse["code"] = Short_Codes.SUCCESS
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : deleteModifierGroupUsingId"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while deleting WooCommerce modifier group"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected deleteModifierGroupUsingId {err=}, {type(err)=}"
            return coreResponse

    def updateModifierGroup(id, modGrpObj, vendorId, wooModGrpMapping):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            payload ={
                "apply_to": "custom",
                "priority":modGrpObj.sortOrder,
                "type_title": modGrpObj.name,
                "type": "updated_type"
            }

            url = platform.baseUrl + "/wp-json/v1/updateModifierGroup/"+str(id)
            wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
            jsonData=wooResponse.json()
            if wooResponse.status_code == 200 and jsonData.get("message") and jsonData.get("message")=="Group record updated successfully":
                wooModGrpMapping[modGrpObj.pk]=jsonData.get("group_id")
                coreResponse["msg"] = "Modifier Group is updated"
                coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                coreResponse["response"] = wooResponse.json()
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : updateModifierGroup"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce modifier group"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateModifierGroup {err=}, {type(err)=}"
            return coreResponse

    def getModifierUsingSKU(sku, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            url = platform.baseUrl + "/wp-json/v1/getModifier/"+sku
            wooResponse = requests.request("GET", url, headers=catlogHeaders)
            if wooResponse.status_code == 200:
                data = wooResponse.json()
                
                if type(data) == list and len(data) > 0 and data[0].get("id"):
                    coreResponse["response"] = data[0]
                    coreResponse["code"] = Short_Codes.CONNECTED_AND_FOUND
                    return coreResponse
                elif data.get("message") and data.get("message") == "Record not found":
                    coreResponse["code"] = Short_Codes.CONNECTED_BUT_NOTFOUND
                    coreResponse["response"] = data
                    return coreResponse
                else:
                    coreResponse["msg"] = "Invalid modifier Item : getModifierUsingSKU"
                    coreResponse["response"] = wooResponse.json()
                    return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : getModifierUsingSKU"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while finding WooCommerce modifier"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected getModifierUsingSKU {err=}, {type(err)=}"
            return coreResponse

    def getModifierUsingGroupSKU(sku,group, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            # https://www.letsunify.in:3003/wp-json/v1/getModifierByGroupIdAndSku/groupid/sku
            url = platform.baseUrl + "wp-json/v1/getModifierByGroupIdAndSku/"+str(group)+"/"+str(sku)
            wooResponse = requests.request("GET", url, headers=catlogHeaders)
            if wooResponse.status_code == 200:
                data = wooResponse.json()
                if data.get('data') and data['data'][0]['id']:
                    coreResponse["response"] = data['data'][0]
                    coreResponse["code"] = Short_Codes.CONNECTED_AND_FOUND
                    return coreResponse
                elif data.get("message") and data.get("message") == "Record not found":
                    coreResponse["code"] = Short_Codes.CONNECTED_BUT_NOTFOUND
                    coreResponse["response"] = data
                    return coreResponse
                else:
                    coreResponse["msg"] = "Invalid modifier Item : getModifierUsingSKU"
                    coreResponse["response"] = wooResponse.json()
                    return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : getModifierUsingSKU"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while finding WooCommerce modifier"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected getModifierUsingSKU {err=}, {type(err)=}"
            return coreResponse

    def createModifier(modItmObj, vendorId, woModGrpId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            payload = {
                "group_id": woModGrpId,
                "title": modItmObj.modifierName,
                "price": modItmObj.modifierPrice,
                "sku": modItmObj.modifierSKU
            }
            url = platform.baseUrl + "/wp-json/v1/saveModifier"
            wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
            jsonData=wooResponse.json()
            if wooResponse.status_code == 200 and jsonData.get("sku"):
                coreResponse["msg"] = "Modifier Created in WooCommerce"
                coreResponse["response"] = wooResponse.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_CREATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : createModifier"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while creating WooCommerce createModifier"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected createModifier {err=}, {type(err)=}"
            return coreResponse

    def updateModifier(modItmObj,vendorId,woModGrpId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            payload = {
                "group_id":woModGrpId,
                "title": modItmObj.modifierName,
                "price": modItmObj.modifierPrice
            }
            print("payload ",payload)
            id = WooCommerce.getModifierUsingGroupSKU(modItmObj.modifierSKU,woModGrpId,vendorId)
            # https://www.letsunify.in:3003/wp-json/v1/updateModifierbyid/46
            # url = platform.baseUrl + "/wp-json/v1/updateModifierbyid/"+str(modItmObj.modifierSKU)
            url = platform.baseUrl + "wp-json/v1/updateModifierbyid/"+str(id['response']['id'])
            wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
            jsonData=wooResponse.json()
            print("jsonData ",jsonData)
            if wooResponse.status_code == 200 and jsonData.get("message") and jsonData.get("message")=="Record updated successfully":
                coreResponse["msg"] = "Modifier is updated"
                coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                coreResponse["response"] = wooResponse.json()
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : updateModifier"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce modifier"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateModifier {err=}, {type(err)=}"
            return coreResponse

    def deleteModifierUsingId(modItmObj, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            url = platform.baseUrl + "/wp-json/v1/deleteModifier/"+str(modItmObj.modifierSKU)
            wooResponse = requests.request("POST", url, headers=catlogHeaders)
            jsonData=wooResponse.json()
            if wooResponse.status_code == 200 and jsonData.get("message") and jsonData.get("message")=="Record deleted successfully":
                coreResponse["msg"] = "Modifier is deleted"
                coreResponse["response"] = wooResponse.json()
                coreResponse["code"] = Short_Codes.SUCCESS
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : deleteModifierUsingId"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while deleting WooCommerce modifier"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected deleteModifierUsingId {err=}, {type(err)=}"
            return coreResponse


    def updateProductModifierGroupJointByProduct(product, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            response  = WooCommerce.getProductUsingSku(product.SKU, product.vendorId)
            if response["code"] == Short_Codes.CONNECTED_AND_FOUND:
                woProductId = response["response"].get("id")
                groups={}
                for joint in ProductAndModifierGroupJoint.objects.filter(product=product.id):
                    gpr = WooCommerce.getModifierGroupUsingSlug(joint.modifierGroup.slug, joint.vendorId)
                    if gpr["code"] == Short_Codes.CONNECTED_AND_FOUND:
                        id = gpr["response"].get("id")
                        groups[id]=1

                platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
                catlogHeaders = {
                    "Content-Type": "application/json"
                }
                url = platform.baseUrl + "/wp-json/wp/v2/product/addons?consumer_key="+platform.secreateKey+"&consumer_secret="+platform.secreatePass
                payload={
                    "data": {
                    "product_id": woProductId,
                    "group_id": groups 
                }
                }
                wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
                jsonData=wooResponse.json()
                if wooResponse.status_code == 200:
                    coreResponse["msg"] = "Product Modifier Group Link"
                    coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                    coreResponse["response"] = wooResponse.json()
                    return coreResponse
                else:
                    coreResponse["msg"] = "Unable to connect WooCommerce : updateProductModifierGroupJoint"
                    coreResponse["response"] = wooResponse.json()
                    return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce Product Modifier Group Joint"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateProductModifierGroupJoint {err=}, {type(err)=}"
            return coreResponse

    def updateProductModifierGroupJoint(jointList,woProductId,woModGrpDict, vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            groups={}
            for joint in jointList:
                id=woModGrpDict.get(joint.modifierGroup.pk)
                groups[id]=1

            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            url = platform.baseUrl + "/wp-json/wp/v2/product/addons?consumer_key="+platform.secreateKey+"&consumer_secret="+platform.secreatePass
            payload={
                "data": {
                "product_id": woProductId,
                "group_id": groups 
             }
            }
            wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(payload))
            jsonData=wooResponse.json()
            if wooResponse.status_code == 200:
                coreResponse["msg"] = "Product Modifier Group Link"
                coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                coreResponse["response"] = wooResponse.json()
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : updateProductModifierGroupJoint"
                coreResponse["response"] = wooResponse.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce Product Modifier Group Joint"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateProductModifierGroupJoint {err=}, {type(err)=}"
            return coreResponse

# +++++++++++++++++ Order Section

    def openOrder(request, vendorId):
        ##++++
        Api_Logs(
                    reason="WooCommerce-Order",
                    status=200,
                    response=request
                ).save()
        ##+++++
        print(request)
        result = {
            "internalOrderId": "",
            "vendorId": vendorId,
            "externalOrderId": str(request["id"]),
            "pickupTime": "",
            "arrivalTime": "",
            "deliveryIsAsap": 'true',
            "note": request["customer_note"],
            "items": [],
            "remake": 'false',
            "customerName": "test",
            "status": "pending",  # Initial status will be pending
            "orderPointId": CorePlatform.WOOCOMMERCE,
            "orderPointName": CorePlatform.WOOCOMMERCE.label,
            "className":ClassNames.WOOCOMMERCE_CLASS,
            "customer": {}
        }
        if len(request["shipping_lines"]) >= 1:
            shipping = request["shipping_lines"][0]
            if "local_pickup" == shipping["method_id"]:
                result["orderType"] = OrderType.PICKUP.label
            else:
                result["orderType"] = OrderType.DELIVERY.label
                result["deliveryCharge"]=shipping["total"]
        else:
            result["orderType"] = OrderType.PICKUP.label

        result["customer"] = {
            # "internalId": customer['id'],
            "fname": request['billing']['first_name'],
            "lname": request['billing']['last_name'],
            "email": request['billing']['email'],
            "phno": request['billing']['phone'] if request['billing']['phone'] != "" else request['shipping']['phone'],
            "address1": request['billing']['address_1'] if request['billing']['address_1'] != "" else request['shipping']['address_1'],
            "address2": request['billing']['address_2'] if request['billing']['address_2'] != "" else request['shipping']['address_2'],
            "city": request['billing']['city'] if request['billing']['city'] != "" else request['shipping']['city'],
            "state": request['billing']['state'] if request['billing']['state'] != "" else request['shipping']['state'],
            "country": request['billing']['country'] if request['billing']['country'] != "" else request['shipping']['country'],
            "countryCode": request['billing']['country'] if request['billing']['country'] != "" else request['shipping']['country'],
            "zip": request['billing']['postcode'] if request['billing']['postcode'] != "" else request['shipping']['postcode'],
            "vendorId": vendorId,
        }

        # +++++++++++ Item In order
        items = []
        for item in request["line_items"]:
            try:
                corePrd = Product.objects.get(
                    SKU=item["sku"], vendorId=vendorId)
            except Product.DoesNotExist:
                return {API_Messages.ERROR: item["sku"]+" Not found"}
            itemData = {
                "plu": corePrd.productParentId.PLU if corePrd.productParentId != None else corePrd.PLU,
                "sku": item["sku"],
                "name": item["name"],
                # Variation Id instead of name
                "variantName": str(item["variation_id"]),
                "quantity": item["quantity"],
                "tag": 1,  # Station tag will be handled in koms
                "subItems": [],
                "itemRemark": "NONE",  # Note Unavailable
                "unit": "qty",  # Default
                "modifiers": []  # TODO
            }
            if corePrd.productParentId != None:
                itemData["variant"] = {
                    "plu": corePrd.PLU
                }
            if item.get("unifyaddondata"):
                for unifyAddOns in item.get("unifyaddondata"):
                    if type(unifyAddOns)==list and len(unifyAddOns)>0:
                        try:
                            coreMod=ProductModifier.objects.filter(vendorId=vendorId,modifierSKU=unifyAddOns[0].get("sku")).first()
                            itemData["modifiers"].append({
                            "plu": coreMod.modifierPLU,
                            "quantity": 1,#They don't have multiple Qty
                            "name": unifyAddOns[0].get("value_title"),
                            "status":1,
                            "group":ProductModifierGroup.objects.filter(name__icontains=unifyAddOns[0].get("group_title")).first().pk,
                            })
                        except ProductModifier.DoesNotExist:
                            print("Modifier not found")
            #####++++++++ Modifiers
            items.append(itemData)
        result["items"] = items
        # +++++++++++ Item In order

        try:
            if request.get("discount_total"):
                discountAmt = float(request["discount_total"])
                if discountAmt > 0:
                    if request["coupon_lines"] and len(request["coupon_lines"]) > 0:
                        coupon = request["coupon_lines"][0]
                        code = coupon.get("code")
                        discount = {}
                        coreDiscount = Order_Discount.objects.get(
                            vendorId_id=vendorId, discountCode=code)
                        discount["discountCode"] = coupon.get("code")
                        discount["status"] = True
                        discount["discountCost"] = coupon.get("discount")
                        discount["discountId"] = coreDiscount.plu
                        discount["discountName"] = coreDiscount.discountName
                        result["discount"] = discount
                    else:
                        print("Discount applied but no data in discount JSON")
                else:
                    print("Discount <= 0")
        except Exception as ex:
            print("Discount not applied")

        result["tip"] = 0  # TODO
        pay = {}
        #########Auth Net
        for orderMeta in request.get("meta_data"):
            if orderMeta["key"] == "_authnet_cc_last4":
                if orderMeta.get("value"):
                    pay["lastDigits"] = orderMeta.get("value")
                else:
                    pay["lastDigits"] = "N/A"
                pay["tipAmount"] = 0  # default zero
                pay["payConfirmation"] = request["transaction_id"]
                pay["payAmount"] = request["total"]
                pay["payType"] = request["payment_method_title"]
                pay["default"] = True
                pay["custProfileId"] = request["customer_id"]
                pay["custPayProfileId"] = request["payment_method_title"]
                pay["payData"] = request["meta_data"]
                pay["CardId"] = "NA"
                pay["expDate"] = "0000"
                pay["transcationId"] = request["transaction_id"]
                pay["billingZip"] = ""
                result['payment'] = pay
        
        if request.get("payment_method")=="cod" or request.get("payment_method")=="Cash on delivery":
            pay["lastDigits"] = "N/A"
            pay["tipAmount"] = 0  # default zero
            pay["payConfirmation"] = request["transaction_id"]
            pay["payAmount"] = request["total"]
            pay["shipping_total"] = request["shipping_total"]
            pay["total_tax"] = request["total_tax"]
            pay["payType"] = request["payment_method_title"]
            pay["default"] = True
            pay["custProfileId"] = request["customer_id"]
            pay["custPayProfileId"] = request["payment_method_title"]
            pay["payData"] = request["meta_data"]
            pay["CardId"] = "NA"
            pay["expDate"] = "0000"
            pay["transcationId"] = request["transaction_id"]
            pay["billingZip"] = ""
            pay['mode']=PaymentType.CASH
            result['payment'] = pay
        
        ######### Razor Pay, stripe or CCavenue
        else:
            pay["lastDigits"] = "N/A"
            pay["tipAmount"] = 0  # default zero
            pay["payConfirmation"] = request["transaction_id"]
            pay["payAmount"] = request["total"]
            pay["shipping_total"] = request["shipping_total"]
            pay["total_tax"] = request["total_tax"]
            pay["payType"] = request["payment_method_title"]
            pay["default"] = False
            pay["custProfileId"] = request["customer_id"]
            pay["custPayProfileId"] = request["payment_method_title"]
            pay["payData"] = request["meta_data"]
            pay["CardId"] = "NA"
            pay["expDate"] = "0000"
            pay["transcationId"] = request["transaction_id"]
            pay["billingZip"] = ""
            pay['mode']=PaymentType.ONLINE
            pay["platform"]=request.get("payment_method")
            result['payment'] = pay
        return result

    def updateOrderStatus(request,vendorId):
        coreResponse = {
            "status": "Error",
            "code": 1,
            "msg": "Something went wrong"
        }
        try:
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            woocommerce_api = API(
                url=platform.baseUrl,
                consumer_key=platform.secreateKey,
                consumer_secret=platform.secreatePass,
                version="wc/v3"
            )
            woocommerce_api.query_string_auth = True

            if request["status"]==OrderStatus.PREPARED.label:
                orderStatus= "prepared"
            elif request["status"]==OrderStatus.CANCELED.label:
                orderStatus="cancelled"
            elif request["status"]==OrderStatus.COMPLETED.label:
                orderStatus="completed"
            else:
                orderStatus= "pending"

            payload = {
                "status": orderStatus
            }
            print(orderStatus)
            response = woocommerce_api.post("orders/"+request.get("externalOrderId"), data=payload)
            if response.status_code == 200:
                coreResponse["msg"] = "Order status is updated WooCommerce"
                coreResponse["response"] = response.json()
                coreResponse["code"] = Short_Codes.CONNECTED_AND_UPDATED
                return coreResponse
            else:
                coreResponse["msg"] = "Unable to connect WooCommerce : updateOrderStatus"
                coreResponse["response"] = response.json()
                return coreResponse
        except Platform.DoesNotExist:
            coreResponse["msg"] = "Platform not found while updating WooCommerce order"
            return coreResponse
        except Exception as err:
            coreResponse["msg"] = f"Unexpected updateOrderStatus {err=}, {type(err)=}"
            print(f"Unexpected updateOrderStatus {err=}, {type(err)=}")
            return coreResponse
        
# +++++++++++++++++ Store TIming Section +++++++++++++++++    
    def get_store_timings(vendorId):
        platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
        catlogHeaders = {
            "Content-Type": "application/json"
        }
        # https://www.letsunify.in:3003/wp-json/custom/v1/get-store-time-table
        url = platform.baseUrl + "wp-json/custom/v1/get-store-time-table"
        wooResponse = requests.request("GET", url, headers=catlogHeaders)
        return wooResponse
    def set_store_timings(vendorId,day):
        wooResponse = WooCommerce.get_store_timings(vendorId)
        platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
        catlogHeaders = {
            "Content-Type": "application/json"
        }
        print(wooResponse)
        if wooResponse.status_code == 200:
            slot_id = None
            Days = wooResponse.json()
            if type(Days) is list:
                for singleDay in Days:
                    if singleDay.get('slot_identity') == day.slot_identity:
                        slot_id = singleDay.get('slot_id')
            body = {
                    "slot_identity": day.slot_identity,
                    "day":day.day,
                    "holiday": 1 if day.is_holiday else 0,
                    "open_time": "00:00" if day.is_holiday else day.open_time.strftime('%H:%M'),
                    "close_time": "00:00" if day.is_holiday else day.close_time.strftime('%H:%M'),
                    "active_disable": 1 if day.is_active else 0
                }
            print(slot_id)
            print(body)
            if slot_id:
                # https://www.letsunify.in:3003/wp-json/custom/v1/update-storetime-record/2
                url = platform.baseUrl + "wp-json/custom/v1/update-storetime-record/" +slot_id
                wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(body))
                jsonData=wooResponse.json()
            else:
                url = platform.baseUrl + "wp-json/custom/v1/insert-store-time-record"
                wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(body))
                jsonData=wooResponse.json()
            return jsonData
                
    def delete_store_timings(vendorId,day):
        try:
            wooResponse = WooCommerce.get_store_timings(vendorId)
            platform = Platform.objects.get(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE)
            catlogHeaders = {
                "Content-Type": "application/json"
            }
            if wooResponse.status_code == 200:
                Days = wooResponse.json()
                for singleDay in Days:
                    if singleDay.get('day') == day.day:
                        body = {
                                "slot_id":singleDay.get('slot_id')
                            }
                        url = platform.baseUrl + "wp-json/custom/v1/delete-store-time-record/"+singleDay.get('slot_id')
                        wooResponse = requests.request("POST", url, headers=catlogHeaders,data=json.dumps(body))
            #             jsonData=wooResponse.json()
            # return jsonData
        except Exception as e:
            print(e)

    def get_customer_by_phone_number(phone_number, vendorId):
        platform = Platform.objects.filter(VendorId=vendorId, corePlatformType=CorePlatform.WOOCOMMERCE).first()

        if platform:
                # https://www.letsunify.in:3003/wp-json/custom/v1/customer-by-phone?phone_number=123456789
                url = platform.baseUrl + f"wp-json/custom/v1/customer-by-phone?phone_number={phone_number}"

                woocommerce_response = requests.request("GET", url, headers={"Content-Type": "application/json"})

                return woocommerce_response
            
        else:
            return None

    def get_loyalty_program_settings(vendor_id):
        platform = Platform.objects.filter(VendorId=vendor_id, corePlatformType=CorePlatform.WOOCOMMERCE).first()

        if platform:
            # https://www.letsunify.in:3003/wp-json/rewapoint/v1/settings
            url = platform.baseUrl + "wp-json/rewapoint/v1/settings"

            woocommerce_response = requests.request("GET", url, headers={"Content-Type": "application/json"})

            return woocommerce_response
        
        else:
            return None
    
    def update_loyalty_program_settings(vendor_id, loyalty_program_settings):
        synced = False

        platform = Platform.objects.filter(VendorId=vendor_id, corePlatformType=CorePlatform.WOOCOMMERCE).first()

        if platform:
            try:
                woocommerce_response = WooCommerce.get_loyalty_program_settings(vendor_id)
                print(woocommerce_response)

                if woocommerce_response and woocommerce_response.status_code == 200:
                    response_json = woocommerce_response.json()
                    print(response_json)

                    if response_json.get('points_to_amount') and response_json['points_to_amount']['id'] and \
                    response_json.get('amount_to_points') and response_json['amount_to_points']['id'] and \
                    response_json.get('settings') and response_json['settings']['rewa_expiry']:
                        
                        if loyalty_program_settings:
                            api_headers = {"Content-Type": "application/json"}

                            points_to_amount_status = False

                            is_program_active = 0
                            
                            if loyalty_program_settings.is_active == True:
                                is_program_active = 1

                            request_body = {
                                "points": 1,
                                "amount":loyalty_program_settings.unit_point_value_in_rupees,
                                "operation": "points_amount",
                                "rewa_expiry": loyalty_program_settings.points_expiry_days,
                                "loyalty_program": is_program_active,
                                "max_point": loyalty_program_settings.redeem_limit_in_percentage
                            }

                            url = platform.baseUrl + f"wp-json/rewapoint/v1/update-settings/{response_json['points_to_amount']['id']}"

                            points_to_amount_response = requests.request("PUT", url, headers=api_headers, data=json.dumps(request_body))
                            
                            if points_to_amount_response.status_code == 200:
                                points_to_amount_status = True

                            amount_to_points_status = False
                            
                            request_body = {
                                "points": 1,
                                "amount":loyalty_program_settings.amount_spent_in_rupees_to_earn_unit_point,
                                "operation": "amount_points"
                                # "rewa_expiry": loyalty_program_settings.points_expiry_days,
                                # "loyalty_program": is_program_active,
                                # "max_point": loyalty_program_settings.redeem_limit_in_percentage
                            }

                            url = platform.baseUrl + f"wp-json/rewapoint/v1/update-settings/{response_json['amount_to_points']['id']}"

                            amount_to_points_response = requests.request("PUT", url, headers=api_headers, data=json.dumps(request_body))
                            
                            if amount_to_points_response.status_code == 200:
                                amount_to_points_status = True

                            if (points_to_amount_status == True) and (amount_to_points_status == True):
                                synced = True
                                return synced
                            
                            else:
                                return synced
                            
                        else:
                            print("Did not find loyalty point settings")
                            return synced
                            
                    else:
                        print("Got invalid response from WooCommerce")
                        return synced
                
            except Exception as err:
                print(f"Unexpected error in get_loyalty_program_settings(): {err=}, {type(err)=}")
                return synced
            
        else:
            return synced
    
    def get_loyalty_points_balance_of_customer(customer_id, vendor_id):
        platform = Platform.objects.filter(VendorId=vendor_id, corePlatformType=CorePlatform.WOOCOMMERCE).first()

        if platform:
            # https://www.letsunify.in:3003/wp-json/rewapoint/v1/get-user-points/1
            url = platform.baseUrl + f"wp-json/rewapoint/v1/get-user-points/{customer_id}"

            woocommerce_response = requests.request("GET", url, headers={"Content-Type": "application/json"})

            return woocommerce_response
        
        else:
            return None
        
    def update_loyalty_points_balance_of_customer(customer_id, points, vendor_id):
        synced = False

        platform = Platform.objects.filter(VendorId=vendor_id, corePlatformType=CorePlatform.WOOCOMMERCE).first()

        if platform:
            try:
                woocommerce_response = WooCommerce.get_loyalty_points_balance_of_customer(customer_id, vendor_id)
                print(woocommerce_response)

                if woocommerce_response and woocommerce_response.status_code == 200:
                    response_json = woocommerce_response.json()
                    print(response_json)

                    if response_json.get('user_id') and response_json.get('points'):
                            request_body = {
                                "user_id": response_json.get('user_id'),
                                "points": points
                            }

                            # https://www.letsunify.in:3003/wp-json/rewapoint/v1/update-user-points
                            url = platform.baseUrl + "wp-json/rewapoint/v1/update-user-points"

                            update_response = requests.request("PUT", url, headers={"Content-Type": "application/json"}, data=json.dumps(request_body))
                            
                            if update_response.status_code == 200:
                                synced = True
                                return synced
                
            except Exception as err:
                print(f"Unexpected error in update_loyalty_points_balance_of_customer(): {err=}, {type(err)=}")
                return synced
            
        else:
            return synced
