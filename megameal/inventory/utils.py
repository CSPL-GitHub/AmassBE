from koms.models import Order as KOMSOrder, Order_content, Order_modifer
from core.models import (
    Platform, Vendor, ProductCategory, Product, ProductImage, ProductCategoryJoint,
    ProductAndModifierGroupJoint, ProductModifierGroup, ProductModifier, ProductModifierAndModifierGroupJoint,
)
from inventory.models import InventorySyncErrorLog
import requests


def get_base_url_of_inventory(vendor_id):
    base_url = None

    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

    if inventory_platform:
        base_url = inventory_platform.baseUrl

    return base_url


def get_category_from_odoo(base_url, category_instance, vendor_id):
    try:
        odoo_category_get_url = f"{base_url}api/product_category/get/"

        if category_instance == None:
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "vendor_id": vendor_id
                }
            }

        else:    
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "plu": category_instance.categoryPLU,
                    "vendor_id": category_instance.vendorId.pk
                }
            }
        
        category_get_response = requests.post(odoo_category_get_url, json=request_data)
        
        if category_get_response.status_code != 200:
            raise Exception("Category fetching failed")
        
        category_get_response_data = category_get_response.json()

        if not category_get_response_data.get("result"):
            raise Exception("Category fetching failed")
        
        elif category_get_response_data.get("result").get("success") == False:
            raise Exception(category_get_response_data.get("result").get("message"))
        
        odoo_category = category_get_response_data.get("result").get("category")

        return odoo_category, ""
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message


def create_category_in_odoo(base_url, category_instance):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": category_instance.categoryPLU,
            "name": category_instance.categoryName,
            "is_active": category_instance.is_active,
            "vendor_id": category_instance.vendorId.pk
        }
    }
    
    try:
        odoo_category_create_url = f"{base_url}api/product_category/create/"

        category_create_response = requests.post(odoo_category_create_url, json=request_data)

        category_create_response_data = category_create_response.json()
                    
        if (category_create_response.status_code != 200):
            raise Exception("Category creation failed")
        
        else:
            if not category_create_response_data.get("result"):
                raise Exception("Category creation failed")
            
            elif (category_create_response_data.get("result").get("success") != True):
                raise Exception(category_create_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def update_category_in_odoo(base_url, category_instance):
    request_data = {
            "jsonrpc": "2.0",
            "params": {
                "plu": category_instance.categoryPLU,
                "name": category_instance.categoryName,
                "is_active": category_instance.is_active,
                "vendor_id": category_instance.vendorId.pk
            }
        }
    
    try:
        odoo_category_update_url = f"{base_url}api/product_category/update/"

        category_update_response = requests.put(odoo_category_update_url, json=request_data)

        category_update_response_data = category_update_response.json()
        
        if (category_update_response.status_code != 200):
            raise Exception("Category update failed")
        
        else:
            if not category_update_response_data.get("result"):
                raise Exception("Category update failed")

            elif (category_update_response_data.get("result").get("success") == False):
                raise Exception(category_update_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data
    

def delete_category_in_odoo(base_url, category_plu, vendor_id):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": category_plu,
            "vendor_id": vendor_id
        }
    }
    
    try:
        odoo_category_delete_url = f"{base_url}api/product_category/delete/"

        category_delete_response = requests.delete(odoo_category_delete_url, json=request_data)

        category_delete_response_data = category_delete_response.json()
                    
        if (category_delete_response.status_code != 200):
            raise Exception("Category deletion failed")
        
        else:
            if not category_delete_response_data.get("result"):
                raise Exception("Category creation failed")
            
            elif (category_delete_response_data.get("result").get("success") == False):
                raise Exception(category_delete_response_data.get("result").get("message"))
        
        return 1, "", None

    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def get_product_from_odoo(base_url, product_instance, vendor_id):
    try:
        odoo_product_get_url = f"{base_url}api/product/get/"

        if product_instance == None:
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "vendor_id": vendor_id
                }
            }

        else:    
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "plu": product_instance.PLU,
                    "vendor_id": product_instance.vendorId.pk
                }
            }
        
        product_get_response = requests.post(odoo_product_get_url, json=request_data)
        
        if product_get_response.status_code != 200:
            raise Exception("Product fetching failed")
        
        product_get_response_data = product_get_response.json()

        if not product_get_response_data.get("result"):
            raise Exception("Product fetching failed")
        
        elif product_get_response_data.get("result").get("success") == False:
            raise Exception(product_get_response_data.get("result").get("message"))
        
        odoo_product = product_get_response_data.get("result").get("product")

        return odoo_product, ""
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message


