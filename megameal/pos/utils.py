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
from koms.models import Station
from django.conf import settings
from django.template.defaultfilters import slugify


def order_count(start_date, end_date, order_type, vendor_id):
    platform = Platform.objects.filter(Name__in=("Mobile App", "Website"), isActive=True, VendorId=vendor_id).first()
    
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


def get_product_by_category_data(products, language, vendor_id):
    product_list = []

    for product in products:
        # product_variants = []

        # if product.productType == "Variant":
        #     for variant in Product.objects.filter(productParentId=product.pk, vendorId=vendor_id, isDeleted=False):
        #         images = []

        #         for instance in ProductImage.objects.filter(product=variant.pk):
        #             if instance is not None:
        #                 images.append(str(instance.image))
                
        #         options = []

        #         for varinatJoint in Product_Option_Joint.objects.filter(productId=variant.pk, vendorId=vendor_id):
        #             options.append(
        #                 {
        #                     "optionId":varinatJoint.optionId.optionId, 
        #                     "optionValueId":varinatJoint.optionValueId.itemOptionId 
        #                 }
        #             )

        #         product_variants.append({
        #             "text":variant.productName,
        #             # "imagePath": HOST+variant.productThumb.name if variant.productThumb !="" else images[0] if len(images)!=0 else HOST+DEFAULTIMG,
        #             # "images":images if len(images)  else [HOST+DEFAULTIMG],
        #             "quantity": 0,
        #             "cost": variant.productPrice,
        #             "description":variant.productDesc,
        #             "allowCustomerNotes": True,
        #             "plu":variant.PLU,
        #             "type":variant.productType,
        #             "options":options
        #         })

        images = []

        product_images = ProductImage.objects.filter(product=product.pk, vendorId=vendor_id)

        for instance in product_images:
            if instance is not None:
                images.append(str(instance.url))
        
        modifier_group_list = []

        product_and_modifier_group_joint = ProductAndModifierGroupJoint.objects.filter(product=product.pk, vendorId=vendor_id)
        
        if product_and_modifier_group_joint:
            for product_and_modifier_group_instance in product_and_modifier_group_joint:
                modifier_list = []

                modifier_and_group_joint = ProductModifierAndModifierGroupJoint.objects.filter(modifierGroup=product_and_modifier_group_instance.modifierGroup.pk, modifierGroup__isDeleted=False, vendor=vendor_id)
                
                if modifier_and_group_joint:
                    for modifier_and_group_instance in modifier_and_group_joint:
                        modifier_name = ""
                        modifier_description = ""

                        if language == "English":
                            modifier_name = modifier_and_group_instance.modifier.modifierName
                            modifier_description = modifier_and_group_instance.modifier.modifierDesc

                        else:
                            modifier_name = modifier_and_group_instance.modifier.modifierName_locale
                            modifier_description = modifier_and_group_instance.modifier.modifierDesc_locale
                        
                        modifier_list.append(
                            {
                                "cost": modifier_and_group_instance.modifier.modifierPrice,
                                "modifierId": modifier_and_group_instance.modifier.pk,
                                "name": modifier_name,
                                "description": modifier_description,
                                "quantity": 0,
                                "plu": modifier_and_group_instance.modifier.modifierPLU,
                                "image": modifier_and_group_instance.modifier.modifierImg if modifier_and_group_instance.modifier.modifierImg else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
                                # "image":modifier_and_group_instance.modifier.modifierImg,
                                "status": True, # Required for order helper function
                                "active": modifier_and_group_instance.modifier.active
                            }                    
                        )

                if product_and_modifier_group_instance.modifierGroup.isDeleted == False: 
                    modifier_group_name = ""
                    modifier_group_description = ""

                    if language == "English":
                        modifier_group_name = product_and_modifier_group_instance.modifierGroup.name
                        modifier_group_description = product_and_modifier_group_instance.modifierGroup.modifier_group_description
                    
                    else:
                        modifier_group_name = product_and_modifier_group_instance.modifierGroup.name_locale
                        modifier_group_description = product_and_modifier_group_instance.modifierGroup.modifier_group_description_locale

                    modifier_group_list.append(
                    {
                        "id": product_and_modifier_group_instance.modifierGroup.pk,
                        "name": modifier_group_name,
                        "plu": product_and_modifier_group_instance.modifierGroup.PLU,
                        "description": modifier_group_description,
                        # "min": product_and_modifier_group_instance.min,
                        # "max": product_and_modifier_group_instance.max,
                        "min": product_and_modifier_group_instance.modifierGroup.min,
                        "max": product_and_modifier_group_instance.modifierGroup.max,
                        # "type": product_and_modifier_group_instance.modifierGroup.modGrptype,
                        "active": product_and_modifier_group_instance.modifierGroup.active,
                        "modifiers": modifier_list
                    }
                )
            
        category_id = 0
        category_name = ""
        product_name = ""
        product_description = ""

        product_category_joint = ProductCategoryJoint.objects.filter(product=product.pk).first()

        if product_category_joint:
            category_id = product_category_joint.category.pk

            if language == "English":
                category_name = product_category_joint.category.categoryName

            else:
                category_name = product_category_joint.category.categoryName_locale
        
        if language == "English":
            product_name = product.productName
            product_description = product.productDesc if product.productDesc else ""
        
        else:
            product_name = product.productName_locale
            product_description = product.productDesc_locale if product.productDesc_locale else ""
        
        product_list.append({
            "categoryId": category_id,
            "categoryName": category_name,
            "productId": product.pk,
            "plu": product.PLU,
            "name": product_name,
            "description": product_description,
            "cost": product.productPrice,
            "tag":  product.tag if product.tag else "",
            "imagePath": images[0] if len(images)!=0 else 'https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg',
            "images": images if len(images)>0  else ['https://www.stockvault.net/data/2018/08/31/254135/preview16.jpg'],
            "isTaxable": product.taxable,
            "type": product.productType,
            "variant": [],
            "quantity": 0, # Required for Flutter model
            "active": product.active,
            "modifiersGroup": modifier_group_list,
        })

    return product_list


