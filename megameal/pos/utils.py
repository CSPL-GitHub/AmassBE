from core.utils import OrderStatus, OrderType
from order.models import Order
from django.db.models import Count, Q
import os
import pandas as pd
from core.models import (
    Product, ProductImage, ProductCategory, ProductCategoryJoint,
    ProductModifierGroup, ProductAndModifierGroupJoint, ProductModifier,
    ProductModifierAndModifierGroupJoint, Platform, Vendor,
)
from django.conf import settings
from django.template.defaultfilters import slugify


def order_count(start_date, end_date, order_type, vendor_id):
    platform = Platform.objects.filter(Name="WooCommerce", isActive=True, VendorId=vendor_id).first()
    
    orders = Order.objects.filter(OrderDate__date__range=(start_date, end_date),  vendorId=vendor_id)

    if order_type == "delivery":
        orders = orders.filter(orderType=OrderType.get_order_type_value('DELIVERY'))
    
    elif order_type == "pickup":
        orders = orders.filter(orderType=OrderType.get_order_type_value('PICKUP'))

    elif order_type == "dinein":
        orders = orders.filter(orderType=OrderType.get_order_type_value('DINEIN'))

    elif order_type == "online":
        if platform:
            orders = orders.filter(platform=platform.pk)

        else:
            count_details = {
                "total_orders": 0,
                "complete_orders": 0,
                "cancelled_orders": 0,
                "processing_orders": 0
            }

            return count_details
        
    elif order_type == "offline":
        if platform:
            orders = orders.exclude(platform=platform.pk)
            
        else:
            count_details = {
                "total_orders": 0,
                "complete_orders": 0,
                "cancelled_orders": 0,
                "processing_orders": 0
            }

            return count_details
    
    count_details = orders.aggregate(
        total_orders=Count('id'),
        complete_orders=Count('id', filter=Q(Status=OrderStatus.get_order_status_value('COMPLETED'))),
        cancelled_orders=Count('id', filter=Q(Status=OrderStatus.get_order_status_value('CANCELED'))),
        processing_orders=Count('id', filter=Q(Status__in=[
            OrderStatus.get_order_status_value('OPEN'),
            OrderStatus.get_order_status_value('INPROGRESS'),
            OrderStatus.get_order_status_value('PREPARED')
        ]))
    )
    
    return count_details