def create_product_in_odoo(base_url, product_instance):
    vendor_id = product_instance.vendorId.pk

    product_id = product_instance.pk

    core_product_image = ""
        
    product_image = ProductImage.objects.filter(product=product_id, vendorId=vendor_id).first()

    if product_image:
        core_product_image = product_image.url
    
    core_product_category_plu = ProductCategoryJoint.objects.filter(
        product=product_id,
        vendorId=vendor_id,
    ).first().category.categoryPLU

    modifier_group_ids = ProductAndModifierGroupJoint.objects.filter(
        product=product_id,
        vendorId=vendor_id
    ).values_list('modifierGroup__pk', flat=True)

    core_modifier_group_plu_list = list(
        set(
            ProductModifierGroup.objects.filter(pk__in=modifier_group_ids).values_list('PLU', flat=True)
        )
    )
    
    request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "plu": product_instance.PLU,
                    "name": product_instance.productName,
                    "price":  product_instance.productPrice,
                    "tag": product_instance.tag,
                    "is_active": product_instance.active,
                    "image": core_product_image,
                    "category_plu": core_product_category_plu,
                    "modifier_group_plu": core_modifier_group_plu_list,
                    "vendor_id": vendor_id
                }
            }
    
    try:
        odoo_product_create_url = f"{base_url}api/product/create/"

        product_create_response = requests.post(odoo_product_create_url, json=request_data)

        product_create_response_data = product_create_response.json()
                    
        if (product_create_response.status_code != 200):
            raise Exception("Product creation failed")
        
        else:
            if not product_create_response_data.get("result"):
                raise Exception("Product creation failed")
            
            elif (product_create_response_data.get("result").get("success") != True):
                raise Exception(product_create_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def update_product_in_odoo(base_url, product_instance, product_image, category_plu, modifier_group_plu_list):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": product_instance.PLU,
            "name": product_instance.productName,
            "price":  product_instance.productPrice,
            "tag": product_instance.tag,
            "is_active": product_instance.active,
            "image": product_image,
            "category_plu": category_plu,
            "modifier_group_plu": modifier_group_plu_list,
            "vendor_id": product_instance.vendorId.pk
        }
    }

    try:
        odoo_product_update_url = f"{base_url}api/product/update/"

        product_update_response = requests.put(odoo_product_update_url, json=request_data)

        product_update_response_data = product_update_response.json()
        
        if (product_update_response.status_code != 200):
            raise Exception("Product update failed")
        
        else:
            if not product_update_response_data.get("result"):
                raise Exception("Product update failed")

            elif (product_update_response_data.get("result").get("success") == False):
                raise Exception(product_update_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data
    

def delete_product_in_odoo(base_url, product_plu, vendor_id):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": product_plu,
            "vendor_id": vendor_id
        }
    }
    
    try:
        odoo_product_delete_url = f"{base_url}api/product/delete/"

        product_delete_response = requests.delete(odoo_product_delete_url, json=request_data)

        product_delete_response_data = product_delete_response.json()
                    
        if (product_delete_response.status_code != 200):
            raise Exception("Category deletion failed")
        
        else:
            if not product_delete_response_data.get("result"):
                raise Exception("Category creation failed")
            
            elif (product_delete_response_data.get("result").get("success") == False):
                raise Exception(product_delete_response_data.get("result").get("message"))
        
        return 1, "", None

    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def get_modifier_group_from_odoo(base_url, modifier_group_instance, vendor_id):
    try:
        odoo_modifier_group_get_url = f"{base_url}api/modifier_group/get/"

        if modifier_group_instance == None:
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "vendor_id": vendor_id
                }
            }

        else:    
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "plu": modifier_group_instance.PLU,
                    "vendor_id": modifier_group_instance.vendorId.pk
                }
            }
        
        modifier_group_get_response = requests.post(odoo_modifier_group_get_url, json=request_data)
        
        if modifier_group_get_response.status_code != 200:
            raise Exception("Modifier group fetching failed")
        
        modifier_group_get_response_data = modifier_group_get_response.json()

        if not modifier_group_get_response_data.get("result"):
            raise Exception("Modifier group fetching failed")
        
        elif modifier_group_get_response_data.get("result").get("success") == False:
            raise Exception(modifier_group_get_response_data.get("result").get("message"))
        
        odoo_modifier_group = modifier_group_get_response_data.get("result").get("modifier_group")

        return odoo_modifier_group, ""
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message


