from django.db.models.signals import post_save
from django.dispatch import receiver
from koms.models import Order as KOMSOrder
from order.models import Customer, Address
from django.utils import timezone
from core.utils import API_Messages
from core.models import Vendor, Platform
from core.utils import OrderStatus, OrderType
from order.models import Order


def openOrder(data):
        print(data)
        vendorId = data["vendorId"]

        coreResponse = {
            "status": "Error",
            "msg": "Something went wrong"
        }

        try:
            try:
                coreCustomer = Customer.objects.get(VendorId=vendorId, Email=data["customer"]["email"])
                addrs = Address.objects.get(pk=coreCustomer.Billing_Address.pk)
                addrs.address_line1 = data["customer"]["address1"]
                addrs.address_line2 = data["customer"]["address2"]
                addrs.city = data["customer"]["city"]
                addrs.state = data["customer"]["state"]
                addrs.country = data["customer"]["country"]
                addrs.zipcode = data["customer"]["zip"]

                addrs.save()
            except Customer.DoesNotExist:
                addrs = Address(
                    address_line1 = data["customer"]["address1"],
                    address_line2 = data["customer"]["address2"],
                    city = data["customer"]["city"],
                    state = data["customer"]["state"],
                    country = data["customer"]["country"],
                    zipcode = data["customer"]["zip"]
                ).save()

                coreCustomer = Customer(
                    FirstName = data["customer"]["fname"],
                    LastName = data["customer"]["lname"],
                    Email = data["customer"]["email"],
                    Billing_Address = addrs,
                    VendorId = Vendor.objects.get(pk=vendorId))
                
                if data["customer"].get("phno"):
                    coreCustomer.Phone_Number = data["customer"].get("phno")
                coreCustomer = coreCustomer.save()

            data["customer"]["internalId"] = coreCustomer.pk  # +JSON

            vendor = Vendor.objects.get(pk=vendorId)
            
            try:
                orderPoint = Platform.objects.get(VendorId=vendor,className=data.get("className"))
            except Exception as ex:
                print(f"Unexpected {ex=}, {type(ex)=}")
                orderPoint = None

            order = Order(
                Status = OrderStatus.OPEN,
                TotalAmount = 0.0,
                OrderDate = timezone.now(),
                Notes = data.get("note"),
                externalOrderld = data.get("externalOrderId"),
                orderType = OrderType.get_order_type_value(data.get("orderType")) if data.get("orderType") !="DINEIN" else 1,
                arrivalTime = timezone.now(),
                tax = 0.0,
                discount = 0.0,
                tip = 0.0,
                delivery_charge = 0.0,
                subtotal = 0.0,
                customerId = coreCustomer,
                vendorId = vendor,
                platform = orderPoint
            ).save()

            data["internalOrderId"] = order.pk

            order = order.save()

            coreResponse["response"] = order.to_dict()
            coreResponse["status"] = API_Messages.SUCCESSFUL

        except KeyError as kerr:
            print(f"Unexpected {kerr=}, {type(kerr)=}")
            coreResponse["msg"] = "POS service not found for . Please contact system administrator."

        except Exception as err:
            coreResponse["msg"] = f"Unexpected {err=}, {type(err)=}"
            print(f"Unexpected {err=}, {type(err)=}")

        print(coreResponse)
        return coreResponse


@receiver(post_save, sender=KOMSOrder)
def create_core_order(sender, instance, created, data, **kwargs):
    if created:
        openOrder(data)