def get_product_data(product_instance ,vendor_id):
    selected_image = ProductImage.objects.filter(product=product_instance.pk).first()

    product_data = {
        "id": product_instance.pk,
        "plu": product_instance.PLU,
        "name": product_instance.productName,
        "name_ar": product_instance.productName_ar,
        "description": product_instance.productDesc if product_instance.productDesc else "",
        "description_ar": product_instance.productDesc_ar if product_instance.productDesc_ar else "",
        "price": product_instance.productPrice,
        "is_active": product_instance.active,
        "tag": product_instance.tag if product_instance.tag else "",
        "tag_ar": product_instance.tag_ar if product_instance.tag_ar else "",
        "is_displayed_online": product_instance.is_displayed_online,
        "selected_image": selected_image.url if selected_image and selected_image.url else "",
        "vendorId": product_instance.vendorId.pk,
        "categories": [],
        "images": [],
        "modifier_groups": [],
    }

    product_category = ProductCategoryJoint.objects.filter(product=product_instance.pk, vendorId=vendor_id).first()

    if product_category:
        if product_category.category:
            product_data["categories"].append({
                "id": product_category.category.pk,
                "plu": product_category.category.categoryPLU,
                "name": product_category.category.categoryName,
                "name_ar": product_category.category.categoryName_ar,
                "description": product_category.category.categoryDescription if product_category.category.categoryDescription else "",
                "description_ar": product_category.category.categoryDescription_ar if product_category.category.categoryDescription_ar else "",
                "image_path": product_category.category.categoryImage.url if product_category.category.categoryImage else "",
                "image_url": product_category.category.categoryImageUrl if product_category.category.categoryImageUrl else "",
                "image_selection": product_category.category.image_selection if product_category.category.image_selection else ""
            })

    product_images = ProductImage.objects.filter(product=product_instance.pk, vendorId=vendor_id)

    if product_images:
        for product_image in product_images:
            if product_image.url:
                product_data["images"].append({
                    "id": product_image.pk,
                    "image": product_image.url,
                    "is_selected": True
                })

    product_modifier_groups = ProductAndModifierGroupJoint.objects.filter(product=product_instance.pk, vendorId=vendor_id)
    
    if product_modifier_groups:
        for modifier_group in product_modifier_groups:
            modifier_data = []

            joint_details = ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=modifier_group.modifierGroup.pk, vendor=vendor_id)

            if joint_details.count() > 0:
                for joint in joint_details:
                    modifier_data.append({
                        "id": joint.modifier.pk,
                        "plu": joint.modifier.modifierPLU,
                        "name": joint.modifier.modifierName,
                        "name_ar": joint.modifier.modifierName_ar,
                        "description": joint.modifier.modifierDesc if joint.modifier.modifierDesc else "",
                        "description_ar": joint.modifier.modifierDesc_ar if joint.modifier.modifierDesc_ar else "",
                        "price": joint.modifier.modifierPrice,
                        "image": joint.modifier.modifierImg if joint.modifier.modifierImg else "",
                        "is_active": joint.modifier.active,
                    })
            
            product_data["modifier_groups"].append({
                "id": modifier_group.modifierGroup.pk,
                "plu": modifier_group.modifierGroup.PLU,
                "name": modifier_group.modifierGroup.name,
                "name_ar": modifier_group.modifierGroup.name_ar,
                "description": modifier_group.modifierGroup.modifier_group_description if modifier_group.modifierGroup.modifier_group_description else "",
                "description_ar": modifier_group.modifierGroup.modifier_group_description_ar if modifier_group.modifierGroup.modifier_group_description_ar else "",
                "min": modifier_group.modifierGroup.min,
                "max": modifier_group.modifierGroup.max,
                "is_active": modifier_group.modifierGroup.active,
                "modifiers": modifier_data
            })

    return product_data