def create_modifier_group_in_odoo(base_url, modifier_group_instance):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": modifier_group_instance.PLU,
            "name": modifier_group_instance.name,
            "is_active": modifier_group_instance.active,
            "vendor_id": modifier_group_instance.vendorId.pk
        }
    }
    
    try:
        odoo_modifier_group_create_url = f"{base_url}api/modifier_group/create/"

        modifier_group_create_response = requests.post(odoo_modifier_group_create_url, json=request_data)

        modifier_group_create_response_data = modifier_group_create_response.json()
                    
        if (modifier_group_create_response.status_code != 200):
            raise Exception("Modifier group creation failed")
        
        else:
            if not modifier_group_create_response_data.get("result"):
                raise Exception("Modifier group creation failed")
            
            elif (modifier_group_create_response_data.get("result").get("success") != True):
                raise Exception(modifier_group_create_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def update_modifier_group_in_odoo(base_url, modifier_group_instance):
    request_data = {
            "jsonrpc": "2.0",
            "params": {
                "plu": modifier_group_instance.PLU,
                "name": modifier_group_instance.name,
                "is_active": modifier_group_instance.active,
                "vendor_id": modifier_group_instance.vendorId.pk
            }
        }
    
    try:
        odoo_modifier_group_update_url = f"{base_url}api/modifier_group/update/"

        modifier_group_update_response = requests.put(odoo_modifier_group_update_url, json=request_data)

        modifier_group_update_response_data = modifier_group_update_response.json()
        
        if (modifier_group_update_response.status_code != 200):
            raise Exception("Modifier group update failed")
        
        else:
            if not modifier_group_update_response_data.get("result"):
                raise Exception("Modifier group update failed")

            elif (modifier_group_update_response_data.get("result").get("success") == False):
                raise Exception(modifier_group_update_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data
    

def delete_modifier_group_in_odoo(base_url, modifier_group_plu, vendor_id):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": modifier_group_plu,
            "vendor_id": vendor_id
        }
    }
    
    try:
        odoo_modifier_group_delete_url = f"{base_url}api/modifier_group/delete/"

        modifier_group_delete_response = requests.delete(odoo_modifier_group_delete_url, json=request_data)

        modifier_group_delete_response_data = modifier_group_delete_response.json()
                    
        if (modifier_group_delete_response.status_code != 200):
            raise Exception("Modifier group deletion failed")
        
        else:
            if not modifier_group_delete_response_data.get("result"):
                raise Exception("Modifier group creation failed")
            
            elif (modifier_group_delete_response_data.get("result").get("success") == False):
                raise Exception(modifier_group_delete_response_data.get("result").get("message"))
        
        return 1, "", None

    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def get_modifier_from_odoo(base_url, modifier_instance, vendor_id):
    try:
        odoo_modifier_get_url = f"{base_url}api/modifier/get/"

        if modifier_instance == None:
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "vendor_id": vendor_id
                }
            }

        else:    
            request_data = {
                "jsonrpc": "2.0",
                "params": {
                    "plu": modifier_instance.modifierPLU,
                    "vendor_id": modifier_instance.vendorId.pk
                }
            }
        
        modifier_get_response = requests.post(odoo_modifier_get_url, json=request_data)
        
        if modifier_get_response.status_code != 200:
            raise Exception("Modifier fetching failed")
        
        modifier_get_response_data = modifier_get_response.json()

        if not modifier_get_response_data.get("result"):
            raise Exception("Modifier fetching failed")
        
        elif modifier_get_response_data.get("result").get("success") == False:
            raise Exception(modifier_get_response_data.get("result").get("message"))
        
        odoo_modifier = modifier_get_response_data.get("result").get("modifier")

        return odoo_modifier, ""
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message


def create_modifier_in_odoo(base_url, modifier_instance):
    core_modifier_image = ""

    if modifier_instance.modifierImg:
        core_modifier_image = modifier_instance.modifierImg
    
    modifier_group_ids = ProductModifierAndModifierGroupJoint.objects.filter(
        modifier=modifier_instance.pk,
        vendor=modifier_instance.vendorId.pk
    ).values_list('modifierGroup__pk', flat=True)

    core_modifier_group_plu_list = list(
        set(
            ProductModifierGroup.objects.filter(pk__in=modifier_group_ids).values_list('PLU', flat=True)
        )
    )
    
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": modifier_instance.modifierPLU,
            "name": modifier_instance.modifierName,
            "price":  modifier_instance.modifierPrice,
            "is_active": modifier_instance.active,
            "image": core_modifier_image,
            "modifier_group_plu": core_modifier_group_plu_list,
            "vendor_id": modifier_instance.vendorId.pk
        }
    }
    
    try:
        odoo_modifier_create_url = f"{base_url}api/modifier/create/"

        modifier_create_response = requests.post(odoo_modifier_create_url, json=request_data)

        modifier_create_response_data = modifier_create_response.json()
                    
        if (modifier_create_response.status_code != 200):
            raise Exception("Modifier creation failed")
        
        else:
            if not modifier_create_response_data.get("result"):
                raise Exception("Modifier creation failed")
            
            elif (modifier_create_response_data.get("result").get("success") != True):
                raise Exception(modifier_create_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def update_modifier_in_odoo(base_url, modifier_instance, modifier_image, modifier_group_plu_list):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": modifier_instance.modifierPLU,
            "name": modifier_instance.modifierName,
            "price":  modifier_instance.modifierPrice,
            "is_active": modifier_instance.active,
            "image": modifier_image,
            "modifier_group_plu": modifier_group_plu_list,
            "vendor_id": modifier_instance.vendorId.pk
        }
    }
    
    try:
        odoo_modifier_update_url = f"{base_url}api/modifier/update/"

        modifier_update_response = requests.put(odoo_modifier_update_url, json=request_data)

        modifier_update_response_data = modifier_update_response.json()
        
        if (modifier_update_response.status_code != 200):
            raise Exception("Modifier update failed")
        
        else:
            if not modifier_update_response_data.get("result"):
                raise Exception("Modifier update failed")

            elif (modifier_update_response_data.get("result").get("success") == False):
                raise Exception(modifier_update_response_data.get("result").get("message"))
        
        return 1, "", None
    
    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data
    

def delete_modifier_in_odoo(base_url, modifier_plu, vendor_id):
    request_data = {
        "jsonrpc": "2.0",
        "params": {
            "plu": modifier_plu,
            "vendor_id": vendor_id
        }
    }
    
    try:
        odoo_modifier_delete_url = f"{base_url}api/modifier/delete/"

        modifier_delete_response = requests.delete(odoo_modifier_delete_url, json=request_data)

        modifier_delete_response_data = modifier_delete_response.json()
                    
        if (modifier_delete_response.status_code != 200):
            raise Exception("Modifier deletion failed")
        
        else:
            if not modifier_delete_response_data.get("result"):
                raise Exception("Modifier creation failed")
            
            elif (modifier_delete_response_data.get("result").get("success") == False):
                raise Exception(modifier_delete_response_data.get("result").get("message"))
        
        return 1, "", None

    except Exception as e:
        error_message = str(e)
        print(error_message)
        return 0, error_message, request_data


