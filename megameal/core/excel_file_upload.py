import threading
import os
import re
import pandas as pd
from django.db import transaction
from core.models import (
    Product,
    ProductImage,
    ProductCategory,
    ProductCategoryJoint,
    ProductModifierGroup,
    ProductAndModifierGroupJoint,
    ProductModifier,
    ProductModifierAndModifierGroupJoint,
    Vendor,
)
from django.conf import settings
from django.template.defaultfilters import slugify


def process_excel(file_path, sheet_name, vendor_id):
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if vendor_instance:
        if os.path.exists(file_path):
            if file_path.lower().endswith(".xlsx"):
                data = pd.read_excel(file_path, sheet_name=sheet_name)

                if sheet_name == "Sheet1":
                        failed_rows = []
                        failed_file_path = ''

                        with transaction.atomic():
                            for index, row in data.iterrows():
                                try:
                                    if pd.isnull(row["Category SKU"]) or row["Category SKU"] == "":
                                        row["Error"] = "Category SKU null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Category SKU null or empty")
                                        continue

                                    if pd.isnull(row["Category Name"]) or row["Category Name"] == "":
                                        row["Error"] = "Category Name null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Category Name null or empty")
                                        continue 

                                    if pd.isnull(row["Product SKU"]) or row["Product SKU"] == "":
                                        row["Error"] = "Product SKU null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product SKU null or empty")
                                        continue

                                    if pd.isnull(row["Product Name"]) or row["Product Name"] == "":
                                        row["Error"] = "Product Name null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product Name null or empty")
                                        continue

                                    if pd.isnull(row["Product Active"]) or row["Product Active"] == "":
                                        row["Error"] = "Product Active null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product Active null or empty")
                                        continue

                                    if pd.isnull(row["Regular Price"]) or row["Regular Price"] == "":
                                        row["Error"] = "Regular Price null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Regular Price null or empty")
                                        continue

                                    if pd.isnull(row["Product Images"]) or row["Product Images"] == "":
                                        row["Error"] = "Product Image null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product Images null or empty")
                                        continue

                                    # if pd.isnull(row["Modifier Group SKU"]) or row["Modifier Group SKU"] == "":
                                    #     row["Error"] = "Modifier Group SKU null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group SKU null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Group Name"]) or row["Modifier Group Name"] == "":
                                    #     row["Error"] = "Modifier Group Name null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group Name null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Group Min"]) or row["Modifier Group Min"] == "":
                                    #     row["Error"] = "Modifier Group Min null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group Min null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Group Max"]) or row["Modifier Group Max"] == "":
                                    #     row["Error"] = "Modifier Group Max null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group Max null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Group Active"]) or row["Modifier Group Active"] == "":
                                    #     row["Error"] = "Modifier Group Active null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group Active null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier SKU"]) or row["Modifier SKU"] == "":
                                    #     row["Error"] = "Modifier SKU null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier SKU null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Name"]) or row["Modifier Name"] == "":
                                    #     row["Error"] = "Modifier Name null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Name null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Price"]) or row["Modifier Price"] == "":
                                    #     row["Error"] = "Modifier Name null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Name null or empty")
                                    #     continue

                                    # if pd.isnull(row["Modifier Active"]) or row["Modifier Active"] == "":
                                    #     row["Error"] = "Modifier Active null or empty"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Cell null or empty")
                                    #     continue

                                    if (row["Regular Price"] < 0):
                                        row["Error"] = "Regular Price negative"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Cell value negative")
                                        continue

                                    if ((row["Product Active"] != 'Y') and (row["Product Active"] != 'N')):
                                        row["Error"] = "Product Active not 'Y' or 'N'"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Cell value not 'Y' or 'N'")
                                        continue
                                    
                                    # if not re.match("[a-zA-Z0-9]", str(row["Category SKU"])):
                                    #     row["Error"] = "Category SKU should be alphanumeric"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Category SKU should be alphanumeric")
                                    #     continue

                                    # if not re.match("[a-zA-Z0-9]", str(row["Product SKU"])):
                                    #     row["Error"] = "Product SKU should be alphanumeric"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Product SKU should be alphanumeric")
                                    #     continue

                                    # if not re.match("[a-zA-Z0-9]", str(row["Modifier Group SKU"])):
                                    #     row["Error"] = "Modifier Group SKU should be alphanumeric"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group SKU should be alphanumeric")
                                    #     continue

                                    # if not re.match("[a-zA-Z0-9]", str(row["Modifier SKU"])):
                                    #     row["Error"] = "Modifier SKU should be alphanumeric"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier SKU should be alphanumeric")
                                    #     continue

                                    # if not re.match("[a-zA-Z]", str(row["Category Name"])):
                                    #     row["Error"] = "Category Name should be alphabets"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Category Name should be alphabets")
                                    #     continue

                                    # if not re.match("[a-zA-Z]", str(row["Product Name"])):
                                    #     row["Error"] = "Product Name should be alphabets"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Product Name should be alphabets")
                                    #     continue

                                    # if not re.match("[a-zA-Z]", str(row["Modifier Group Name"])):
                                    #     row["Error"] = "Modifier Group Name should be alphabets"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Group Name should be alphabets")
                                    #     continue

                                    # if not re.match("[a-zA-Z]", str(row["Modifier Name"])):
                                    #     row["Error"] = "Modifier Name should be alphabets"
                                    #     failed_rows.append(row)
                                    #     print(f"Error processing row: {row}, Error: Modifier Name should be alphabets")
                                    #     continue
                                    
                                    # Using filter() instead of get() because exists only works on filter()
                                    # filter() does not stops the execution of code if value is not found, hence used with first()
                                    existing_category = ProductCategory.objects.filter(
                                        categoryPLU = row["Category SKU"],
                                        vendorId = vendor_id,
                                    ).exists()

                                    if not existing_category:
                                            category_image = ""

                                            if (not pd.isnull(row["Category Image"])) or (row["Category Image"] != ""):
                                                category_image = row["Category Image"]

                                            category_instance = ProductCategory.objects.create(
                                                categoryName = row["Category Name"],
                                                categoryDescription = None if pd.isnull(row["Category Desc"]) or row["Category Desc"] == "" else row["Category Desc"],
                                                categoryPLU = row["Category SKU"],
                                                categorySlug = slugify(str(row["Category Name"]).lower()),
                                                categoryImageUrl = category_image,
                                                vendorId = vendor_instance,
                                            )
                                            # Columns with default value:
                                            # categoryParentId, categoryImage, categoryCreatedAt, categoryUpdatedAt, categoryIsDeleted, categoryStation

                                    existing_product = Product.objects.filter(
                                        PLU = row["Product SKU"],
                                        vendorId = vendor_id,
                                    ).exists()

                                    if not existing_product:
                                        if row["Product Active"] == "Y":
                                            is_active = True
                                        elif row["Product Active"] == "N":
                                            is_active = False

                                        product_instance = Product.objects.create(
                                            PLU = row["Product SKU"],
                                            SKU = row["Product SKU"],
                                            productName = row["Product Name"],
                                            productDesc = None if pd.isnull(row["Product Desc"]) or row["Product Desc"] == "" else row["Product Desc"],
                                            productPrice = row["Regular Price"],
                                            tag = None if pd.isnull(row["Tags"]) or row["Tags"] == "" else row["Tags"],
                                            active = is_active,
                                            productType = "Regular",
                                            vendorId = vendor_instance,
                                            taxable = True,
                                        )
                                        # Columns with default value:
                                        # productThumb, productParentId, preparationTime, isDeleted, meta, is_unlimited
                                        
                                    if (not(pd.isnull(row["Product SKU"])) and row["Product SKU"] != ""):
                                        if (not(pd.isnull(row["Product Images"])) and row["Product Images"] != ""):
                                            existing_product_images = ProductImage.objects.filter(
                                                product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                                                url = row["Product Images"],
                                                vendorId = vendor_id,
                                            ).exists()

                                            if not existing_product_images:
                                                existing_product_images = ProductImage.objects.create(
                                                    product = Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first(),
                                                    url = row["Product Images"],
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
                                        print(f"Error processing row: {row}, Error: Modifier is without modifier group")
                                        continue

                                    elif ((not(pd.isnull(row["Modifier Group SKU"]))) or row["Modifier Group SKU"] != "") and \
                                    (pd.isnull(row["Modifier SKU"]) or row["Modifier SKU"] == ""):
                                        row["Error"] = "Modifier group has no modifiers"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Modifier group has no modifiers")
                                        continue

                                    else:
                                        existing_modifier_group = ProductModifierGroup.objects.filter(
                                            PLU = row["Modifier Group SKU"],
                                            vendorId = vendor_id,
                                        ).exists()

                                        if not existing_modifier_group:
                                            if row["Modifier Group Active"] == "Y":
                                                is_active = True
                                            elif row["Modifier Group Active"] == "N":
                                                is_active = False
                                            
                                            modifier_group_instance = ProductModifierGroup.objects.create(
                                                name = row["Modifier Group Name"],
                                                PLU = row["Modifier Group SKU"],
                                                slug = slugify(str(row["Modifier Group Name"]).lower()),
                                                modifier_group_description = None if pd.isnull(row["Modifier Group Desc"]) or row["Modifier Group Desc"] == "" else row["Modifier Group Desc"],
                                                min = row["Modifier Group Min"],
                                                max = row["Modifier Group Max"],
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
                                            if row["Modifier Active"] == "Y":
                                                is_active = True
                                            elif row["Modifier Active"] == "N":
                                                is_active = False
                                            
                                            modifier_instance = ProductModifier.objects.create(
                                                modifierName = row["Modifier Name"],
                                                modifierPLU = row["Modifier SKU"],
                                                modifierSKU = row["Modifier SKU"],
                                                modifierPrice = row["Modifier Price"],
                                                modifierDesc = None if pd.isnull(row["Modifier Desc"]) or row["Modifier Desc"] == "" else row["Modifier Desc"],
                                                active = is_active,
                                                vendorId = vendor_instance,
                                            )
                                            # Columns with default value: modifierImg, isDeleted, parentId

                                        existing_product_modgroup_joint = ProductAndModifierGroupJoint.objects.filter(
                                            modifierGroup = (ProductModifierGroup.objects.filter(PLU=row["Modifier Group SKU"], vendorId=vendor_id).first()).pk,
                                            product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                                            vendorId = vendor_id
                                        ).exists()

                                        if not existing_product_category_joint:
                                            if row["Modifier Group Active"] == "Y":
                                                is_active = True
                                            elif row["Modifier Group Active"] == "N":
                                                is_active = False
                                            
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
                                    print(f"Error processing row: {row}, Error: {str(e)}")
                            
                            if failed_rows:
                                directory = os.path.join(settings.MEDIA_ROOT, 'Product Details Excel')
                                os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

                                file_name = f"failed_rows_Vendor{vendor_id}.xlsx"

                                relative_file_path = os.path.join('Product Details Excel', file_name)

                                failed_file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                                
                                failed_df = pd.DataFrame(failed_rows)

                                failed_df.to_excel(failed_file_path, index=False)

                                failed_file_path = os.path.join(settings.HOST, f'media/{relative_file_path}')

                        print("Excel file processing completed")
                        
                        if failed_file_path:
                            return 1, failed_file_path
                        else:
                            failed_file_path = None
                            return 1, failed_file_path

                else:
                    print("Sheet name not found")
                    message = "Sheet name should be 'Sheet1'"
                    return 0, message

            else:
                print("File format is not .xlsx")
                message = "File format is not .xlsx"
                return 0, message
        else:
            print("File does not exist")
            message = "File does not exist"
            return 0, message

    else:
        print("Vendor does not exist")
        message = "Vendor does not exist"
        return 0, message


def update_products_through_excel(file_path, sheet_name, vendor_id):
    vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

    if vendor_instance:
        if os.path.exists(file_path):
            if file_path.lower().endswith(".xlsx"):
                data = pd.read_excel(file_path, sheet_name=sheet_name)

                if sheet_name == "Sheet1":
                        failed_rows = []
                        failed_file_path = ''

                        with transaction.atomic():
                            for index, row in data.iterrows():
                                try:
                                    if pd.isnull(row["Category SKU"]) or row["Category SKU"] == "":
                                        row["Error"] = "Category SKU null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Category SKU null or empty")
                                        continue

                                    if pd.isnull(row["Category Name"]) or row["Category Name"] == "":
                                        row["Error"] = "Category Name null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Category Name null or empty")
                                        continue 

                                    if pd.isnull(row["Product SKU"]) or row["Product SKU"] == "":
                                        row["Error"] = "Product SKU null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product SKU null or empty")
                                        continue

                                    if pd.isnull(row["Product Name"]) or row["Product Name"] == "":
                                        row["Error"] = "Product Name null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product Name null or empty")
                                        continue

                                    if pd.isnull(row["Product Active"]) or row["Product Active"] == "":
                                        row["Error"] = "Product Active null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product Active null or empty")
                                        continue

                                    if pd.isnull(row["Regular Price"]) or row["Regular Price"] == "":
                                        row["Error"] = "Regular Price null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Regular Price null or empty")
                                        continue

                                    if pd.isnull(row["Product Images"]) or row["Product Images"] == "":
                                        row["Error"] = "Product Image null or empty"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Product Images null or empty")
                                        continue

                                    if (row["Regular Price"] < 0):
                                        row["Error"] = "Regular Price negative"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Cell value negative")
                                        continue

                                    if ((row["Product Active"] != 'Y') and (row["Product Active"] != 'N')):
                                        row["Error"] = "Product Active not 'Y' or 'N'"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Cell value not 'Y' or 'N'")
                                        continue
                                    
                                    # Using filter() instead of get() because exists only works on filter()
                                    # filter() does not stops the execution of code if value is not found, hence used with first()
                                    existing_category = ProductCategory.objects.filter(categoryPLU = row["Category SKU"], vendorId = vendor_id).exists()

                                    if existing_category:
                                        category_instance = ProductCategory.objects.filter(categoryPLU=row["Category SKU"], vendorId=vendor_id).first()
                                        
                                        category_instance.categoryDescription = None if pd.isnull(row["Category Desc"]) or row["Category Desc"] == "" else row["Category Desc"]
                                        category_instance.categorySlug = slugify(str(row["Category Name"]).lower())

                                        category_instance.save()
                                        
                                    else:
                                        row["Error"] = "Invalid Category SKU"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Invalid Category SKU")
                                        continue
                                    
                                    existing_product = Product.objects.filter(PLU = row["Product SKU"], vendorId=vendor_id).exists()

                                    if existing_product:
                                        if row["Product Active"] == "Y":
                                            is_active = True
                                        elif row["Product Active"] == "N":
                                            is_active = False

                                        product_instance = Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()

                                        product_instance.productName = row["Product Name"]
                                        product_instance.productDesc = None if pd.isnull(row["Product Desc"]) or row["Product Desc"] == "" else row["Product Desc"]
                                        product_instance.productPrice = row["Regular Price"]
                                        product_instance.tag = None if pd.isnull(row["Tags"]) or row["Tags"] == "" else row["Tags"]
                                        product_instance.active = is_active

                                        product_instance.save()

                                    else:
                                        row["Error"] = "Invalid Product SKU"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Invalid Product SKU")
                                        continue
                                        
                                    existing_product_images = ProductImage.objects.filter(
                                        product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                                        url = row["Product Images"],
                                        vendorId = vendor_id,
                                    ).exists()

                                    if not existing_product_images:
                                        existing_product_images = ProductImage.objects.create(
                                            product = Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first(),
                                            url = row["Product Images"],
                                            vendorId = vendor_instance,
                                        )
                                    
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
                                        print(f"Error processing row: {row}, Error: Modifier is without modifier group")
                                        continue

                                    elif ((not(pd.isnull(row["Modifier Group SKU"]))) or row["Modifier Group SKU"] != "") and \
                                    (pd.isnull(row["Modifier SKU"]) or row["Modifier SKU"] == ""):
                                        row["Error"] = "Modifier group has no modifiers"
                                        failed_rows.append(row)
                                        print(f"Error processing row: {row}, Error: Modifier group has no modifiers")
                                        continue

                                    else:
                                        existing_modifier_group = ProductModifierGroup.objects.filter(
                                            PLU = row["Modifier Group SKU"],
                                            vendorId = vendor_id,
                                        ).exists()

                                        if existing_modifier_group:
                                            if row["Modifier Group Active"] == "Y":
                                                is_active = True
                                            elif row["Modifier Group Active"] == "N":
                                                is_active = False
                                            
                                            modifier_group_instance = ProductModifierGroup.objects.filter(
                                                PLU=row["Modifier Group SKU"],
                                                vendorId=vendor_id
                                            ).first()

                                            modifier_group_instance.name = row["Modifier Group Name"]
                                            modifier_group_instance.slug = slugify(str(row["Modifier Group Name"]).lower())
                                            modifier_group_instance.modifier_group_description = None if pd.isnull(row["Modifier Group Desc"]) or row["Modifier Group Desc"] == "" else row["Modifier Group Desc"]
                                            modifier_group_instance.min = row["Modifier Group Min"]
                                            modifier_group_instance.max = row["Modifier Group Max"]
                                            modifier_group_instance.active = is_active

                                            modifier_group_instance.save()

                                        else:
                                            row["Error"] = "Invalid Modifier Group SKU"
                                            failed_rows.append(row)
                                            print(f"Error processing row: {row}, Error: Invalid Modifier Group SKU")
                                            continue
                                            
                                        existing_modifier = ProductModifier.objects.filter(
                                            modifierPLU = row["Modifier SKU"],
                                            vendorId = vendor_id,
                                        ).exists()

                                        if existing_modifier:
                                            if row["Modifier Active"] == "Y":
                                                is_active = True
                                            elif row["Modifier Active"] == "N":
                                                is_active = False
                                            
                                            modifier_instance = ProductModifier.objects.filter(
                                                modifierPLU=row["Modifier SKU"],
                                                vendorId=vendor_id
                                            ).first()
                                            
                                            modifier_instance.modifierName = row["Modifier Name"]
                                            modifier_instance.modifierPrice = row["Modifier Price"]
                                            modifier_instance.modifierDesc = None if pd.isnull(row["Modifier Desc"]) or row["Modifier Desc"] == "" else row["Modifier Desc"],
                                            modifier_instance.active = is_active

                                            modifier_instance.save()
                                        
                                        else:
                                            row["Error"] = "Invalid Modifier SKU"
                                            failed_rows.append(row)
                                            print(f"Error processing row: {row}, Error: Invalid Modifier SKU")
                                            continue

                                        existing_product_modgroup_joint = ProductAndModifierGroupJoint.objects.filter(
                                            modifierGroup = (ProductModifierGroup.objects.filter(PLU=row["Modifier Group SKU"], vendorId=vendor_id).first()).pk,
                                            product = (Product.objects.filter(PLU=row["Product SKU"], vendorId=vendor_id).first()).pk,
                                            vendorId = vendor_id
                                        ).exists()

                                        if not existing_product_category_joint:
                                            if row["Modifier Group Active"] == "Y":
                                                is_active = True
                                            elif row["Modifier Group Active"] == "N":
                                                is_active = False
                                            
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
                                    print(f"Error processing row: {row}, Error: {str(e)}")
                            
                            if failed_rows:
                                directory = os.path.join(settings.MEDIA_ROOT, 'Product Details Excel')
                                os.makedirs(directory, exist_ok=True) # Create the directory if it doesn't exist inside MEDIA_ROOT

                                file_name = f"failed_rows_Vendor{vendor_id}.xlsx"

                                relative_file_path = os.path.join('Product Details Excel', file_name)

                                failed_file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                                
                                failed_df = pd.DataFrame(failed_rows)

                                failed_df.to_excel(failed_file_path, index=False)

                                failed_file_path = os.path.join(settings.HOST, f'media/{relative_file_path}')

                        print("Excel file processing completed")
                        
                        if failed_file_path:
                            return 1, failed_file_path
                        else:
                            failed_file_path = None
                            return 1, failed_file_path

                else:
                    print("Sheet name not found")
                    message = "Sheet name should be 'Sheet1'"
                    return 0, message

            else:
                print("File format is not .xlsx")
                message = "File format is not .xlsx"
                return 0, message
        else:
            print("File does not exist")
            message = "File does not exist"
            return 0, message

    else:
        print("Vendor does not exist")
        message = "Vendor does not exist"
        return 0, message


def process_excel_thread(file_path, sheet_name, vendor_id):
    try:
        thread = threading.Thread(
            target=process_excel, args=(file_path, sheet_name, vendor_id)
        )

        thread.start()
        thread.join()

        print("Excel file thread completed")

    except Exception as e:
        print(f"Error in excel file threading: {str(e)}")


def update_products_through_excel_thread(file_path, sheet_name, vendor_id):
    try:
        thread = threading.Thread(
            target=update_products_through_excel, args=(file_path, sheet_name, vendor_id)
        )

        thread.start()
        thread.join()

        print("Excel file thread completed")

    except Exception as e:
        print(f"Error in excel file threading: {str(e)}")