def get_product_data(product_instance ,vendor_id):
    selected_image = ProductImage.objects.filter(product=product_instance.pk).first()

    product_data = {
        "id": product_instance.pk,
        "plu": product_instance.PLU,
        "name": product_instance.productName,
        "name_locale": product_instance.productName_locale,
        "description": product_instance.productDesc if product_instance.productDesc else "",
        "description_locale": product_instance.productDesc_locale if product_instance.productDesc_locale else "",
        "price": product_instance.productPrice,
        "is_active": product_instance.active,
        "tag": product_instance.tag if product_instance.tag else "",
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
                "name_locale": product_category.category.categoryName_locale,
                "description": product_category.category.categoryDescription if product_category.category.categoryDescription else "",
                "description_locale": product_category.category.categoryDescription_locale if product_category.category.categoryDescription_locale else "",
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
                        "name_locale": joint.modifier.modifierName_locale,
                        "description": joint.modifier.modifierDesc if joint.modifier.modifierDesc else "",
                        "description_locale": joint.modifier.modifierDesc_locale if joint.modifier.modifierDesc_locale else "",
                        "price": joint.modifier.modifierPrice,
                        "image": joint.modifier.modifierImg if joint.modifier.modifierImg else "",
                        "is_active": joint.modifier.active,
                    })
            
            product_data["modifier_groups"].append({
                "id": modifier_group.modifierGroup.pk,
                "plu": modifier_group.modifierGroup.PLU,
                "name": modifier_group.modifierGroup.name,
                "name_locale": modifier_group.modifierGroup.name_locale,
                "description": modifier_group.modifierGroup.modifier_group_description if modifier_group.modifierGroup.modifier_group_description else "",
                "description_locale": modifier_group.modifierGroup.modifier_group_description_locale if modifier_group.modifierGroup.modifier_group_description_locale else "",
                "min": modifier_group.modifierGroup.min,
                "max": modifier_group.modifierGroup.max,
                "is_active": modifier_group.modifierGroup.active,
                "modifiers": modifier_data
            })

    return product_data