def modifier_groups_sync_with_odoo(vendor_id):
    error_log = {
        "modifier_group_get_error_log": "",
        "modifier_group_update_error_log": [],
        "modifier_group_create_error_log": [],
        "modifier_group_delete_error_log": [],
        "modifier_group_vendor_mismatch_log": []
    }
    
    base_url = get_base_url_of_inventory(vendor_id)
    
    if not base_url:
        error_log["modifier_group_get_error_log"] = "Invalid base URL"

        return error_log

    odoo_modifier_groups, get_error_message = get_modifier_group_from_odoo(base_url, None, vendor_id)

    if get_error_message != "":
        error_log["modifier_group_get_error_log"] = get_error_message

        return error_log
    
    modifier_group_create_error_log = []
    
    if not odoo_modifier_groups:
        core_modifier_groups = ProductModifierGroup.objects.filter(vendorId=vendor_id)

        for core_modifier_group in core_modifier_groups:
            create_status, create_error_message, request_data = create_modifier_group_in_odoo(base_url, core_modifier_group)

            if create_status == 0:
                modifier_group_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["modifier_group_create_error_log"] = modifier_group_create_error_log

        return error_log

    else:
        core_modifier_group_plu_set = set(ProductModifierGroup.objects.filter(vendorId=vendor_id).values_list('PLU', flat=True))

        odoo_modifier_group_plu_set = set()
        
        modifier_group_vendor_mismatch_log = []
        
        for odoo_modifier_group in odoo_modifier_groups:
            if odoo_modifier_group.get('vendor_id') == vendor_id:
                odoo_modifier_group_plu_set.add(odoo_modifier_group.get('plu'))

            else:
                modifier_group_vendor_mismatch_log.append({
                    "payload": f"PLU: {odoo_modifier_group.get('plu')}, \
                        Odoo Vendor ID: {odoo_modifier_group.get('vendor_id')}, \
                        Core Vendor ID: {vendor_id}",
                    "message": "Vendor IDs do not match",
                })

        error_log["modifier_group_vendor_mismatch_log"] = modifier_group_vendor_mismatch_log
        
        modifier_group_plu_in_both = core_modifier_group_plu_set.intersection(odoo_modifier_group_plu_set)

        modifier_group_plu_in_core_not_in_odoo = core_modifier_group_plu_set - odoo_modifier_group_plu_set

        modifier_group_plu_in_odoo_not_in_core = odoo_modifier_group_plu_set - core_modifier_group_plu_set

        modifier_group_update_error_log = []
        
        for modifier_group_plu in modifier_group_plu_in_both:
            core_modifier_group = ProductModifierGroup.objects.filter(PLU=modifier_group_plu, vendorId=vendor_id).first()

            for odoo_modifier_group in odoo_modifier_groups:
                if odoo_modifier_group.get("vendor_id") == core_modifier_group.vendorId.pk:
                    if odoo_modifier_group.get("plu") == modifier_group_plu:
                        if odoo_modifier_group.get("name") != core_modifier_group.name or \
                        odoo_modifier_group.get("is_active") != core_modifier_group.active:
                            update_status, error_message, request_data = update_modifier_group_in_odoo(base_url, core_modifier_group)
                        
                            if update_status == 0:
                                modifier_group_update_error_log.append({
                                    "payload": request_data.get("params"),
                                    "message": error_message,
                                })

        error_log["modifier_group_update_error_log"] = modifier_group_update_error_log

        for modifier_group_plu in modifier_group_plu_in_core_not_in_odoo:
            core_modifier_group = ProductModifierGroup.objects.filter(PLU=modifier_group_plu, vendorId=vendor_id).first()

            create_status, create_error_message, request_data = create_modifier_group_in_odoo(base_url, core_modifier_group)

            if create_status == 0:
                modifier_group_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["modifier_group_create_error_log"] = modifier_group_create_error_log

        modifier_group_delete_error_log = []

        for modifier_group_plu in modifier_group_plu_in_odoo_not_in_core:
            delete_status, delete_error_message, request_data = delete_modifier_group_in_odoo(base_url, modifier_group_plu, vendor_id)
        
            if delete_status == 0:
                modifier_group_delete_error_log.append({
                    "payload": request_data.get("params"),
                    "message": delete_error_message
                })

        error_log["modifier_group_delete_error_log"] = modifier_group_delete_error_log
        
        return error_log


