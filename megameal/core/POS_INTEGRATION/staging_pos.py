from core.models import Platform, ProductModifier, Product, Tax, Vendor
from order.models import Address, Customer, Order, Order_Discount, OrderItem, OrderItemModifier, OrderPayment
from core.utils import (
    API_Messages, DiscountCal, OrderType, TaxLevel, send_order_confirmation_email,
)
from core.models import EmailLog
from pos.language import master_order_status_number
from megameal.settings import EMAIL_HOST_USER
from django.template.loader import render_to_string
from django.utils import timezone
from logging import log
import socket



class StagingIntegration():
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
                coreCustomer = Customer.objects.filter(Phone_Number=data["customer"]["phno"], VendorId=vendorId).first()
                
                customer_address = data["customer"]

                if (data["platform"] == "Website") or (data["platform"] == "Mobile App"):
                    if not coreCustomer:
                        coreCustomer = Customer.objects.create(
                            FirstName = data["customer"]["fname"],
                            LastName = data["customer"]["lname"],
                            Email = data["customer"]["email"],
                            Phone_Number = data["customer"]["phno"],
                            VendorId = vendor_instance
                        )

                        addrs = Address.objects.create(
                            address_line1 = customer_address["address1"],
                            address_line2 = customer_address["address2"],
                            city = customer_address["city"],
                            state = customer_address["state"],
                            country = customer_address["country"],
                            zipcode = customer_address["zip"],
                            type = "shipping_address",
                            is_selected = True,
                            customer = coreCustomer
                        )

                    else:
                        addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first()

                        if not addrs:
                            addrs = Address.objects.create(
                            address_line1 = customer_address["address1"],
                            address_line2 = customer_address["address2"],
                            city = customer_address["city"],
                            state = customer_address["state"],
                            country = customer_address["country"],
                            zipcode = customer_address["zip"],
                            type = "shipping_address",
                            is_selected = True,
                            customer = coreCustomer
                        )
                
                else:
                    if coreCustomer and ((coreCustomer.Phone_Number != '0') or (coreCustomer.FirstName != 'Guest')):
                        addrs = Address.objects.filter(customer=coreCustomer.pk, type="shipping_address", is_selected=True).first()

                        if not addrs:
                            addrs = Address.objects.create(
                                address_line1 = customer_address["address1"],
                                address_line2 = customer_address["address2"],
                                city = customer_address["city"],
                                state = customer_address["state"],
                                country = customer_address["country"],
                                zipcode = customer_address["zip"],
                                type = "shipping_address",
                                is_selected = True,
                                customer = coreCustomer
                            )
                
            except Exception as e:
                print(e)
            
            data["customer"]["internalId"] = coreCustomer.pk

            ##++++++Order Platform
            try:
                platform_instance = Platform.objects.get(Name=data.get("platform"), VendorId=vendorId)
            
            except Exception as ex:
                print(f"Unexpected {ex=}, {type(ex)=}")
                platform_instance = None
            
            ##++++++End Order Platform
            discount=0.0
            if data.get("discount"):
                if data.get("discount").get('value'):
                    discount=data.get("discount").get('value')
            order = Order(
                Status = master_order_status_number["Open"],
                TotalAmount = 0.0,
                OrderDate = timezone.now(),
                Notes = data.get("note"),
                externalOrderId = data.get("externalOrderId"),
                orderType = OrderType.get_order_type_value(data.get("orderType")),
                arrivalTime = timezone.now(),
                tax = 0.0,
                discount = discount,
                tip = 0.0,
                delivery_charge = 0.0,
                subtotal = 0.0,
                customerId = coreCustomer,
                vendorId = vendor_instance,
                platform = platform_instance
            ).save()
            request["internalOrderId"] = order.pk
            request["master_id"] = order.pk
            # +++++++

            # ++++++ Discounts
            if data.get("discount"):
                try:
                    discount = Order_Discount.objects.get(vendorId=vendorId, discountCode=data["discount"].get("discountCode"))
                    
                    data["discount"] = discount.to_dict()

                except Order_Discount.DoesNotExist:
                    print("Invalid Discount")
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
                taxes = Tax.objects.filter(enabled=True, vendorId=vendorId)

                if taxes.exists():
                    tax = order.tax+productTaxes

            order.tax = tax
            order.subtotal = subtotal
            order.discount = discount
            order.tip = data["tip"]
            data["subtotal"] = subtotal
            order.TotalAmount=(order.subtotal - order.discount + order.tax + order.delivery_charge)

            if order.platform.Name == "Mobile App" or order.platform.Name == "Website":
                order.TotalAmount = data["payment"]["payAmount"]
                order.delivery_charge = data["payment"]["shipping_total"]
                order.tax = data["payment"]["total_tax"]

            # +++++ Add order Taxes
            try:
                data["orderLevelTax"] = []

                orderTaxes = Tax.objects.filter(
                    vendorId=vendorId, isDeleted=False, taxLevel=TaxLevel.ORDER, enabled=True
                )

                if orderTaxes:
                    for orderTax in orderTaxes:
                        data["orderLevelTax"].append(orderTax.to_dict())

            except Tax.DoesNotExist:
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
                    type=data["payment"].get('mode', "Cash"),
                    platform=data["payment"].get('platform', "")
                ).save()
            # ++++++++++++

            if ((coreCustomer.Phone_Number != '0') or (coreCustomer.FirstName != 'Guest')) and \
            ((order.platform.Name == 'Website') or (order.platform.Name == 'Mobile App')):
                tax_details = []
                
                taxes = Tax.objects.filter(enabled=True, vendorId=vendorId)

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

                # local_ips = []

                # host_name = socket.gethostname()

                # host_ip_info = socket.gethostbyname_ex(host_name)

                # for ip in host_ip_info[2]:
                #     if not ip.startswith("127."):
                #         local_ips.append(ip)

                # external_ip = None

                # external_ip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                # port = request.META.get("SERVER_PORT")

                # try:
                #     external_ip_socket.connect(('8.8.8.8', 53))

                #     external_ip = external_ip_socket.getsockname()[0]

                # finally:
                #     external_ip_socket.close()

                # if local_ips:
                #     server_ip = local_ips[0]

                # else:
                #     server_ip = external_ip
                
                sender = EMAIL_HOST_USER
                receiver = coreCustomer.Email

                subject = "Your order is confirmed"
                email_body_type = "html"
                
                context = {
                    "order_id": order.pk,
                    "order_type": data.get("orderType"),
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
                    "logo_url": f"{vendor_instance.logo.url}" if vendor_instance.logo else "",
                    "currency": vendor_instance.currency_symbol,
                }
                
                email_body = render_to_string('email.html', context)
                
                email_status = send_order_confirmation_email(sender, receiver, subject, email_body_type, email_body)

                email_log = EmailLog(
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
            coreResponse["msg"] = f"Unexpected {kerr=}, {type(kerr)=}"

        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"

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
                taxForProduct = Tax.objects.filter(
                    vendorId = vendor,
                    isDeleted = False,
                    enabled = True,
                    taxLevel = TaxLevel.ORDER
                )

                appliedTaxes.extend(list(taxForProduct))

            except Tax.DoesNotExist:
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
    