def get_modifier_data(modifier_instance, vendor_id):
    modifier_data = {
        "id": modifier_instance.pk,
        "plu": modifier_instance.modifierPLU,
        "name": modifier_instance.modifierName,
        "name_locale": modifier_instance.modifierName_locale,
        "description": modifier_instance.modifierDesc if modifier_instance.modifierDesc else "",
        "description_locale": modifier_instance.modifierDesc_locale if modifier_instance.modifierDesc_locale else "",
        "image": modifier_instance.modifierImg if modifier_instance.modifierImg else "",
        "price": modifier_instance.modifierPrice,
        "is_active": modifier_instance.active,
        "vendorId": modifier_instance.vendorId.pk,
        "modifier_groups": [],
    }

    modifier_group_joint = ProductModifierAndModifierGroupJoint.objects.filter(modifier=modifier_instance.pk, vendor=vendor_id)

    for joint in modifier_group_joint:
        modifier_data["modifier_groups"].append({
            "id": joint.modifierGroup.pk,
            "plu": joint.modifierGroup.PLU,
            "name": joint.modifierGroup.name,
            "name_locale": joint.modifierGroup.name_locale,
            "description": joint.modifierGroup.modifier_group_description if joint.modifierGroup.modifier_group_description else "",
            "description_locale": joint.modifierGroup.modifier_group_description_locale if joint.modifierGroup.modifier_group_description_locale else "",
            "min": joint.modifierGroup.min,
            "max": joint.modifierGroup.max,
            "is_active": joint.modifierGroup.active,
        })

    return modifier_data


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

    if not vendor_instance.secondary_language:
        specified_columns = [
            "Category Name", "Category SKU", "Category Description", "Is Category Active (yes/no)", "Category Image",
            "Product Name", "Product SKU", "Product Description", "Tag", "Product Price", "Is Product Active (yes/no)", "Product Image",
            "Modifier Group Name", "Modifier Group SKU", "Modifier Group Description", "Modifier Group Min", "Modifier Group Max", "Is Modifier Group Active (yes/no)",
            "Modifier Name", "Modifier SKU", "Modifier Description", "Modifier Price", "Modifier Active (yes/no)", "Modifier Image"
        ]

    else:
        specified_columns = [
            "Category Name", "Category Name (Locale)", "Category SKU", "Category Description", "Category Description (Locale)", "Is Category Active (yes/no)", "Category Image",
            "Product Name", "Product Name (Locale)", "Product SKU", "Product Description", "Product Description (Locale)", "Tag", "Product Price", "Is Product Active (yes/no)", "Product Image",
            "Modifier Group Name", "Modifier Group Name (Locale)", "Modifier Group SKU", "Modifier Group Description", "Modifier Group Description (Locale)", "Modifier Group Min", "Modifier Group Max", "Is Modifier Group Active (yes/no)",
            "Modifier Name", "Modifier Name (Locale)", "Modifier SKU", "Modifier Description", "Modifier Description (Locale)", "Modifier Price", "Modifier Active (yes/no)", "Modifier Image"
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
            if pd.isnull(row["Category Station"]) or row["Category Station"] == "":
                row["Error"] = "Category Station null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Category Station null or empty\n")
                continue 
            
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

            if pd.isnull(row["Product Price"]) or row["Product Price"] == "":
                row["Error"] = "Product Price null or empty"
                failed_rows.append(row)
                print(f"Error processing row: {row}, Error: Product Price null or empty\n")
                continue

            if (row["Product Price"] < 0):
                row["Error"] = "Product Price negative"
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
                
                category_station_instance = Station.objects.filter(station_name=row["Category Station"], vendorId=vendor_instance.pk).first()

                if not category_station_instance:
                    row["Error"] = "Category Station not created"
                    failed_rows.append(row)
                    print(f"Error processing row: {row}, Error: Category Station not created\n")
                    continue
                
                if not vendor_instance.secondary_language:
                    category_instance = ProductCategory.objects.create(
                        categoryStation = category_station_instance,
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

                else:
                    category_instance = ProductCategory.objects.create(
                        categoryStation = category_station_instance,
                        categoryName = row["Category Name"],
                        categoryName_locale = row["Category Name (Locale)"],
                        categoryDescription = category_description,
                        categoryDescription_locale = row["Category Description (Locale)"],
                        categoryImageUrl = category_image,
                        categoryPLU = row["Category SKU"],
                        categorySlug = slugify(str(row["Category Name"]).lower()),
                        vendorId = vendor_instance,
                        is_active=is_active
                    )

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
                
                if not vendor_instance.secondary_language:
                    product_instance = Product.objects.create(
                        PLU = row["Product SKU"],
                        SKU = row["Product SKU"],
                        productName = row["Product Name"],
                        productDesc = product_description,
                        productPrice = row["Product Price"],
                        tag = row["Tag"],
                        active = is_active,
                        productType = "Regular",
                        vendorId = vendor_instance,
                        taxable = True,
                    )
                    # Columns with default value:
                    # productThumb, productParentId, preparationTime, isDeleted, meta, is_unlimited

                else:
                    product_instance = Product.objects.create(
                        PLU = row["Product SKU"],
                        SKU = row["Product SKU"],
                        productName = row["Product Name"],
                        productName_locale = row["Product Name (Locale)"],
                        productDesc = product_description,
                        productDesc_locale = row["Product Description (Locale)"],
                        productPrice = row["Product Price"],
                        tag = row["Tag"],
                        active = is_active,
                        productType = "Regular",
                        vendorId = vendor_instance,
                        taxable = True,
                    )
                
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
                    
                    if not vendor_instance.secondary_language:
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
                        # Columns with default value: isDeleted

                    else:
                        modifier_group_instance = ProductModifierGroup.objects.create(
                            name = row["Modifier Group Name"],
                            name_locale = row["Modifier Group Name (Locale)"],
                            PLU = row["Modifier Group SKU"],
                            slug = slugify(str(row["Modifier Group Name"]).lower()),
                            modifier_group_description = modifier_group_description,
                            modifier_group_description_locale = row["Modifier Group Description (Locale)"],
                            min = modifier_group_min,
                            max = modifier_group_max,
                            modGrptype = "MULTIPLE",
                            vendorId = vendor_instance,
                            active = is_active
                        )
                        # Columns with default value: isDeleted
                    
                existing_modifier = ProductModifier.objects.filter(
                    modifierPLU = row["Modifier SKU"],
                    vendorId = vendor_id,
                ).exists()

                if not existing_modifier:
                    if pd.isnull(row["Modifier Price"]) or row["Modifier Price"] == "":
                        row["Error"] = "Modifier Price null or empty"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Price null or empty")
                        continue

                    if (row["Modifier Price"] < 0):
                        row["Error"] = "Modifier Price negative"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Cell value negative \n")
                        continue

                    try:
                        modifier_price = float(row["Modifier Price"])

                    except ValueError:
                        row["Error"] = "Modifier Price invalid"
                        failed_rows.append(row)
                        print(f"Error processing row: {row}, Error: Modifier Price invalid")
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
                    
                    if not vendor_instance.secondary_language:
                        modifier_instance = ProductModifier.objects.create(
                            modifierName=row["Modifier Name"],
                            modifierPLU=row["Modifier SKU"],
                            modifierSKU=row["Modifier SKU"],
                            modifierPrice=modifier_price,
                            modifierDesc=modifier_description,
                            modifierImg=modifier_image,
                            active=is_active,
                            vendorId=vendor_instance,
                        )
                        # Columns with default value: modifierImg, isDeleted, parentId

                    else:
                        modifier_instance = ProductModifier.objects.create(
                            modifierName=row["Modifier Name"],
                            modifierName_locale=row["Modifier Name (Locale)"],
                            modifierPLU=row["Modifier SKU"],
                            modifierSKU=row["Modifier SKU"],
                            modifierPrice=modifier_price,
                            modifierDesc=modifier_description,
                            modifierDesc_locale=row["Modifier Description (Locale)"],
                            modifierImg=modifier_image,
                            active=is_active,
                            vendorId=vendor_instance,
                        )

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