def modifiers_sync_with_odoo(vendor_id):
    error_log = {
        "modifier_get_error_log": "",
        "modifier_update_error_log": [],
        "modifier_create_error_log": [],
        "modifier_delete_error_log": [],
        "modifier_vendor_mismatch_log": []
    }
    
    base_url = get_base_url_of_inventory(vendor_id)
    
    if not base_url:
        error_log["modifier_get_error_log"] = "Invalid base URL"

        return error_log

    odoo_modifiers, get_error_message = get_modifier_from_odoo(base_url, None, vendor_id)

    if get_error_message != "":
        error_log["modifier_get_error_log"] = get_error_message

        return error_log

    modifier_create_error_log = []
    
    if not odoo_modifiers:
        core_modifiers = ProductModifier.objects.filter(vendorId=vendor_id)
    
        for core_modifier in core_modifiers:
            create_status, create_error_message, request_data = create_modifier_in_odoo(base_url, core_modifier)

            if create_status == 0:
                modifier_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["modifier_create_error_log"] = modifier_create_error_log

        return error_log
    
    else:
        core_modifier_plu_set = set(ProductModifier.objects.filter(vendorId=vendor_id).values_list('modifierPLU', flat=True))

        odoo_modifier_plu_set = set()
        
        modifier_vendor_mismatch_log = []
        
        for odoo_modifier in odoo_modifiers:
            if odoo_modifier.get('vendor_id') == vendor_id:
                odoo_modifier_plu_set.add(odoo_modifier.get('plu'))

            else:
                modifier_vendor_mismatch_log.append({
                    "payload": f"PLU: {odoo_modifier.get('plu')}, \
                        Odoo Vendor ID: {odoo_modifier.get('vendor_id')}, \
                        Core Vendor ID: {vendor_id}",
                    "message": "Vendor IDs do not match",
                })

        error_log["modifier_vendor_mismatch_log"] = modifier_vendor_mismatch_log

        modifier_plu_in_both = core_modifier_plu_set.intersection(odoo_modifier_plu_set)

        modifier_plu_in_core_not_in_odoo = core_modifier_plu_set - odoo_modifier_plu_set

        modifier_plu_in_odoo_not_in_core = odoo_modifier_plu_set - core_modifier_plu_set
        
        modifier_update_error_log = []
        
        for modifier_plu in modifier_plu_in_both:
            core_modifier = ProductModifier.objects.filter(modifierPLU=modifier_plu, vendorId=vendor_id).first()

            core_modifier_image = ""

            if core_modifier.modifierImg:
                core_modifier_image = core_modifier.modifierImg
            
            modifier_group_ids = ProductModifierAndModifierGroupJoint.objects.filter(
                modifier=core_modifier.pk,
                vendor=vendor_id
            ).values_list('modifierGroup__pk', flat=True)

            core_modifier_group_plu_list = list(
                set(
                    ProductModifierGroup.objects.filter(pk__in=modifier_group_ids).values_list('PLU', flat=True)
                )
            )
            
            for odoo_modifier in odoo_modifiers:
                if odoo_modifier.get("vendor_id") == core_modifier.vendorId:
                    if odoo_modifier.get("plu") == modifier_plu:
                        if (odoo_modifier.get("name") != core_modifier.modifierName) or \
                        (odoo_modifier.get("price") != core_modifier.modifierPrice) or \
                        (odoo_modifier.get("is_active") != core_modifier.active) or \
                        (odoo_modifier.get("image") != core_modifier.modifierImg) or \
                        (odoo_modifier.get("modifier_group_plu") != core_modifier_group_plu_list):
                            update_status, error_message, request_data = update_modifier_in_odoo(base_url, core_modifier, core_modifier_image, core_modifier_group_plu_list)
                        
                            if update_status == 0:
                                modifier_update_error_log.append({
                                    "payload": request_data.get("params"),
                                    "message": error_message,
                                })

        error_log["modifier_update_error_log"] = modifier_update_error_log
        
        for modifier_plu in modifier_plu_in_core_not_in_odoo:
            core_modifier = ProductModifier.objects.filter(modifierPLU=modifier_plu, vendorId=vendor_id).first()
                
            create_status, create_error_message, request_data = create_modifier_in_odoo(base_url, core_modifier)

            if create_status == 0:
                modifier_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["modifier_create_error_log"] = modifier_create_error_log

        modifier_delete_error_log = []

        for modifier_plu in modifier_plu_in_odoo_not_in_core:
            delete_status, delete_error_message, request_data = delete_modifier_in_odoo(base_url, modifier_plu, vendor_id)
        
            if delete_status == 0:
                modifier_delete_error_log.append({
                    "payload": request_data.get("params"),
                    "message": delete_error_message
                })

        error_log["modifier_delete_error_log"] = modifier_delete_error_log
        
        return error_log


