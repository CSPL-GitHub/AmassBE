from core.POS_INTEGRATION.abstract_pos_integration import AbstractPOSIntegration
from core.PLATFORM_INTEGRATION.woms_ecom import WomsEcom
from core.PLATFORM_INTEGRATION.woocommerce_ecom import WooCommerce
from core.models import (
    Platform, ProductCategory, ProductImage, ProductModifier, Product, ProductCategoryJoint, ProductModifierGroup,
    Product_Option, Product_Option_Value, Product_Tax, Product_Taxt_Joint, Vendor, Transaction_History, Product_Option_Joint,
    ProductAndModifierGroupJoint
)
from order.models import Address, Customer, CustomerPaymentProfile, Order, Order_Discount, OrderItem, OrderItemModifier, OrderPayment
from core.utils import API_Messages, DiscountCal, OrderStatus, OrderType, PaymentType, TaxLevel, UpdatePoint, send_order_confirmation_email
from koms.models import Order as KOMSorder
from core.models import EmailLog
from megameal.settings import EMAIL_HOST_USER
from django.conf import settings
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from rest_framework.response import Response
from core.models import POS_Settings
from django.utils import timezone
from datetime import datetime
from logging import log



class StagingIntegration(AbstractPOSIntegration):
    def menuPushtread(vendorId, response):
        # ++++ pick all the channels of vendor
        try:
            platforms = Platform.objects.filter(
                VendorId=vendorId, isActive=True, autoSyncMenu=True)
            oldMenu = Transaction_History.objects.filter(
                vendorId_id=vendorId, transactionType="MENU").order_by("-createdAt").first()
            for platform in platforms:
                platformOBJ = globals()[platform.className]
                response = platformOBJ.pushMenu(platform, oldMenu)
        except Platform.DoesNotExist:
            print("Channel Not Found")
        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")

    def pushProducts(self, VendorId, response):
        vendor = Vendor.objects.get(id=VendorId)
        # +++++ Get old Products
        try:
            oldMenu = Transaction_History.objects.filter(
                vendorId=VendorId, transactionType="MENU").order_by("-createdAt").first()
        except Transaction_History.DoesNotExist:
            print("No Menu Found")

        # ++++++++ Insert Update category in Core
        oldCats = {} if oldMenu is None else oldMenu.transactionData.get(
            "category")
        for coreCat in response["category"]:
            coreCat = response["category"][coreCat]
            # ++++++++ If its available in old Cats
            if oldCats:
                print(coreCat)
                if coreCat["plu"] in oldCats:
                    del oldCats[coreCat["plu"]]
            # ++++++++

            self.saveUpdateCategory(coreCat=coreCat, vendor=vendor)
        # +++++++++++ Delete Categories
        for deletedCat in oldCats:
            deletedCat = oldCats[deletedCat]
            self.deleteCategory(coreCat=deletedCat, vendor=vendor)
        # +++++++++ End Category Update

        # +++++ Product Insert Update
        oldPrds = {} if oldMenu is None else oldMenu.transactionData.get(
            "products")
        for corePrd in response["products"]:
            corePrd = response["products"][corePrd]
            # ++++++++ If its available in old Cats
            if oldPrds:
                print(corePrd)
                if corePrd["PLU"] in oldPrds:
                    del oldPrds[corePrd["PLU"]]
            # ++++++++
            self.saveUpdateProduct(corePrd, vendor)

        # +++++++++++ Delete products
        for deletedPrd in oldPrds:
            deletedPrd = oldPrds[deletedPrd]
            self.deleteProduct(deletedPrd, vendor)
        # +++++++++ End Product Insert Update

        # ++++++++ Product Option
        oldPrdOptions = {} if oldMenu is None else oldMenu.transactionData.get(
            "productOptions")
        for corePrdOptions in response["productOptions"]:
            corePrdOptions = response["productOptions"][corePrdOptions]
            # ++++++++ If its available in old Cats
            if oldPrdOptions:
                print(oldPrdOptions)
                if corePrdOptions["id"] in oldPrdOptions:
                    del oldPrdOptions[corePrdOptions["id"]]
            # ++++++++
            self.saveUpdateOption(corePrdOptions=corePrdOptions, vendor=vendor)
        # +++++++++++ Delete option
        for deletedOpt in oldPrdOptions:
            deletedOpt = oldPrdOptions[deletedOpt]
            self.deleteOption(corePrdOptions=deletedOpt, vendor=vendor)
        # ++++++++ End Product Option

        # ++++++++ Product Option Value
        oldPrdOptVal = {} if oldMenu is None else oldMenu.transactionData.get(
            "productOptionsVal")
        for corePrdOptVal in response["productOptionsVal"]:
            corePrdOptVal = response["productOptionsVal"][corePrdOptVal]
            # ++++++++ If its available in old Cats
            if oldPrdOptVal:
                print(oldPrdOptVal)
                if corePrdOptVal["id"] in oldPrdOptVal:
                    del oldPrdOptVal[corePrdOptVal["id"]]
            # ++++++++
            self.saveUpdateOptionValue(
                corePrdOptVal=corePrdOptVal, vendor=vendor)

        # +++++++++++ Delete option
        for deletedOptVal in oldPrdOptVal:
            deletedOptVal = oldPrdOptVal[deletedOptVal]
            self.deleteOptionValue(corePrdOptVal=deletedOptVal,vendor=vendor)

        # ++++++++ End Product Option Value

        # +++++ Variation Product Insert Update
        oldVrts = {} if oldMenu is None else oldMenu.transactionData.get(
            "varinats")
        for coreVrt in response["varinats"]:
            coreVrt = response["varinats"][coreVrt]
            # ++++++++ If its available in old variation
            if oldVrts:
                print(coreVrt)
                if coreVrt["PLU"] in oldVrts:
                    del oldVrts[coreVrt["PLU"]]
            # ++++++++
            self.saveUpdateVariant(coreVrt, vendor)

        # +++++++++++ Delete Variations
        for deletedVrt in oldVrts:
            deletedVrt = oldVrts[deletedVrt]
            self.deleteVariant(coreVrt, vendor)
        # +++++++++ End Variation Product Insert Update

        # ++++++++ Product Modifier Group
        oldModGrp = {} if oldMenu is None else oldMenu.transactionData.get(
            "modifiersGroup")
        for coreModGrp in response["modifiersGroup"]:
            coreModGrp = response["modifiersGroup"][coreModGrp]
            # ++++++++ If its available in old ModGrp
            if oldModGrp:
                if coreModGrp["id"] in oldModGrp:
                    del oldModGrp[coreModGrp["id"]]
            # ++++++++
            self.saveUpdateModifierGroup(coreModGrp=coreModGrp, vendor=vendor)
        # +++++++++++ Delete Product Modifier Group
        for deletedModGrp in oldModGrp:
            deletedModGrp = oldModGrp[deletedModGrp]
            self.deleteModifierGroup(
                coreModGrp=deletedModGrp, vendor=vendor)
        # ++++++++ End Product Modifier Group

        # +++++++++ Modifier Insert Update
        oldModItm = {} if oldMenu is None else oldMenu.transactionData.get(
            "modifiers")
        # coreModDelete = []
        for coreModItm in response["modifiers"]:
            coreModItm = response["modifiers"][coreModItm]
            # ++++++++ If its available in old Cats
            if oldModItm:
                if coreModItm["id"] in oldModItm:
                    del oldModItm[coreModItm["id"]]
            # ++++++++
            self.saveUpdateModifierItem(coreModItm=coreModItm, vendor=vendor)
        # +++++++++++ Delete Product Modifier Group
        for deletedModItm in oldModItm:
            deletedModItm = oldModItm[deletedModItm]
            self.deleteModifierItem(coreModItm=deletedModItm, vendor=vendor)
        # +++++++++ End Modifier Insert Update

        # +++++++++ Product Tax
        oldTax = {} if oldMenu is None else oldMenu.transactionData.get(
            "taxes")
        coreTaxDelete = []
        for coreTax in response["taxes"]:
            coreTax = response["taxes"][coreTax]

            # ++++++++ If its available in old Taxes
            if oldTax:
                if coreTax["id"] in oldTax:
                    del oldTax[coreTax["id"]]
            # ++++++++

            try:
                cat = Product_Tax.objects.get(
                    posId=coreTax["id"], vendorId=vendor)
                cat.isDeleted = False
                cat.name = coreTax["taxName"]
                cat.percentage = coreTax["percentage"]
                cat.taxLevel = TaxLevel.get_Tax_Level_value(
                    coreTax["taxLevel"])
                cat.enabled = True
                cat.save()
            except Product_Tax.DoesNotExist:
                cat = Product_Tax(
                    vendorId=vendor,
                    isDeleted=False,
                    name=coreTax["taxName"],
                    percentage=coreTax["percentage"],
                    taxLevel=TaxLevel.get_Tax_Level_value(coreTax["taxLevel"]),
                    enabled=True,
                    posId=coreTax["id"]
                )
                cat.save()
        # +++++++++++ Delete tax
        if oldTax:
            for deletedTax in oldTax:
                deletedTax = oldTax[deletedTax]
                try:
                    cat = Product_Tax.objects.get(
                        posId=deletedTax["id"], vendorId=vendor)
                    cat.isDeleted = True
                    coreTaxDelete.append(cat)
                except Product_Tax.DoesNotExist:
                    print("Tax not found to delete")
        Product_Tax.objects.bulk_update(coreTaxDelete, ["isDeleted"])

        # updating tax joints
        for prdPlu in response["taxesJnt"]:
            try:
                prd = Product.objects.get(vendorId=vendor, PLU=prdPlu)
                Product_Taxt_Joint.objects.filter(
                    vendorId=vendor, productId=prd).delete()
                for taxId in response["taxesJnt"][prdPlu]:
                    tx = Product_Tax.objects.get(vendorId=vendor, posId=taxId)
                    Product_Taxt_Joint(
                        vendorId=vendor,
                        productId=prd,
                        taxId=tx
                    ).save()

            except Product_Taxt_Joint.DoesNotExist:
                print("Tax not found")
            except Product_Tax.DoesNotExist:
                print("Tax not found")
            except Product.DoesNotExist:
                print("Product not found")

        # +++++++++ End Tax Insert Update

        # +++++++++++ Product ModifierGroup Joint
        for productId in response["modGrpPrdJoint"]:
            self.saveUpdateDeleteModifierGroupProductJoint(productId, response["modGrpPrdJoint"][productId], vendor)

        self.saveTransaction(
            vendorId=VendorId, coreResponse=response, tracType='MENU')
        # +++++++++++ End Product ModifierGroup Joint

    def pullProducts(self, request):
        # ++++++++++ request data
        data = request

        # +++++ response template
        coreResponse = {
            "status": "Error",
            "msg": "Something went wrong"
        }

        # ++++ pick all the channels of vendor
        try:
            platform = POS_Settings.objects.get(VendorId=data['vendorId'])
        except POS_Settings.DoesNotExist:
            coreResponse["msg"] = "POS settings not found"
            return Response(coreResponse, status=400)

        try:
            posService = globals()[platform.className]
            response = posService.pullProducts(platform.VendorId.pk)
            self.pushProducts(platform.VendorId.pk, response["response"])
            coreResponse["status"]=API_Messages.SUCCESSFUL
            coreResponse["msg"]=API_Messages.SUCCESSFUL
            # +++++ Push Menu to externalWbhooks

            # TODO Temp command
            import threading
            thr = threading.Thread(
                target=StagingIntegration.menuPushtread,
                args=(),
                kwargs={"vendorId": platform.VendorId.pk, "response": response["response"]})
            thr.setDaemon(True)
            thr.start()

            # ++++++++++++
            if response:
                return Response(response, status=200)
            coreResponse["msg"] = "Service Found"
            return Response("Done", status=200)
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            return Response(coreResponse, status=500)

    def saveTransaction(self, vendorId, coreResponse, tracType):
        try:
            transaction_History = Transaction_History(vendorId=Vendor.objects.get(
                pk=vendorId), transactionData=coreResponse, createdAt=datetime.now(), transactionType=tracType)
            transaction_History.save()
        except Vendor.DoesNotExist:
            pass

    def saveUpdateCategory(self, coreCat, vendor):
        catParentId = None
        if coreCat["parentId"] != -1:
            catParentId = coreCat["parentId"]

        try:
            cat = ProductCategory.objects.get(
                categoryPLU=coreCat["plu"], vendorId=vendor)
            cat.categoryName = coreCat["categoryName"]
            # cat.categorySlug = slugify(coreCat["categoryName"]) Bug Fix for update
            cat.categoryParentId = catParentId
            cat.categoryDescription = coreCat["description"]
            cat.categoryStatus = coreCat["status"]
            cat.categorySortOrder = coreCat["sortOrder"]
            cat.categoryImage = coreCat["image"]
            cat.categoryUpdatedAt = timezone.make_aware(
                datetime.now(), timezone.utc)
            cat.save()
        except ProductCategory.DoesNotExist:
            cat = ProductCategory(categoryName=coreCat["categoryName"],
                                   categorySlug=slugify(
                                       coreCat["categoryName"]),
                                   categoryParentId=catParentId,
                                   categoryDescription=coreCat["description"],
                                   categoryStatus=coreCat["status"],
                                   categorySortOrder=coreCat["sortOrder"],
                                   categoryImage=coreCat["image"],
                                   categoryCreatedAt=timezone.make_aware(
                                       datetime.now(), timezone.utc),
                                   categoryUpdatedAt=timezone.make_aware(
                                       datetime.now(), timezone.utc),
                                   categoryPLU=coreCat["plu"],
                                   vendorId=vendor)
            cat.save()

    def deleteCategory(self, coreCat, vendor):
        try:
            cat = ProductCategory.objects.get(
                categoryPLU=coreCat["plu"], vendorId=vendor)
            cat.categoryIsDeleted = True
            cat.save()
        except ProductCategory.DoesNotExist:
            print("Category not found to delete")

    def saveUpdateProduct(self, corePrd, vendor):
        if corePrd.get("description") == None:
            corePrd["description"] = ""

        try:
            cat = Product.objects.get(
                PLU=corePrd["PLU"], vendorId=vendor)
            cat.productName = corePrd["productName"]
            cat.productDesc = corePrd["description"]
            cat.productThumb = corePrd["thumbnail"]
            cat.productQty = corePrd["qty"]
            cat.productPrice = corePrd["price"]
            cat.Unlimited = corePrd["unlimited"]
            cat.productStatus = corePrd["productStatus"]
            cat.vendorId = vendor
            cat.preparationTime = corePrd["preparationTime"]
            cat.taxable = corePrd["taxable"]
            cat.productType = corePrd["type"]
            cat.SKU = corePrd.get("sku")
            cat.meta = corePrd.get("meta")
            cat.save()
        except Product.DoesNotExist:
            cat = Product(
                PLU=corePrd["PLU"],
                productName=corePrd["productName"],
                productDesc=corePrd["description"],
                productThumb=corePrd["thumbnail"],
                productQty=corePrd["qty"],
                productPrice=corePrd["price"],
                Unlimited=corePrd["unlimited"],
                productStatus=corePrd["productStatus"],
                vendorId=vendor,
                preparationTime=corePrd["preparationTime"],
                taxable=corePrd["taxable"],
                SKU=corePrd.get("sku"),
                meta=corePrd.get("meta"),
                productType=corePrd["type"])
            cat = cat.save()
        # ++++++++ save images
        for saveImg in corePrd["images"]:
            try:
                ProductImage.objects.filter(product=cat).delete()
            except ProductImage.DoesNotExist:
                print("Images not found for product")
            ProductImage(product=cat, url=saveImg).save()

        # Deleting all the links of product and category
        try:
            deleteLinks = ProductCategoryJoint.objects.get(product=cat)
            deleteLinks.delete()
        except ProductCategoryJoint.DoesNotExist:
            print("Link not found")

        # Creating links
        for catLink in corePrd["parentId"]:
            try:
                linkCat = ProductCategory.objects.get(categoryPLU=catLink,vendorId=vendor)
                ProductCategoryJoint.objects.create(
                    category=linkCat, product=cat)
            except ProductCategory.DoesNotExist:
                continue

    def deleteProduct(self, corePrd, vendor):
        try:
            cat = Product.objects.get(
                PLU=corePrd["PLU"], vendorId=vendor)
            cat.isDeleted = True
            cat.save()
        except Product.DoesNotExist:
            print("Product not found to delete")

    def saveUpdateVariant(self, coreVrt, vendor):
        # ++++++ Base Product
        try:
            baseProduct = Product.objects.get(
                PLU=coreVrt["baseProductId"], vendorId=vendor)
        except Product.DoesNotExist:
            return
        # ++++++ Base Product

        if coreVrt.get("description") == None:
            coreVrt["description"] = ""

        try:
            cat = Product.objects.get(
                PLU=coreVrt["PLU"], vendorId=vendor)
            cat.productName = coreVrt["productName"]
            cat.productDesc = coreVrt["description"]
            cat.productThumb = coreVrt["thumbnail"]
            cat.productQty = coreVrt["qty"]
            cat.productPrice = coreVrt["price"]
            cat.Unlimited = coreVrt["unlimited"]
            cat.productStatus = coreVrt["productStatus"]
            cat.vendorId = vendor
            cat.preparationTime = coreVrt["preparationTime"]
            cat.taxable = coreVrt["taxable"]
            cat.productType = coreVrt["type"]
            cat.productParentId = baseProduct
            cat.sortOrder = coreVrt["sortOrder"]
            cat.SKU = coreVrt.get("sku")
            cat.save()
        except Product.DoesNotExist:
            cat = Product(
                PLU=coreVrt["PLU"],
                productName=coreVrt["productName"],
                productDesc=coreVrt["description"],
                productThumb=coreVrt["thumbnail"],
                productQty=coreVrt["qty"],
                productPrice=coreVrt["price"],
                Unlimited=coreVrt["unlimited"],
                productStatus=coreVrt["productStatus"],
                vendorId=vendor,
                preparationTime=coreVrt["preparationTime"],
                taxable=coreVrt["taxable"],
                productType=coreVrt["type"],
                productParentId=baseProduct,
                SKU=coreVrt.get("sku"),
                sortOrder=coreVrt["sortOrder"]
            )
            cat = cat.save()
        # +++++ delete old joints and add New
        try:
            deleteLinks = Product_Option_Joint.objects.filter(
                productId=cat)
            deleteLinks.delete()
        except Product_Option_Joint.DoesNotExist:
            print("Link not found")
        # +++++ End delete old joints and add New

        # Creating links
        for catLink in coreVrt["option"]:
            try:
                # linkOpt=Product_Option.objects.get(optionId=catLink["productOptionId"])
                linkOptVal = Product_Option_Value.objects.get(
                    itemOptionId=catLink["productOptionVal"])
                Product_Option_Joint.objects.create(
                    vendorId=vendor,
                    productId=cat,
                    optionId=linkOptVal.optionId,
                    optionValueId=linkOptVal
                )
            except Product_Option_Value.DoesNotExist:
                print("Option Value not found")
                continue
        # Creating links

    def deleteVariant(self, coreVrt, vendor):
        try:
            cat = Product.objects.get(
                PLU=coreVrt["PLU"], vendorId=vendor)
            cat.isDeleted = True
            cat.save()
        except Product.DoesNotExist:
            print("Product not found to delete")

    def saveUpdateModifierGroup(self, coreModGrp, vendor):
        try:
            cat = ProductModifierGroup.objects.get(
                PLU=coreModGrp["id"], vendorId=vendor)
            cat.name = coreModGrp["modifierGroupName"]
            cat.min = 0
            cat.max = 0
            cat.isDeleted = False
            cat.sortOrder = coreModGrp["sortOrder"]
            cat.modGrptype = coreModGrp["type"]
            # coreModGrpUpdate.append(cat)
        except ProductModifierGroup.DoesNotExist:
            cat = ProductModifierGroup(
                PLU=coreModGrp["id"],
                slug=slugify(coreModGrp["modifierGroupName"]),
                name=coreModGrp["modifierGroupName"],
                min=0,
                max=0,
                isDeleted=False,
                sortOrder=coreModGrp["sortOrder"],
                modGrptype=coreModGrp["type"],
                vendorId=vendor)
        cat.save()

    def deleteModifierGroup(self, coreModGrp, vendor):
        try:
            cat = ProductModifierGroup.objects.get(
                PLU=coreModGrp["id"], vendorId=vendor)
            cat.isDeleted = True
            cat.save()
            # coreModGrpDelete.append(cat)
        except ProductModifierGroup.DoesNotExist:
            print("Mod Grp not found to delete")

    def saveUpdateModifierItem(self, coreModItm, vendor):
        try:
            modGrp = ProductModifierGroup.objects.get(
                PLU=coreModItm["parentId"], vendorId=vendor)
        except ProductModifierGroup.DoesNotExist:
            return

        try:
            cat = ProductModifier.objects.get(
                modifierPLU=coreModItm["id"], vendorId=vendor)
            cat.modifierName = coreModItm["modifierName"]
            cat.modifierImg = coreModItm["image"]
            cat.modifierPrice = coreModItm["price"]
            cat.modifierDesc = coreModItm["description"]
            cat.modifierQty = coreModItm["qty"]
            cat.modifierStatus = coreModItm["modifierStatus"]
            cat.vendorId = vendor
            cat.paretId = modGrp
            cat.save()
        except ProductModifier.DoesNotExist:
            cat = ProductModifier(
                modifierPLU=coreModItm["id"],
                modifierSKU=coreModItm.get("sku") if coreModItm.get("sku") else str(coreModItm["id"]),
                modifierName=coreModItm["modifierName"],
                modifierImg=coreModItm["image"],
                modifierPrice=coreModItm["price"],
                modifierDesc=coreModItm["description"],
                modifierQty=coreModItm["qty"],
                modifierStatus=coreModItm["modifierStatus"],
                vendorId=vendor,
                paretId=modGrp)
            cat.save()

    def deleteModifierItem(self, coreModItm, vendor):
        try:
            cat = ProductModifier.objects.get(
                modifierPLU=coreModItm["id"], vendorId=vendor)
            cat.isDeleted = True
            cat.save()
        except ProductModifier.DoesNotExist:
            print("Mod Itm not found to delete")

    def saveUpdateDeleteModifierGroupProductJoint(self, productId, coreModGrpPrdJnt, vendor):
        try:
            prd = Product.objects.get(
                PLU=productId, vendorId=vendor)
        except Product.DoesNotExist:
            print("Product not found")
            return

        try:
            jointLink = ProductAndModifierGroupJoint.objects.filter(product=prd)
            jointLink.delete()
        except ProductAndModifierGroupJoint.DoesNotExist:
            print("Link Not found")

        for modGrpId in coreModGrpPrdJnt:
            dictOfModGrpData = coreModGrpPrdJnt[modGrpId]
            try:
                modGrp = ProductModifierGroup.objects.get(
                    PLU=modGrpId, vendorId=vendor)
            except ProductModifierGroup.DoesNotExist:
                print("Error Modifier Group not found")
                continue
            saveJoint = ProductAndModifierGroupJoint(product=prd, modifierGroup=modGrp, isEnabled=True, min=dictOfModGrpData.get(
                "min"), max=dictOfModGrpData.get("max"))
            saveJoint.save()

    def saveUpdateOption(self, corePrdOptions, vendor):
        try:
            cat = Product_Option.objects.get(
                optionId=corePrdOptions["id"], vendorId=vendor)
            cat.name = corePrdOptions["productOptionName"]
            cat.save()
        except Product_Option.DoesNotExist:
            cat = Product_Option(
                name=corePrdOptions["productOptionName"],
                optionId=corePrdOptions["id"],
                isDeleted=False,
                vendorId=vendor)
            cat.save()

    def deleteOption(self, corePrdOptions, vendor):
        try:
            cat = Product_Option.objects.get(
                optionId=corePrdOptions["id"], vendorId=vendor)
            cat.isDeleted = True
            cat.save()
        except Product_Option.DoesNotExist:
            print("Option not found to delete")

    def saveUpdateOptionValue(self, corePrdOptVal, vendor):
        try:
            productOption = Product_Option.objects.get(
                optionId=corePrdOptVal["productOptionId"], vendorId=vendor)
        except Product_Option.DoesNotExist:
            return

        try:
            cat = Product_Option_Value.objects.get(
                itemOptionId=corePrdOptVal["id"], vendorId=vendor)
            cat.optionsName = corePrdOptVal["productOptionValName"]
            cat.itemOptionId = corePrdOptVal["id"]
            cat.sortOrder = corePrdOptVal["sortOrder"]
            cat.optionId = productOption
            cat.isDeleted = False
            cat.save()
        except Product_Option_Value.DoesNotExist:
            cat = Product_Option_Value(
                optionsName=corePrdOptVal["productOptionValName"],
                itemOptionId=corePrdOptVal["id"],
                sortOrder=corePrdOptVal["sortOrder"],
                optionId=productOption,
                isDeleted=False,
                vendorId=vendor)
            cat.save()

    def deleteOptionValue(self, corePrdOptVal, vendor):
        try:
            cat = Product_Option_Value.objects.get(
                itemOptionId=corePrdOptVal["id"], vendorId=vendor)
            cat.isDeleted = True
            cat.save()
        except Product_Option_Value.DoesNotExist:
            print("Option Val not found to delete")