def process_product_excel(file_path, sheet_name, vendor_id):
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()
    
    if not os.path.exists(file_path):
        print("File does not exist")
        message = "File does not exist"
        return 0, message
    
    if not file_path.lower().endswith(".xlsx"):
        print("File format is not .xlsx")
        message = "File format is not .xlsx"
        return 0, message
    
    if sheet_name != "Sheet1":
        print("Sheet name not found")
        message = "Sheet name should be 'Sheet1'"
        return 4, message
    
    try:
        data = pd.read_excel(file_path, sheet_name=sheet_name)
    except ValueError as e:
        message = "Wrong file format"
        return 3, message
    
    failed_rows = []
    failed_file_path = ''

    specified_columns = [
        "Category Name", "Category SKU", "Category Description", "Is Category Active (yes/no)", "Category Image",
        "Product Name", "Product SKU", "Product Description", "Tag", "Product Price (in Rs.)", "Is Product Active (yes/no)", "Product Image",
        "Modifier Group Name", "Modifier Group SKU", "Modifier Group Description", "Modifier Group Min", "Modifier Group Max", "Is Modifier Group Active (yes/no)",
        "Modifier Name", "Modifier SKU", "Modifier Description", "Modifier Price (in Rs.)", "Modifier Active (yes/no)", "Modifier Image"
    ]

    existing_columns = data.columns.tolist()

    non_existing_columns = []

    for column_name in specified_columns:
        if column_name not in existing_columns:
            non_existing_columns.append(column_name)

    if non_existing_columns:
        print("Following columns not found: ", non_existing_columns)
        message = f"Following columns not found: {non_existing_columns}"
        return 2, message

    for index, row in data.iterrows():
        try:
            if pd.isnull(row["Category Name"]) or row["Category Name"] == "":
                row["Error"] = "Category Name null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Category Name null or empty\n")
                continue 
            
            if pd.isnull(row["Category SKU"]) or row["Category SKU"] == "":
                row["Error"] = "Category SKU null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Category SKU null or empty\n")
                continue

            if pd.isnull(row["Product Name"]) or row["Product Name"] == "":
                row["Error"] = "Product Name null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Product Name null or empty\n")
                continue
            
            if pd.isnull(row["Product SKU"]) or row["Product SKU"] == "":
                row["Error"] = "Product SKU null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Product SKU null or empty\n")
                continue

            if pd.isnull(row["Product Price (in Rs.)"]) or row["Product Price (in Rs.)"] == "":
                row["Error"] = "Product Price (in Rs.) null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Product Price (in Rs.) null or empty\n")
                continue

            if pd.isnull(row["Product Image"]) or row["Product Image"] == "":
                row["Error"] = "Product Image null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Product Image null or empty\n")
                continue

            if (row["Product Price (in Rs.)"] < 0):
                row["Error"] = "Product Price (in Rs.) negative"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Cell value negative \n")
                continue
            
            existing_category = ProductCategory.objects.filter(
                categoryPLU = row["Category SKU"],
                vendorId = vendor_id,
            ).exists()

            if not existing_category:
                category_description = row["Category Description"]
                category_image = row["Category Image"]
                
                if pd.isnull(row["Category Description"]) or row["Category Description"] == "":
                    category_description = None

                if pd.isnull(row["Category Image"]) or row["Category Image"] == "":
                    category_image = None

                if row["Is Category Active (yes/no)"].lower() == "yes":
                    is_active = True
                elif row["Is Category Active (yes/no)"].lower() == "no":
                    is_active = False
                else:
                    row["Error"] = "Is Category Active (yes/no) should be 'yes' or 'no'"
                    failed_rows.append(row)
                    print(f"Error processing row: {row}, Error: Cell value not 'yes' or 'no'\n")
                    continue
                
                category_instance = ProductCategory.objects.create(
                    categoryName = row["Category Name"],
                    categoryDescription = category_description,
                    categoryImageUrl = category_image,
                    categoryPLU = row["Category SKU"],
                    categorySlug = slugify(str(row["Category Name"]).lower()),
                    vendorId = vendor_instance,
                    is_active=is_active
                )
                # Columns with default value:
                # categoryParentId, categoryStatus, categoryImage, categoryCreatedAt, categoryUpdatedAt, categoryIsDeleted, categoryStation

            existing_product = Product.objects.filter(
                PLU = row["Product SKU"],
                vendorId = vendor_id,
            ).exists()

            if not existing_product:
                if row["Is Product Active (yes/no)"].lower() == "yes":
                    is_active = True
                elif row["Is Product Active (yes/no)"].lower() == "no":
                    is_active = False
                else:
                    row["Error"] = "Is Product Active (yes/no) should be 'yes' or 'no'"
                    failed_rows.append(row)
                    print(f"Error processing row: {row}, Error: Cell value not 'yes' or 'no'\n")
                    continue

                if row["Tag"].lower() not in ("veg", "non-veg"):
                    print(row["Tag"].lower())
                    row["Error"] = "Tag should be 'veg' or 'non-veg'"
                    failed_rows.append(row)
                    print(f"Error processing row: {row}, Error: Cell value not 'veg' or 'non-veg'\n")
                    continue

                product_description = row["Product Description"]
                
                if pd.isnull(row["Product Description"]) or row["Product Description"] == "":    
                    product_description = None
                
                product_instance = Product.objects.create(
                    PLU = row["Product SKU"],
                    SKU = row["Product SKU"],
                    productName = row["Product Name"],
                    productDesc = product_description,
                    productPrice = row["Product Price (in Rs.)"],
                    tag = row["Tag"],
                    active = is_active,
                    productType = "Regular",
                    Unlimited = 1,
                    vendorId = vendor_instance,
                    taxable = True,
                )
                # Columns with default value:
                # productThumb, productQty, productParentId, preparationTime, isDeleted, meta
                
            if (not(pd.isnull(row["Product SKU"])) and row["Product SKU"] != ""):
                if (not(pd.isnull(row["Product Image"])) and row["Product Image"] != ""):
                    existing_product_images = ProductImage.objects.filter(
                        product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                        url = row["Product Image"],
                        vendorId = vendor_id,
                    ).exists()

                    if not existing_product_images:
                        existing_product_images = ProductImage.objects.create(
                            product = Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first(),
                            url = row["Product Image"],
                            vendorId = vendor_instance,
                        )
                        # default column: image
            
            existing_product_category_joint = ProductCategoryJoint.objects.filter(
                product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                category = (ProductCategory.objects.filter(categoryPLU=row["Category SKU"], vendorId=vendor_id).first()).pk,
                vendorId = vendor_id
            ).exists()

            if not existing_product_category_joint:
                product_category_joint_instance = ProductCategoryJoint.objects.create(
                    product = Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first(),
                    category = ProductCategory.objects.filter(categoryPLU=row["Category SKU"], vendorId=vendor_id).first(),
                    vendorId = vendor_instance
                )
            
            if (pd.isnull(row["Modifier Group SKU"]) or row["Modifier Group SKU"] == "") and \
            (pd.isnull(row["Modifier SKU"]) or row["Modifier SKU"] == ""):
                pass
            
            elif (pd.isnull(row["Modifier Group SKU"]) or row["Modifier Group SKU"] == "") and \
            ((not(pd.isnull(row["Modifier SKU"]))) or row["Modifier SKU"] != ""):
                row["Error"] = "Modifier is without modifier group"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Modifier is without modifier group\n")
                continue

            elif ((not(pd.isnull(row["Modifier Group SKU"]))) or row["Modifier Group SKU"] != "") and \
            (pd.isnull(row["Modifier SKU"]) or row["Modifier SKU"] == ""):
                row["Error"] = "Modifier group has no modifiers"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Modifier group has no modifiers\n")
                continue

            else:
                existing_modifier_group = ProductModifierGroup.objects.filter(
                    PLU = row["Modifier Group SKU"],
                    vendorId = vendor_id,
                ).exists()

                if not existing_modifier_group:
                    if row["Is Modifier Group Active (yes/no)"] == "yes":
                        is_active = True
                    elif row["Is Modifier Group Active (yes/no)"] == "no":
                        is_active = False
                    else:
                        row["Error"] = "Is Modifier Group Active (yes/no) should be 'yes' or 'no'"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Cell value not 'yes' or 'no'\n")
                        continue
                    
                    if pd.isnull(row["Modifier Group Min"]) or row["Modifier Group Min"] == "":
                        row["Error"] = "Modifier Group Min null or empty"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Group Min null or empty\n")
                        continue

                    if pd.isnull(row["Modifier Group Max"]) or row["Modifier Group Max"] == "":
                        row["Error"] = "Modifier Group Max null or empty"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Group Max null or empty\n")
                        continue

                    try:
                        modifier_group_min = int(row["Modifier Group Min"])
                        modifier_group_max = int(row["Modifier Group Max"])

                    except ValueError:
                        row["Error"] = "Modifier Group Min or Max invalid"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Group Min or Max invalid\n")
                        continue
                    
                    modifier_group_description = row["Modifier Group Description"]
                    
                    if pd.isnull(row["Modifier Group Description"]) or row["Modifier Group Description"] == "":
                        modifier_group_description = None
                    
                    modifier_group_instance = ProductModifierGroup.objects.create(
                        name = row["Modifier Group Name"],
                        PLU = row["Modifier Group SKU"],
                        slug = slugify(str(row["Modifier Group Name"]).lower()),
                        modifier_group_description = modifier_group_description,
                        min = modifier_group_min,
                        max = modifier_group_max,
                        modGrptype = "MULTIPLE",
                        vendorId = vendor_instance,
                        active = is_active
                    )
                    # Columns with default value: isDeleted, sortOrder
                    
                existing_modifier = ProductModifier.objects.filter(
                    modifierPLU = row["Modifier SKU"],
                    vendorId = vendor_id,
                ).exists()

                if not existing_modifier:
                    if pd.isnull(row["Modifier Price (in Rs.)"]) or row["Modifier Price (in Rs.)"] == "":
                        row["Error"] = "Modifier Price (in Rs.) null or empty"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Price (in Rs.) null or empty")
                        continue

                    if (row["Modifier Price (in Rs.)"] < 0):
                        row["Error"] = "Modifier Price (in Rs.) negative"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Cell value negative \n")
                        continue

                    try:
                        modifier_price = float(row["Modifier Price (in Rs.)"])

                    except ValueError:
                        row["Error"] = "Modifier Price (in Rs.) invalid"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Price (in Rs.) invalid")
                        continue

                    if row["Modifier Active (yes/no)"] == "yes":
                        is_active = True

                    elif row["Modifier Active (yes/no)"] == "no":
                        is_active = False

                    else:
                        row["Error"] = "Modifier Active (yes/no) should be 'yes' or 'no'"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Cell value not 'yes' or 'no'\n")
                        continue
                    
                    if pd.isnull(row["Modifier Image"]) or row["Modifier Image"] == "":
                        row["Error"] = "Modifier Image null or empty"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Image null or empty\n")
                        continue
                    
                    modifier_description = row["Modifier Description"]
                    
                    if pd.isnull(row["Modifier Description"]) or row["Modifier Description"] == "":
                        modifier_description = None

                    modifier_image = row["Modifier Image"]
                    
                    if pd.isnull(row["Modifier Image"]) or row["Modifier Image"] == "":
                        modifier_image = None
                    
                    modifier_instance = ProductModifier.objects.create(
                        modifierName=row["Modifier Name"],
                        modifierPLU=row["Modifier SKU"],
                        modifierSKU=row["Modifier SKU"],
                        modifierPrice=modifier_price,
                        modifierDesc=modifier_description,
                        modifierImg=row["Modifier Image"],
                        active = is_active,
                        vendorId = vendor_instance,
                    )
                    # Columns with default value: modifierImg, modifierQty, modifierStatus, isDeleted, paretId

                existing_product_modgroup_joint = ProductAndModifierGroupJoint.objects.filter(
                    modifierGroup = (ProductModifierGroup.objects.filter(PLU=row["Modifier Group SKU"], vendorId=vendor_id).first()).pk,
                    product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                    vendorId = vendor_id
                ).exists()

                if not existing_product_modgroup_joint:
                    if row["Is Modifier Group Active (yes/no)"] == "yes":
                        is_active = True
                    elif row["Is Modifier Group Active (yes/no)"] == "no":
                        is_active = False
                    else:
                        row["Error"] = "Is Modifier Group Active (yes/no) should be 'yes' or 'no'"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Cell value not 'yes' or 'no'\n")
                        continue
                    
                    product_modgroup_joint_instance = ProductAndModifierGroupJoint.objects.create(
                        modifierGroup = ProductModifierGroup.objects.filter(PLU=row["Modifier Group SKU"], vendorId=vendor_id).first(),
                        product = Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first(),
                        min = row["Modifier Group Min"],
                        max = row["Modifier Group Max"],
                        active = is_active,
                        isEnabled = is_active,
                        vendorId = vendor_instance
                    )

                existing_product_modifier_modgroup_joint = ProductModifierAndModifierGroupJoint.objects.filter(
                    modifierGroup = (ProductModifierGroup.objects.filter(PLU=row["Modifier Group SKU"], vendorId=vendor_id).first()).pk, 
                    modifier = (ProductModifier.objects.filter(modifierPLU=row["Modifier SKU"], vendorId=vendor_id).first()).pk,
                    vendor = vendor_id
                ).exists()

                if not existing_product_modifier_modgroup_joint:
                    product_modifier_modgroup_joint_instance = ProductModifierAndModifierGroupJoint.objects.create(
                        modifierGroup = ProductModifierGroup.objects.filter(PLU=row["Modifier Group SKU"], vendorId=vendor_id).first(),
                        modifier = ProductModifier.objects.filter(modifierPLU=row["Modifier SKU"], vendorId=vendor_id).first(),
                        vendor = vendor_instance
                    )
        
        except Exception as e:
            row["Error"] = str(e)
            failed_rows.append(row)
            print(f"Error processing row: {row}, Error: {str(e)}\n")
    
    if failed_rows:
        directory = os.path.join(settings.MEDIA_ROOT, 'Product Details Excel')
        os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

        file_name = f"failed_rows_Vendor{vendor_id}.xlsx"

        relative_file_path = os.path.join('Product Details Excel', file_name)

        failed_file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
        
        failed_df = pd.DataFrame(failed_rows)

        failed_df.to_excel(failed_file_path, index=False)

        failed_file_path = "/media/" + relative_file_path

    print("Excel file processing completed")
    
    if failed_file_path:
        return 1, failed_file_path
    
    else:
        failed_file_path = None
        return 1, failed_file_path