def categories_sync_with_odoo(vendor_id):
    error_log = {
        "category_get_error_log": "",
        "category_update_error_log": [],
        "category_create_error_log": [],
        "category_delete_error_log": [],
        "category_vendor_mismatch_log": []
    }

    base_url = get_base_url_of_inventory(vendor_id)
    
    if not base_url:
        error_log["category_get_error_log"] = "Invalid base URL"

        return error_log

    odoo_categories, get_error_message = get_category_from_odoo(base_url, None, vendor_id)

    if get_error_message != "":
        error_log["category_get_error_log"] = get_error_message

        return error_log

    category_create_error_log = []
    
    if not odoo_categories:
        core_categories = ProductCategory.objects.filter(vendorId=vendor_id)

        for core_category in core_categories:
            create_status, create_error_message, request_data = create_category_in_odoo(base_url, core_category)

            if create_status == 0:
                category_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["category_create_error_log"] = category_create_error_log

        return error_log

    else:
        core_category_plu_set = set(ProductCategory.objects.filter(vendorId=vendor_id).values_list('categoryPLU', flat=True))

        odoo_category_plu_set = set()

        category_vendor_mismatch_log = []

        for odoo_category in odoo_categories:
            if odoo_category.get('vendor_id') == vendor_id:
                odoo_category_plu_set.add(odoo_category.get('plu'))

            else:
                category_vendor_mismatch_log.append({
                    "payload": f"PLU: {odoo_category.get('plu')}, \
                        Odoo Vendor ID: {odoo_category.get('vendor_id')}, \
                        Core Vendor ID: {vendor_id}",
                    "message": "Vendor IDs do not match",
                })

        error_log["category_vendor_mismatch_log"] = category_vendor_mismatch_log

        category_plu_in_both = core_category_plu_set.intersection(odoo_category_plu_set)

        category_plu_in_core_not_in_odoo = core_category_plu_set - odoo_category_plu_set

        category_plu_in_odoo_not_in_core = odoo_category_plu_set - core_category_plu_set
        
        category_update_error_log = []
        
        for category_plu in category_plu_in_both:
            core_category = ProductCategory.objects.filter(categoryPLU=category_plu, vendorId=vendor_id).first()

            for odoo_category in odoo_categories:
                if (odoo_category.get("plu") == category_plu):
                    if (odoo_category.get("name") != core_category.categoryName) or \
                    (odoo_category.get("is_active") != core_category.is_active):
                        update_status, error_message, request_data = update_category_in_odoo(base_url, core_category)
                        
                        if update_status == 0:
                            category_update_error_log.append({
                                "payload": request_data.get("params"),
                                "message": error_message,
                            })

        error_log["category_update_error_log"] = category_update_error_log

        for category_plu in category_plu_in_core_not_in_odoo:
            core_category = ProductCategory.objects.filter(categoryPLU=category_plu, vendorId=vendor_id).first()

            create_status, create_error_message, request_data = create_category_in_odoo(base_url, core_category)

            if create_status == 0:
                category_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["category_create_error_log"] = category_create_error_log

        category_delete_error_log = []
        
        for category_plu in category_plu_in_odoo_not_in_core:
            delete_status, delete_error_message, request_data = delete_category_in_odoo(base_url, category_plu, vendor_id)
        
            if delete_status == 0:
                category_delete_error_log.append({
                    "payload": request_data.get("params"),
                    "message": delete_error_message
                })

        error_log["category_delete_error_log"] = category_delete_error_log
    
        return error_log


def products_sync_with_odoo(vendor_id):
    error_log = {
        "product_get_error_log": "",
        "product_update_error_log": [],
        "product_create_error_log": [],
        "product_delete_error_log": [],
        "product_vendor_mismatch_log": []
    }
    
    base_url = get_base_url_of_inventory(vendor_id)
    
    if not base_url:
        error_log["product_get_error_log"] = "Invalid base URL"

        return error_log
    
    odoo_products, get_error_message = get_product_from_odoo(base_url, None, vendor_id)

    if get_error_message != "":
        error_log["product_get_error_log"] = get_error_message

        return error_log
    
    product_create_error_log = []
    
    if not odoo_products:
        core_products = Product.objects.filter(vendorId=vendor_id)

        for core_product in core_products:
            create_status, create_error_message, request_data = create_product_in_odoo(base_url, core_product)

            if create_status == 0:
                product_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["product_create_error_log"] = product_create_error_log

        return error_log

    else:
        core_product_plu_set = set(Product.objects.filter(vendorId=vendor_id).values_list('PLU', flat=True))

        odoo_product_plu_set = set()
        
        product_vendor_mismatch_log = []
        
        for odoo_product in odoo_products:
            if odoo_product.get('vendor_id') == vendor_id:
                odoo_product_plu_set.add(odoo_product.get('plu'))

            else:
                product_vendor_mismatch_log.append({
                    "payload": f"PLU: {odoo_product.get('plu')}, \
                        Odoo Vendor ID: {odoo_product.get('vendor_id')}, \
                        Core Vendor ID: {vendor_id}",
                    "message": "Vendor IDs do not match",
                })

        error_log["product_vendor_mismatch_log"] = product_vendor_mismatch_log

        product_plu_in_both = core_product_plu_set.intersection(odoo_product_plu_set)

        product_plu_in_core_not_in_odoo = core_product_plu_set - odoo_product_plu_set

        product_plu_in_odoo_not_in_core = odoo_product_plu_set - core_product_plu_set
        
        product_update_error_log = []
        
        for product_plu in product_plu_in_both:
            core_product = Product.objects.filter(PLU=product_plu, vendorId=vendor_id).first()

            core_product_image = ""
            
            product_image = ProductImage.objects.filter(product=core_product.pk, vendorId=vendor_id).first()

            if product_image:
                core_product_image = product_image.url
            
            core_product_category_plu = ProductCategoryJoint.objects.filter(
                product=core_product.pk,
                vendorId=vendor_id,
            ).first().category.categoryPLU

            modifier_group_ids = ProductAndModifierGroupJoint.objects.filter(
                product=core_product.pk,
                vendorId=vendor_id
            ).values_list('modifierGroup__pk', flat=True)

            core_modifier_group_plu_list = list(
                set(
                    ProductModifierGroup.objects.filter(pk__in=modifier_group_ids).values_list('PLU', flat=True)
                )
            )

            for odoo_product in odoo_products:
                if odoo_product.get("vendor_id") == core_product.vendorId.pk:
                    if odoo_product.get("plu") == product_plu:
                        if (odoo_product.get("name") != core_product.productName) or \
                        (odoo_product.get("price") != core_product.productPrice) or \
                        (odoo_product.get("tag") != core_product.tag) or \
                        (odoo_product.get("is_active") != core_product.active) or \
                        (odoo_product.get("image") != core_product_image) or \
                        (odoo_product.get("category_plu") != core_product_category_plu) or \
                        (odoo_product.get("modifier_group_plu") != core_modifier_group_plu_list):
                            update_status, error_message, request_data = update_product_in_odoo(
                                base_url,
                                core_product,
                                core_product_image,
                                core_product_category_plu,
                                core_modifier_group_plu_list
                            )
                        
                            if update_status == 0:
                                product_update_error_log.append({
                                    "payload": request_data.get("params"),
                                    "message": error_message,
                                })

        error_log["product_update_error_log"] = product_update_error_log
        
        for product_plu in product_plu_in_core_not_in_odoo:
            core_product = Product.objects.filter(PLU=product_plu, vendorId=vendor_id).first()

            create_status, create_error_message, request_data = create_product_in_odoo(base_url, core_product)

            if create_status == 0:
                product_create_error_log.append({
                    "payload": request_data.get("params"),
                    "message": create_error_message
                })

        error_log["product_create_error_log"] = product_create_error_log

        product_delete_error_log = []
        
        for product_plu in product_plu_in_odoo_not_in_core:
            delete_status, delete_error_message, request_data = delete_product_in_odoo(base_url, product_plu, vendor_id)
        
            if delete_status == 0:
                product_delete_error_log.append({
                    "payload": request_data.get("params"),
                    "message": delete_error_message
                })

        error_log["product_delete_error_log"] = product_delete_error_log
            
        return error_log