# +++++++++++++++++++ Below is Order Section

    def openOrder(self, request):
        # ++++++++++ request data
        data = request
        print(data)
        vendorId = data["vendorId"]

        vendor_instance = Vendor.objects.get(pk=vendorId)

        # +++++ response template
        coreResponse = {
            "status": "Error",
            "msg": "Something went wrong"
        }
        try:
            try:
                if (data["customer"]["phno"] == None) or (data["customer"]["phno"] == ""):
                    coreCustomer = Customer.objects.filter(
                    Phone_Number="0",
                    VendorId=vendorId,
                ).first()
                    
                else:
                    coreCustomer = Customer.objects.filter(
                        Phone_Number=data["customer"]["phno"],
                        VendorId=vendorId,
                    ).first()

                if coreCustomer:
                    if coreCustomer.Phone_Number != '0' or coreCustomer.FirstName != 'Guest':
                        addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first() 
                        
                        if not addrs:
                            if ((data["customer"]["address1"] == None) or (data["customer"]["address1"] == "")) and \
                            ((data["customer"]["address2"] == None) or (data["customer"]["address2"] == "")) and \
                            ((data["customer"]["city"] == None) or (data["customer"]["city"] == "")) and \
                            ((data["customer"]["state"] == None) or (data["customer"]["state"] == "")) and \
                            ((data["customer"]["country"] == None) or (data["customer"]["country"] == "")) and \
                            ((data["customer"]["zip"] == None) or (data["customer"]["zip"] == "")):
                                pass

                            else:
                                addrs = Address.objects.create(
                                    address_line1=data["customer"]["address1"],
                                    address_line2=data["customer"]["address2"],
                                    city=data["customer"]["city"],
                                    state=data["customer"]["state"],
                                    country=data["customer"]["country"],
                                    zipcode=data["customer"]["zip"],
                                    type="shipping_address",
                                    is_selected=True,
                                    customer=coreCustomer
                                )
                
                else:
                    coreCustomer = Customer.objects.create(
                        FirstName=data["customer"]["fname"],
                        LastName=data["customer"]["lname"],
                        Email=data["customer"]["email"],
                        Phone_Number=data["customer"]["phno"],
                        VendorId=vendor_instance
                    )

                    if coreCustomer.Phone_Number != '0' or coreCustomer.FirstName != 'Guest':    
                        if ((data["customer"]["address1"] == None) or (data["customer"]["address1"] == "")) and \
                        ((data["customer"]["address2"] == None) or (data["customer"]["address2"] == "")) and \
                        ((data["customer"]["city"] == None) or (data["customer"]["city"] == "")) and \
                        ((data["customer"]["state"] == None) or (data["customer"]["state"] == "")) and \
                        ((data["customer"]["country"] == None) or (data["customer"]["country"] == "")) and \
                        ((data["customer"]["zip"] == None) or (data["customer"]["zip"] == "")):
                            pass

                        else:
                            addrs = Address.objects.create(
                                address_line1=data["customer"]["address1"],
                                address_line2=data["customer"]["address2"],
                                city=data["customer"]["city"],
                                state=data["customer"]["state"],
                                country=data["customer"]["country"],
                                zipcode=data["customer"]["zip"],
                                type="shipping_address",
                                is_selected=True,
                                customer=coreCustomer
                            )

            except Exception as esasd:
                print(esasd)

                if (data["customer"]["phno"] == None) or (data["customer"]["phno"] == ""):
                    coreCustomer = Customer.objects.filter(
                        Phone_Number="0",
                        VendorId=vendorId,
                    ).first()
                    
                else:
                    coreCustomer = Customer.objects.filter(
                        Phone_Number=data["customer"]["phno"],
                        VendorId=vendorId,
                    ).first()

                if coreCustomer:
                    if coreCustomer.Phone_Number != '0' or coreCustomer.FirstName != 'Guest':
                        addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first() 
                            
                        if not addrs:
                            if ((data["customer"]["address1"] == None) or (data["customer"]["address1"] == "")) and \
                            ((data["customer"]["address2"] == None) or (data["customer"]["address2"] == "")) and \
                            ((data["customer"]["city"] == None) or (data["customer"]["city"] == "")) and \
                            ((data["customer"]["state"] == None) or (data["customer"]["state"] == "")) and \
                            ((data["customer"]["country"] == None) or (data["customer"]["country"] == "")) and \
                            ((data["customer"]["zip"] == None) or (data["customer"]["zip"] == "")):
                                pass

                            else:
                                addrs = Address.objects.create(
                                    address_line1=data["customer"]["address1"],
                                    address_line2=data["customer"]["address2"],
                                    city=data["customer"]["city"],
                                    state=data["customer"]["state"],
                                    country=data["customer"]["country"],
                                    zipcode=data["customer"]["zip"],
                                    type="shipping_address",
                                    is_selected=True,
                                    customer=coreCustomer
                                )
                
                else:
                    coreCustomer = Customer.objects.create(
                        FirstName=data["customer"]["fname"],
                        LastName=data["customer"]["lname"],
                        Email=data["customer"]["email"],
                        Phone_Number=data["customer"]["phno"],
                        VendorId=vendor_instance
                    )

                    if coreCustomer.Phone_Number != '0' or coreCustomer.FirstName != 'Guest':
                        addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first() 
                            
                        if not addrs:
                            if ((data["customer"]["address1"] == None) or (data["customer"]["address1"] == "")) and \
                            ((data["customer"]["address2"] == None) or (data["customer"]["address2"] == "")) and \
                            ((data["customer"]["city"] == None) or (data["customer"]["city"] == "")) and \
                            ((data["customer"]["state"] == None) or (data["customer"]["state"] == "")) and \
                            ((data["customer"]["country"] == None) or (data["customer"]["country"] == "")) and \
                            ((data["customer"]["zip"] == None) or (data["customer"]["zip"] == "")):
                                pass

                            else:
                                addrs = Address.objects.create(
                                    address_line1=data["customer"]["address1"],
                                    address_line2=data["customer"]["address2"],
                                    city=data["customer"]["city"],
                                    state=data["customer"]["state"],
                                    country=data["customer"]["country"],
                                    zipcode=data["customer"]["zip"],
                                    type="shipping_address",
                                    is_selected=True,
                                    customer=coreCustomer
                                )
            
            data["customer"]["internalId"] = coreCustomer.pk  # +JSON

            # +++ Customer Payment Profile
            if data.get("payment"):
                try:
                    custPayProfile = CustomerPaymentProfile.objects.get(
                        customerId=coreCustomer,
                        custProfileId=data["payment"]["custProfileId"],
                        custPayProfileId=data["payment"]["custPayProfileId"]
                    )
                except CustomerPaymentProfile.DoesNotExist:
                    try:
                        CustomerPaymentProfile.objects.filter(
                            customerId=coreCustomer).update(isDefault=False)
                    except CustomerPaymentProfile.DoesNotExist:
                        print("Profile Not found")
                    custPayProfile = CustomerPaymentProfile(
                        customerId=coreCustomer,
                        custProfileId=data["payment"]["custProfileId"],
                        custPayProfileId=data["payment"]["custPayProfileId"],
                        payType=data["payment"]["payType"],
                        isDefault=True,
                        lastDigits=data["payment"]["lastDigits"],
                        cardId=data["payment"].get("cardId"),
                        zipcode=data["payment"].get("zipcode"),
                    ).save()
                except Exception as custPayProfileError:
                    print(custPayProfileError)
            # ++++++++++
            
            ##++++++Order Platform
            try:
                orderPoint=Platform.objects.get(VendorId=vendorId, className=data.get("className"))
            except Exception as ex:
                print(f"Unexpected {ex=}, {type(ex)=}")
                orderPoint=None
            
            ##++++++End Order Platform
            discount=0.0
            if data.get("discount"):
                if data.get("discount").get('value'):
                    discount=data.get("discount").get('value')
            order = Order(
                Status=OrderStatus.OPEN,
                TotalAmount=0.0,
                OrderDate=timezone.now(),
                Notes=data.get("note"),
                externalOrderld=data.get("externalOrderId"),
                orderType=OrderType.get_order_type_value(data.get("orderType")),
                arrivalTime=timezone.now(),
                tax=0.0,
                discount=discount,
                tip=0.0,
                delivery_charge=0.0,
                subtotal=0.0,
                customerId=coreCustomer,
                vendorId=vendor_instance,
                platform=orderPoint
            ).save()
            request["internalOrderId"] = order.pk
            request["master_id"] = order.pk
            # +++++++

            # ++++++ Discounts
            # platform = POS_Settings.objects.get(VendorId=vendorId)
            if data.get("discount"):
                try:
                    discount = Order_Discount.objects.get(vendorId=vendorId, discountCode=data["discount"].get("discountCode"))
                    # posService = globals()[platform.className]
                    # posResponse = posService.getDiscount(data)
                    # if posResponse["erroCode"] == 200:
                    data["discount"] = discount.to_dict()
                    # else:
                    #     print("Discount not found in POS")
                except Order_Discount.DoesNotExist:
                    print("Invalid Discount")
                except POS_Settings.DoesNotExist:
                    print("POS settings not found")
            # ++++++

            # +++++++++++ Storing Line Items
            order_details = []

            subtotal = 0.0
            productTaxes = 0.0
            discount = 0.0

            for index, lineItm in enumerate(data["items"]):
                data["item"] = lineItm
                lineRes = self.addLineItem(request)
                if lineRes[API_Messages.STATUS] == API_Messages.ERROR:
                    return lineRes
                
                order_details.append(lineRes.get("item"))
                
                subtotal = subtotal + lineRes["item"].get("subtotal")
                productTaxes = productTaxes+lineRes["item"].get("tax")
                discount = discount+lineRes["item"].get("discount")
                data["items"][index] = lineRes["item"]  # +JSON
            # ++++++++++++ End Store Line Items

            tax = 0

            if 'total_tax' in data['payment']: 
                tax = data.get("payment").get("total_tax")

            elif 'tax' in data:
                tax = data.get("tax")

            else:
                taxes = Product_Tax.objects.filter(enabled=True, vendorId=vendorId)

                if taxes.exists():
                    tax = order.tax+productTaxes

            order.tax = tax
            order.subtotal = subtotal
            # order.tax = order.tax+productTaxes
            order.discount = discount
            order.tip = data["tip"]
            data["subtotal"] = subtotal  # +JSON
            order.TotalAmount=(order.subtotal - order.discount + order.tax + order.delivery_charge)

            # order.subtotal = data.get("subtotal")
            # order.tax = data.get("tax")
            # order.TotalAmount= data.get("finalTotal")

            if order.platform.className == "WooCommerce":
                order.TotalAmount=data["payment"]["payAmount"]
                order.delivery_charge=data["payment"]["shipping_total"]
                order.tax=data["payment"]["total_tax"]
            # data["productLevelTax"] = order.tax  # +JSON
            # +++++ Add order Taxes
            try:
                data["orderLevelTax"] = []
                orderTaxes = Product_Tax.objects.filter(
                    vendorId=vendorId, isDeleted=False, taxLevel=TaxLevel.ORDER, enabled=True
                )
                if orderTaxes:
                    for orderTax in orderTaxes:
                        data["orderLevelTax"].append(orderTax.to_dict())
            except Product_Tax.DoesNotExist:
                print("Tax not found for vendor")
            # +++++ Taxes

            order = order.save()

            # ++++ Payment
            print("++++ Payment")
            if data.get("payment"):
                print("++++ Payment Started")
                OrderPayment(
                    orderId=order,
                    paymentBy=coreCustomer.Email,
                    paymentKey=data["payment"]["payConfirmation"],
                    paid=data["payment"]["payAmount"],
                    due=0.0,
                    tip=data["payment"]["tipAmount"],
                    status=data["payment"].get('default', False),
                    type=data["payment"].get('mode', PaymentType.CASH),
                    platform=data["payment"].get('platform', "")
                ).save()
                Transaction_History(
                    vendorId=vendor_instance,
                    transactionData=data["payment"].get("payData"),
                    createdAt=datetime.now(),
                    transactionType= API_Messages.PAYMENT
                ).save()

            # ++++++++++++

            if ((coreCustomer.Phone_Number != '0') or (coreCustomer.FirstName != 'Guest')) and \
            order.platform.Name == 'WooCommerce':
                tax_details = []
                
                taxes = Product_Tax.objects.filter(enabled=True, vendorId=vendorId)

                if taxes:
                    for tax in taxes:
                        tax_details.append({
                            'name': tax.name,
                            'percentage': tax.percentage,
                            'amount': round(order.subtotal * (tax.percentage / 100), 2)
                        })

                product_details = []
                counter = 1

                for product in order_details:
                    modifiers = product.get("modifiers")

                    modifier_details = []

                    for modifier in modifiers:
                        modifier_details.append({
                            "name": modifier.get("name"),
                            "price": modifier.get("price"),
                            "quantity": modifier.get("quantity"),
                            "amount": round((modifier.get("quantity") * modifier.get("price")), 2),
                        })

                    product_details.append({
                        "counter": counter,
                        "name": product.get("productName"),
                        "price": product.get("price"),
                        "quantity": product.get("quantity"),
                        "amount": round((product.get("quantity") * product.get("price")), 2),
                        "modifiers": modifier_details
                    })

                    counter = counter + 1
                
                sender = EMAIL_HOST_USER
                receiver = coreCustomer.Email

                subject = "Your order confirmed"
                email_body_type = "html"
                
                context = {
                    "order_id": order.pk,
                    "first_name": coreCustomer.FirstName,
                    "full_name": coreCustomer.FirstName + " " + coreCustomer.LastName,
                    "phone_number": coreCustomer.Phone_Number,
                    "email": coreCustomer.Email,
                    "shipping_address": addrs,
                    "product_details": product_details,
                    "subtotal": round(order.subtotal, 2),
                    "discount": round(order.discount, 2),
                    "delivery_charge": round(order.delivery_charge, 2),
                    "tax_details": tax_details,
                    "total_amount": round(order.TotalAmount, 2),
                    "media_url": settings.MEDIA_URL
                }
                
                email_body = render_to_string('email.html', context)
                
                email_status = send_order_confirmation_email(sender, receiver, subject, email_body_type, email_body)

                email_log = EmailLog.objects.create(
                    order=order,
                    sender=sender,
                    receiver=receiver,
                    subject=subject,
                    email_body_type=email_body_type,
                    email_body=email_body,
                    status=email_status,
                    customer=coreCustomer,
                    vendor=vendor_instance
                )

                email_log.save()

            coreResponse["response"] = order.to_dict()
            coreResponse["status"] = API_Messages.SUCCESSFUL
            # ++++++++++ End Stage The Order
        except KeyError as kerr:
            print(f"Unexpected {kerr=}, {type(kerr)=}")
            coreResponse["msg"] = "POS service not found for . Please contact system administrator."
        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(f"Unexpected {err=}, {type(err)=}")
        print(coreResponse)
        return coreResponse

    def addLineItem(self, response):
        # +++++ response template
        coreResponse = {
            API_Messages.STATUS: API_Messages.ERROR,
            "msg": "Something went wrong"
        }
        try:
            vendorId = response["vendorId"]
            coreOrder = Order.objects.get(
                pk=response["internalOrderId"], vendorId=vendorId)
            vendor = Vendor.objects.get(pk=response["vendorId"])
            prdName = ''
            varName = ''
            varPlu = None
            subtotal = 0.0
            try:
                if response["item"].get("variant"):
                    product = Product.objects.get(
                        vendorId=vendorId, PLU=response["item"]["variant"]["plu"])
                    prdName = product.productParentId.productName
                    varName = product.productName
                    varPlu = response["item"].get("variant").get("plu")
                    lineItem = OrderItem.objects.get(
                        vendorId=vendorId, orderId=coreOrder, plu=response["item"]["plu"], variantPlu=response["item"]["variant"]["plu"])
                else:
                    product = Product.objects.get(
                        vendorId=vendorId, PLU=response["item"]["plu"])
                    prdName = product.productName
                    lineItem = OrderItem.objects.get(
                        vendorId=vendorId, orderId=coreOrder, plu=response["item"]["plu"])
            except OrderItem.DoesNotExist:
                lineItem = OrderItem(
                    orderId=coreOrder,
                    vendorId=vendor,
                    productName=prdName,
                    variantName=varName,
                    plu=response["item"]["plu"],
                    variantPlu=varPlu,
                    Quantity=response["item"]["quantity"],
                    price=product.productPrice,
                    tax=0.0,
                    discount=0.0,
                    note=response["item"]["itemRemark"]
                )
            lineItem.Quantity = response["item"]["quantity"]
            subtotal = lineItem.Quantity*lineItem.price
            lineItem = lineItem.save()
            coreResponse["item"] = lineItem.to_dict()
            coreResponse["item"]["modifiers"] = []
            # +++++ Modifiers
            if response["item"].get("modifiers"):
                for mod in response["item"].get("modifiers"):
                    modObj = ProductModifier.objects.get(
                        modifierPLU=mod["plu"], vendorId=vendorId)
                    subtotal = subtotal + lineItem.Quantity * \
                        mod["quantity"] * modObj.modifierPrice
                    orderItemMod = OrderItemModifier(
                        orderItemId=lineItem,
                        name=modObj.modifierName,
                        plu=modObj.modifierPLU,
                        quantity=mod["quantity"],
                        price=modObj.modifierPrice,
                        tax=0.0,
                        discount=0.0,
                    ).save()
                    orderItemModDdict=orderItemMod.to_dict()
                    orderItemModDdict['group']=mod['group']
                    if mod.get("status"):
                        orderItemModDdict["status"]=mod.get("status")
                    coreResponse["item"]["modifiers"].append(
                        orderItemModDdict)

            # ++++++++++ Discount
            if response.get("discount"):
                if response.get("discount")["calType"] == DiscountCal.PERCENTAGE:
                    lineItem.discount = (
                        (subtotal*response.get("discount")["value"])/100)
                else:
                    lineItem.discount = response.get(
                        "discount")["value"]/len(response.get("items"))
                coreResponse["item"]["discount"] = lineItem.discount
                subtotal = subtotal-lineItem.discount
            # ++++++++++

            # ++++++ Sub and Tax
            appliedTaxes = []
            coreResponse["item"]["itemLevelTax"] = []
            try:
                taxForProduct = Product_Taxt_Joint.objects.filter(
                    vendorId=vendor, productId=product)
                if taxForProduct:
                    for taxOfProduct in taxForProduct:
                        appliedTaxes.append(taxOfProduct.taxId)
                        coreResponse["item"]["itemLevelTax"].append(
                            taxOfProduct.taxId.to_dict())
            except Product_Taxt_Joint.DoesNotExist:
                print("No tax found for product")

            try:
                taxForProduct = Product_Tax.objects.filter(
                    vendorId=vendor, isDeleted=False, enabled=True, taxLevel=TaxLevel.ORDER)
                appliedTaxes.extend(list(taxForProduct))
            except Product_Tax.DoesNotExist:
                print("No tax found for order")

            taxTlt = 0.0
            taxPer = 0.0
            for taxOfProduct in appliedTaxes:
                taxTlt = taxTlt + ((subtotal*taxOfProduct.percentage)/100)
                taxPer = taxPer+taxOfProduct.percentage
            lineItem.tax = taxTlt
            lineItem.save()
            coreResponse["item"]["tax"] = taxTlt
            coreResponse["item"]["taxPer"] = taxPer

            coreResponse["item"]["subtotal"] = subtotal+lineItem.discount
            # +++++
            coreResponse[API_Messages.STATUS] = API_Messages.SUCCESSFUL

        except Order.DoesNotExist:
            log(level=1, msg="Order not found")
            coreResponse["msg"] = "Order not found"
        except Product.DoesNotExist:
            log(level=1, msg="Product not found")
            coreResponse["msg"] = "Product not found"
        except Vendor.DoesNotExist:
            log(level=1, msg="Vendor not found")
            coreResponse["msg"] = "Vendor not found"
        except Exception as err:
            log(level=1, msg=f"Unexpected {err=}, {type(err)=}")
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
        return coreResponse

    def addModifier(response):
        pass

    def applyDiscount(response):
        pass

    def payBill(response):
        pass

    def updateOrderStatus(self,request):
     try:
        import  koms.views as koms_views
        orderStatus=OrderStatus.get_order_status_value(request["status"])
        try:
            updateOrderStatus=Order.objects.get(pk=request['orderId'])
        except Exception as err:
            updateOrderStatus=Order.objects.get(externalOrderld=request['orderId'])
        request["externalOrderId"]=updateOrderStatus.externalOrderld
        # if request["updatePoint"]==UpdatePoint.KOMS:
        #     if orderStatus==OrderStatus.COMPLETED:
        #         orderStatus=OrderStatus.PREPARED
        #         request["status"]=OrderStatus.PREPARED.label
        updateOrderStatus.Status=orderStatus
        updateOrderStatus.save()
        if request["updatePoint"]!=UpdatePoint.KOMS:
            if request["updatePoint"]==UpdatePoint.WOOCOMERCE:
                order=KOMSorder.objects.filter(externalOrderId=updateOrderStatus.pk)    
                if orderStatus==OrderStatus.COMPLETED:
                    order.update(order_status=3)
                if orderStatus==OrderStatus.CANCELED:
                    order.update(order_status=5)
                if orderStatus==OrderStatus.OPEN:
                    order.update(order_status=1)
                for i in order:
                    koms_views.waiteOrderUpdate(orderid=i.pk,vendorId=i.vendorId.pk)
            print('KOMS update')
        return {API_Messages.STATUS:API_Messages.SUCCESSFUL,API_Messages.RESPONSE:"Order status updated"}
     except Exception as err:
        return {API_Messages.STATUS:API_Messages.ERROR,API_Messages.RESPONSE:f"Unexpected {err=}, {type(err)=}"}

    def getOrder(self,request):
        pass
    # def updateOrderStatusFromWooCommerce(self,request):
    #   try:
    #     updateOrderStatus=Order.objects.get(pk=request['orderId'])
    #     request["externalOrderId"]=updateOrderStatus.externalOrderld
    #     if request["updatePoint"]==UpdatePoint.KOMS:
    #         if orderStatus==OrderStatus.COMPLETED:
    #             orderStatus=OrderStatus.PREPARED
    #             request["status"]=OrderStatus.PREPARED.label
    #     updateOrderStatus.Status=orderStatus
    #     updateOrderStatus.save()
    #     return {API_Messages.STATUS:API_Messages.SUCCESSFUL,API_Messages.RESPONSE:"Order status updated"}
    #   except Exception as err:
    #     return {API_Messages.STATUS:API_Messages.ERROR,API_Messages.RESPONSE:f"Unexpected {err=}, {type(err)=}"}