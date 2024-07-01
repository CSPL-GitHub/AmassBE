from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from core.models import Platform, Product, ProductImage, ProductModifier, Vendor
from inventory.utils import categories_sync_with_odoo, products_sync_with_odoo, modifier_groups_sync_with_odoo, modifiers_sync_with_odoo


@api_view(["POST"])
def sync_all(request):
    vendor_id = request.GET.get('vendor')
    
    try:
        if not vendor_id:
            raise ValueError
    
        vendor_id = int(vendor_id)
    
    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

    if not inventory_platform:
        return Response("Contact your administrator to activate the inventory", status=status.HTTP_400_BAD_REQUEST)

    modifier_group_sync_response = modifier_groups_sync_with_odoo(vendor_id)
    print("Modifier groups synced")

    modifier_sync_response = modifiers_sync_with_odoo(vendor_id)
    print("Modifiers synced")

    category_sync_response = categories_sync_with_odoo(vendor_id)
    print("Categories synced")

    product_sync_response = products_sync_with_odoo(vendor_id)
    print("Products synced")

    response_log = {
        "modifier_group": modifier_group_sync_response,
        "modifier": modifier_sync_response,
        "category": category_sync_response,
        "product": product_sync_response
    }

    return JsonResponse(response_log)


@api_view(["POST"])
def modifier_group_sync(request):
    vendor_id = request.GET.get('vendor')

    try:
        if not vendor_id:
            raise ValueError
        
        vendor_id = int(vendor_id)

    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

    if not inventory_platform:
        return Response("Contact your administrator to activate the inventory", status=status.HTTP_400_BAD_REQUEST)
    
    response_log = modifier_groups_sync_with_odoo(vendor_id)

    return JsonResponse(response_log)


@api_view(["POST"])
def modifier_sync(request):
    vendor_id = request.GET.get('vendor')

    try:
        if not vendor_id:
            raise ValueError
        
        vendor_id = int(vendor_id)

    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

    if not inventory_platform:
        return Response("Contact your administrator to activate the inventory", status=status.HTTP_400_BAD_REQUEST)
    
    response_log = modifiers_sync_with_odoo(vendor_id)

    return JsonResponse(response_log)


@api_view(["POST"])
def category_sync(request):
    vendor_id = request.GET.get('vendor')

    try:
        if not vendor_id:
            raise ValueError
        
        vendor_id = int(vendor_id)

    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

    if not inventory_platform:
        return Response("Contact your administrator to activate the inventory", status=status.HTTP_400_BAD_REQUEST)
    
    response_log = categories_sync_with_odoo(vendor_id)

    return JsonResponse(response_log)


@api_view(["POST"])
def product_sync(request):
    vendor_id = request.GET.get('vendor')

    try:
        if not vendor_id:
            raise ValueError
        
        vendor_id = int(vendor_id)

    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor does not exist", status=status.HTTP_400_BAD_REQUEST)

    inventory_platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=vendor_id).first()

    if not inventory_platform:
        return Response("Contact your administrator to activate the inventory", status=status.HTTP_400_BAD_REQUEST)
    
    response_log = products_sync_with_odoo(vendor_id)

    return JsonResponse(response_log)


@api_view(["PATCH"])
def product_status_toggle(request):
    try:
        request_data = request.data
        
        if not request_data:
            return Response("No data in the request body", status=status.HTTP_400_BAD_REQUEST)
        
        required_keys = {"plu", "is_active", "vendor_id"}

        if not required_keys.issubset(request_data.keys()):
            return Response("Keys in request data should be: 'plu', 'is_active', 'vendor_id'", status=status.HTTP_400_BAD_REQUEST)

        product_plu = request_data.get("plu")
        is_active = request_data.get("is_active")
        vendor_id = request_data.get("vendor_id")
        
        if not product_plu:
            return Response("Product PLU empty", status=status.HTTP_400_BAD_REQUEST)
        
        if (is_active is None) or (not isinstance(is_active, bool)):
            return Response("Invalid is_active parameter", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if not vendor_id:
                raise ValueError
            
            vendor_id = int(vendor_id)

        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)    

        product = Product.objects.filter(PLU=product_plu, vendorId=vendor_id).first()

        if not product:
            return Response("Product with given PLU does not exist", status=status.HTTP_404_NOT_FOUND)
        
        product.active = is_active

        product.save()

        return Response("Product status changed", status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(f"{str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(["PATCH"])
def modifier_status_toggle(request):
    try:
        request_data = request.data
        
        if not request_data:
            return Response("No data in the request body", status=status.HTTP_400_BAD_REQUEST)
        
        required_keys = {"plu", "is_active", "vendor_id"}

        if not required_keys.issubset(request_data.keys()):
            return Response("Keys in request data should be: 'plu', 'is_active', 'vendor_id'", status=status.HTTP_400_BAD_REQUEST)

        modifier_plu = request_data.get("plu")
        is_active = request_data.get("is_active")
        vendor_id = request_data.get("vendor_id")

        if not modifier_plu:
            return Response("Modifier PLU empty", status=status.HTTP_400_BAD_REQUEST)
        
        if (is_active is None) or (not isinstance(is_active, bool)):
            return Response("Invalid is_active parameter", status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if not vendor_id:
                raise ValueError
            
            vendor_id = int(vendor_id)

        except ValueError:
            return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
        
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)    

        modifier = ProductModifier.objects.filter(modifierPLU=modifier_plu, vendorId=vendor_id).first()

        if not modifier:
            return Response("Modifier with given PLU does not exist", status=status.HTTP_404_NOT_FOUND)
        
        modifier.active = is_active

        modifier.save()

        return Response("Modifier status changed", status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(f"{str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def disabled_items(request):
    vendor_id = request.GET.get("vendor")
    item_type = request.GET.get("type")

    if not item_type:
        return Response("Type parameter empty", status=status.HTTP_400_BAD_REQUEST)
    
    try:
        if not vendor_id:
            raise ValueError
        
        vendor_id = int(vendor_id)

    except ValueError:
        return Response("Invalid vendor ID", status=status.HTTP_400_BAD_REQUEST)
    
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if not vendor_instance:
        return Response("Vendor with given ID does not exist", status=status.HTTP_404_NOT_FOUND)

    if item_type not in ("product", "modifier"):
        return Response("Invalid type parameter", status=status.HTTP_400_BAD_REQUEST)
    
    items = []

    if item_type == "product":
        disabled_products = Product.objects.filter(active=False, isDeleted=False, vendorId=vendor_id)

        if not disabled_products.exists():
            return JsonResponse({"items": items}, status=status.HTTP_200_OK)
        
        for product in disabled_products:
            product_image = ProductImage.objects.filter(
                product=product.pk,
                vendorId=vendor_id
            ).first()

            image_url = 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
            
            if product_image:    
                image_url = product_image.url

            items.append({
                "id": product.pk,
                "name": product.productName,
                "price": product.productPrice,
                "tag": product.tag,
                "is_displayed_online": product.is_displayed_online,
                "image": image_url
            })

    elif item_type == "modifier":
        disabled_modifiers = ProductModifier.objects.filter(active=False, isDeleted=False, vendorId=vendor_id)

        if not disabled_modifiers.exists():
            return JsonResponse({"items": items}, status=status.HTTP_200_OK)
        
        for modifier in disabled_modifiers:
            image_url = 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'
            
            if modifier.modifierImg:    
                image_url = modifier.modifierImg

            items.append({
                "id": modifier.pk,
                "name": modifier.modifierName,
                "price": modifier.modifierPrice,
                "image": image_url
            })

    return JsonResponse({"items": items}, status=status.HTTP_200_OK)