def sync_order_content_with_inventory(master_order_id, vendor_id):
    try:
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

        staging_order = KOMSOrder.objects.filter(master_order=master_order_id).first()

        if staging_order:
            staging_order_id = staging_order.pk

            products_ordered = Order_content.objects.filter(orderId=staging_order_id)

            product_details = []
            modifier_details = []
            
            if products_ordered.exists():    
                for product_content in products_ordered:
                    product_status = True
                    
                    if product_content.status == "5":
                        product_status = False
                    
                    product_details.append({
                        "plu": product_content.SKU,
                        "status": product_status,
                        "qty": product_content.quantity
                    })

                    ordered_modifiers = Order_modifer.objects.filter(contentID=product_content.pk)

                    modifier_status = False
                    
                    if ordered_modifiers.exists():
                        for modifier_content in ordered_modifiers:
                            if modifier_content.quantityStatus == 1:
                                modifier_status = True

                            modifier_details.append({
                                "plu": modifier_content.SKU,
                                "status": modifier_status,
                                "qty": modifier_content.quantity
                            })

                base_url = platform.baseUrl

                odoo_order_json_post_url = f"{base_url}api/create_order/"

                request_data = {
                    "jsonrpc": "2.0",
                    "params": {
                        "order_id": master_order_id,
                        "products": product_details,
                        "modifiers": modifier_details,
                        "vendor_id": vendor_id,
                    }
                }

                order_json_post_response = requests.post(odoo_order_json_post_url, json=request_data)

                order_json_post_response_data = order_json_post_response.json()
                
                if (order_json_post_response.status_code != 200) or \
                ((order_json_post_response.status_code == 200) and (order_json_post_response_data.get("result").get("success") == False)):
                    inventory_sync_error_log_instance = InventorySyncErrorLog(
                        payload=request_data,
                        response_status_code=order_json_post_response.status_code,
                        response=order_json_post_response_data.get("result").get("message"),
                        vendor=vendor_instance
                    )

                    inventory_sync_error_log_instance.save()

        else:
            inventory_sync_error_log_instance = InventorySyncErrorLog(
                payload=master_order_id,
                response_status_code=0,
                response=f"Order not found for given master order ID: {master_order_id}",
                vendor=vendor_instance
            )

            inventory_sync_error_log_instance.save()
    
    except Exception as e:
        inventory_sync_error_log_instance = InventorySyncErrorLog(
            payload="",
            response_status_code=0,
            response=str(e),
            vendor=vendor_instance
        )

        inventory_sync_error_log_instance.save()


def single_category_sync_with_odoo(category_instance):
    try:
        base_url = get_base_url_of_inventory(category_instance.vendorId.pk)
        
        if not base_url:
            raise Exception("Invalid base URL")
        
        odoo_category, get_error_message = get_category_from_odoo(base_url, category_instance, category_instance.vendorId.pk)
        
        if odoo_category == 0:
            raise Exception(get_error_message)
        
        elif odoo_category is None:
            create_status, create_error_message, request_data = create_category_in_odoo(base_url, category_instance)
        
            if create_status == 0:
                raise Exception(create_error_message)
            
            return 1
        
        else:
            if (odoo_category.get("vendor_id") != category_instance.vendorId.pk) or \
            (odoo_category.get("plu") != category_instance.categoryPLU):
                raise Exception("PLU or vendor ID did not match with response")
            
            update_response, update_error_message, request_data = update_category_in_odoo(base_url, category_instance)
        
            if update_response == 0:
                raise Exception(update_error_message)
                
            return 1

    except Exception as e:
        print(str(e))
        return 0


