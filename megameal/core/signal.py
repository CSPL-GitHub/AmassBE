from koms.views import notify
from core.PLATFORM_INTEGRATION.woocommerce_ecom import WooCommerce
from core.utils import Short_Codes
from django.db.models.signals import post_save , pre_delete
from django.dispatch import receiver
from core.models import *

# Category signals start #################################################################

# @receiver(post_save, sender=ProductCategory)
# def product_category_post_save(sender, instance, created, **kwargs):
#     response = WooCommerce.getCategoryUsingSlug(instance.categorySlug, instance.vendorId)
#     if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
#         catCreateRes = WooCommerce.createCategory(instance, instance.vendorId)
#         print(f"Product Category '{instance.categoryName}' created. response::{catCreateRes}")
#     elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         catCreateRes = WooCommerce.updateCategory(instance,response["response"].get("id"), instance.vendorId)
#         print(f"Product Category '{instance.categoryName}' updated. response::{catCreateRes}")
#     elif response["code"] == Short_Codes.ERROR:
#         print(f"error , {response}")
#         notify(type=6,msg='0',desc='Category error',stn=['POS'],vendorId=instance.vendorId)

# @receiver(pre_delete, sender=ProductCategory)
# def product_category_pre_delete(sender, instance, **kwargs):
#     response = WooCommerce.getCategoryUsingSlug(instance.categorySlug, instance.vendorId)
#     if response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         catCreateRes = WooCommerce.deleteCategoryUsingId(response["response"].get("id"), instance.vendorId)
#         print(f"Product Category '{instance.categoryName}' will be deleted. response::{catCreateRes}")
#     elif response["code"] == Short_Codes.ERROR:
#         print(f"error , {response}")
#         notify(type=6,msg='0',desc='Category error',stn=['POS'],vendorId=instance.vendorId)

# # Category signals end #################################################################


# # Product signals start #################################################################

# @receiver(post_save, sender=Product)
# def product_post_save(sender, instance, created, **kwargs):
#     wCatPrdMapping = {}
#     for i in ProductCategoryJoint.objects.filter(product=instance.pk):
#         response = WooCommerce.getCategoryUsingSlug(i.category.categorySlug, i.category.vendorId)
#         if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
#             wCatPrdMapping[i.category.pk]=response["response"].get("id")
#     response = WooCommerce.getProductUsingSku(instance.SKU, instance.vendorId)
#     if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
#         prdCreateRes = WooCommerce.createProduct(instance, instance.vendorId, wCatPrdMapping)
#         print(f"Product '{instance.productName}' created. response: {prdCreateRes}")
#     if response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         prdCreateRes = WooCommerce.updateProduct(response["response"].get("id"), instance, instance.vendorId, wCatPrdMapping)
#         print(f"Product '{instance.productName}' updated.  response: {prdCreateRes}")
        
# @receiver(pre_delete, sender=Product)
# def product_pre_delete(sender, instance, **kwargs):
#     response = WooCommerce.getProductUsingSku(instance.SKU, instance.vendorId)
#     if response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         prdCreateRes = WooCommerce.deleteProductUsingId(response["response"].get("id"), instance.vendorId, None)
#         print(f"Product '{instance.productName}' will be deleted.  response: {prdCreateRes}")
    
# # Product signals end #################################################################



# # Mod Group signals start #################################################################

# @receiver(post_save, sender=ProductModifierGroup)
# def mod_group_post_save(sender, instance, created, **kwargs):
#     response = WooCommerce.getModifierGroupUsingSlug(instance.slug, instance.vendorId)
#     if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
#         modGrpCrtRes = WooCommerce.createModifierGroup(instance, instance.vendorId, {})
#         print(f"Mod Group '{instance.productName}' will be created.  response: {modGrpCrtRes}")
#     elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         modGrpCrtRes = WooCommerce.updateModifierGroup(response["response"].get("id"), instance, instance.vendorId, {})
#         print(f"Mod Group '{instance.productName}' will be updated.  response: {modGrpCrtRes}")
        
# @receiver(pre_delete, sender=ProductModifierGroup)
# def mod_group_pre_delete(sender, instance, **kwargs):
#     response = WooCommerce.getProductUsingSku(instance.SKU, instance.vendorId)
#     if response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         modGrpCrtRes = WooCommerce.deleteModifierGroupUsingId(response["response"].get("id"), instance.vendorId)
#         print(f"Mod Group '{instance.productName}' will be deleted.  response: {modGrpCrtRes}")
    
# # Mod Group signals end #################################################################


# # Mod signals start #################################################################

# @receiver(post_save, sender=ProductModifierGroup)
# def mod_post_save(sender, instance, created, **kwargs):
#     coreModItms = ProductModifierAndModifierGroupJoint.objects.filter(vendor=instance.vendorId,modifier=instance.pk)
#     for coreModItm in coreModItms:
#         grp = WooCommerce.getModifierGroupUsingSlug(coreModItm.modifierGroup.slug, instance.vendorId)
#         response = WooCommerce.getModifierUsingGroupSKU(coreModItm.modifier.modifierSKU, grp["response"].get("id"), instance.vendorId)
#         if response["code"] == Short_Codes.CONNECTED_BUT_NOTFOUND:
#             modItmCrtRes = WooCommerce.createModifier(coreModItm.modifier, instance.vendorId, grp["response"].get("id"))
#         elif response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#             modItmCrtRes = WooCommerce.updateModifier(coreModItm.modifier, instance.vendorId,grp["response"].get("id"))

# @receiver(pre_delete, sender=ProductModifierGroup)
# def mod_pre_delete(sender, instance, **kwargs):
#     # response = WooCommerce.getProductUsingSku(instance.SKU, instance.vendorId)
#     # if response["code"] == Short_Codes.CONNECTED_AND_FOUND:
#         modGrpCrtRes = WooCommerce.deleteModifierUsingId(instance, instance.vendorId)
#         print(f"Mod Group '{instance.productName}' will be deleted.  response: {modGrpCrtRes}")

# # Mod signals end #################################################################