def single_product_sync_with_odoo(product_instance):
    vendor_id = product_instance.vendorId.pk

    try:
        base_url = get_base_url_of_inventory(vendor_id)
        
        if not base_url:
            raise Exception("Invalid base URL")
        
        odoo_product, get_error_message = get_product_from_odoo(base_url, product_instance, vendor_id)
        
        if odoo_product == 0:
            raise Exception(get_error_message)
        
        elif odoo_product is None:
            create_status, create_error_message, request_data = create_product_in_odoo(base_url, product_instance)
        
            if create_status == 0:
                raise Exception(create_error_message)
            
            return 1
        
        else:
            product_id = product_instance.pk

            core_product_image = ""
        
            product_image = ProductImage.objects.filter(product=product_id, vendorId=vendor_id).first()

            if product_image:
                core_product_image = product_image.url
            
            category_plu = ProductCategoryJoint.objects.filter(
                product=product_id,
                vendorId=vendor_id,
            ).first().category.categoryPLU

            modifier_group_ids = ProductAndModifierGroupJoint.objects.filter(
                product=product_id,
                vendorId=vendor_id
            ).values_list('modifierGroup__pk', flat=True)

            modifier_group_plu_list = list(
                set(
                    ProductModifierGroup.objects.filter(pk__in=modifier_group_ids).values_list('PLU', flat=True)
                )
            )
            
            if (odoo_product.get("vendor_id") != vendor_id) or \
            (odoo_product.get("plu") != product_instance.PLU):
                raise Exception("PLU or vendor ID did not match with response")
            
            update_response, update_error_message, request_data = update_product_in_odoo(base_url, product_instance, core_product_image, category_plu, modifier_group_plu_list)
        
            if update_response == 0:
                raise Exception(update_error_message)
                
            return 1

    except Exception as e:
        print(str(e))
        return 0


def single_modifier_group_sync_with_odoo(modifier_group_instance):
    try:
        base_url = get_base_url_of_inventory(modifier_group_instance.vendorId.pk)
        
        if not base_url:
            raise Exception("Invalid base URL")
        
        modifier_group, get_error_message = get_modifier_group_from_odoo(base_url, modifier_group_instance, modifier_group_instance.vendorId.pk)
        
        if modifier_group == 0:
            raise Exception(get_error_message)
        
        elif modifier_group is None:
            create_status, create_error_message, request_data = create_modifier_group_in_odoo(base_url, modifier_group_instance)
        
            if create_status == 0:
                raise Exception(create_error_message)
            
            return 1
        
        else:
            if (modifier_group.get("vendor_id") != modifier_group_instance.vendorId.pk) or \
            (modifier_group.get("plu") != modifier_group_instance.PLU):
                raise Exception("PLU or vendor ID did not match with response")
            
            update_response, update_error_message, request_data = update_modifier_group_in_odoo(base_url, modifier_group_instance)
        
            if update_response == 0:
                raise Exception(update_error_message)
                
            return 1

    except Exception as e:
        print(str(e))
        return 0


def single_modifier_sync_with_odoo(modifier_instance):
    try:
        base_url = get_base_url_of_inventory(modifier_instance.vendorId.pk)
        
        if not base_url:
            raise Exception("Invalid base URL")
        
        modifier_group, get_error_message = get_modifier_from_odoo(base_url, modifier_instance, modifier_instance.vendorId.pk)
        
        if modifier_group == 0:
            raise Exception(get_error_message)
        
        elif modifier_group is None:
            create_status, create_error_message, request_data = create_modifier_in_odoo(base_url, modifier_instance)
        
            if create_status == 0:
                raise Exception(create_error_message)
            
            return 1
        
        else:
            core_modifier_image = ""

            if modifier_instance.modifierImg:
                core_modifier_image = modifier_instance.modifierImg
            
            modifier_group_ids = ProductModifierAndModifierGroupJoint.objects.filter(
                modifier=modifier_instance.pk,
                vendor=modifier_instance.vendorId.pk
            ).values_list('modifierGroup__pk', flat=True)

            core_modifier_group_plu_list = list(
                set(
                    ProductModifierGroup.objects.filter(pk__in=modifier_group_ids).values_list('PLU', flat=True)
                )
            )
            if (modifier_group.get("vendor_id") != modifier_instance.vendorId.pk) or \
            (modifier_group.get("plu") != modifier_instance.modifierPLU):
                raise Exception("PLU or vendor ID did not match with response")
            
            update_response, update_error_message, request_data = update_modifier_in_odoo(base_url, modifier_instance, core_modifier_image, core_modifier_group_plu_list)
        
            if update_response == 0:
                raise Exception(update_error_message)
                
            return 1

    except Exception as e:
        print(str(e))
        return 0
