from django.db import models
from core.models import Platform, Vendor
from core.utils import DiscountCal
from pos.language import master_order_status_name
import string
import secrets


class Customer(models.Model):
    FirstName = models.CharField(max_length=122, null=True, blank=True, default="Guest")
    LastName = models.CharField(max_length=122, null=True, blank=True)
    Email = models.EmailField(null=True, blank=True)
    Phone_Number = models.CharField(max_length=16, default=0)
    loyalty_points_balance = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    VendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('Phone_Number', 'VendorId')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self
    
    def __str__(self):
        return self.FirstName


class Address(models.Model):
    address_line1 = models.CharField(max_length=122)
    address_line2 = models.CharField(max_length=122)
    city = models.CharField(max_length=122)
    state = models.CharField(max_length=122)
    country = models.CharField(max_length=122)
    zipcode = models.CharField(max_length=122)
    type = models.CharField(
        max_length=20,
        choices=(('shipping_address', 'shipping_address'), ('billing_address', 'billing_address')),
        default='shipping_address',
    )
    is_selected = models.BooleanField(default=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self
    
    def __str__(self):
        return self.address_line1


class Order(models.Model):
    Status = models.IntegerField(
    choices = ((1, 'Open'), (2, 'Completed'), (3, 'Canceled'), (4, 'Inprogress'), (5, 'Prepared'),),
        default = 1
    )
    masterOrder = models.ForeignKey("self", null=True, blank=True,on_delete=models.CASCADE)
    TotalAmount = models.FloatField()
    OrderDate = models.DateTimeField(auto_now=False)
    Notes = models.CharField(max_length=122, default='', null=True, blank=True)
    externalOrderId = models.CharField(max_length=122, null=True, blank=True)
    orderType = models.IntegerField(choices = ((1, 'Pickup'), (2, 'Delivery'), (3, 'Dinein')))
    arrivalTime = models.DateTimeField(auto_now=False)
    tax = models.FloatField()
    discount = models.FloatField()
    tip = models.FloatField(default=0.0)
    delivery_charge = models.FloatField()
    subtotal = models.FloatField()
    due = models.FloatField(default=0.0)
    customerId = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def to_dict(self):
        return {
            'orderId': self.pk,
            'status': master_order_status_name[self.Status],
            "externalOrderId": self.externalOrderId
        }
    
    def __str__(self):
        return str(self.pk)


class OriginalOrder(models.Model):
    orderJSON = models.JSONField()
    updateTime = models.DateTimeField(auto_now=True)
    externalOrderId = models.CharField(max_length=122)
    orderId = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True)
    platformName = models.CharField(max_length=122)
    vendorId = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, null=True, blank=True)


class OrderPayment(models.Model):
    orderId = models.ForeignKey(Order, on_delete = models.CASCADE)
    masterPaymentId = models.ForeignKey("self", null = True, blank = True, on_delete = models.CASCADE)
    paymentBy = models.CharField(max_length = 122)
    paymentKey = models.CharField(max_length = 255, null = True, blank = True)
    paid = models.FloatField()
    due = models.FloatField()
    tip = models.FloatField(default = 0.0)
    type = models.IntegerField(choices=((1, "Cash"), (2, "Online"), (3, "Card"), (4, "Split")), default = 1)
    splitType = models.CharField(
        max_length = 50,
        choices = (("by_percent", "by_percent"), ("by_person", "by_person"), ("by_product", "by_product")),
        null = True,
        blank = True,
    )
    status = models.BooleanField(default = False)
    platform = models.CharField(max_length = 122, default = "")


class OrderItem(models.Model):
    productName = models.CharField(max_length=250)
    variantName = models.CharField(max_length=250)
    orderId = models.ForeignKey(Order, on_delete=models.CASCADE)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    plu = models.CharField(max_length=122)
    variantPlu = models.CharField(max_length=122, null=True, blank=True)
    Quantity = models.FloatField()
    price = models.FloatField()
    tax = models.FloatField(null=True, blank=True)
    discount = models.FloatField(null=True, blank=True)
    note= models.CharField(max_length=122)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def to_dict(self):
        return {
            'orderItemId': self.pk,
            'orderId': self.orderId.pk,
            'productName': self.productName,
            'variantName': self.variantName,
            'plu': self.plu,
            'variantPlu': self.variantPlu,
            'quantity': self.Quantity,
            'price': self.price,
            'tax': self.tax,
            'discount': self.discount,
            'note':self.note
        }
    
    def __str__(self):
        return str(self.orderId.pk)


class OrderItemModifier(models.Model):
    orderItemId = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    name = models.CharField(max_length=122)
    plu = models.CharField(max_length=122)
    quantity = models.FloatField()
    price = models.FloatField()
    tax = models.FloatField(null=True, blank=True)
    discount = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def to_dict(self):
        return {
            'orderItemId': self.orderItemId.pk,
            'name': self.name,
            'plu': self.plu,
            'quantity': self.quantity,
            'price': self.price,
            'tax': self.tax,
            'discount': self.discount
        }

class Order_Discount(models.Model):
    discountName = models.CharField(max_length=122)
    discountCode = models.CharField(max_length=122)
    value = models.FloatField()
    start = models.DateField()
    end = models.DateField()
    multiUse = models.BooleanField(default=True)
    calType = models.IntegerField(choices=DiscountCal.choices, default=DiscountCal.AMOUNT)
    is_active = models.BooleanField(default=False)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    

    class Meta:
        unique_together = ("vendorId", "discountCode")

    def save(self, *args, **kwargs):
        if not self.discountCode:
            unique_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            self.discountCode = unique_code

        super().save(*args, **kwargs)
        return self

    def to_dict(self):
        return {
            'id': self.pk,
            'discountCode': self.discountCode,
            'discountName': self.discountName,
            'multiUse':self.multiUse,
            'start':self.start,
            'end':self.end,
            'calType':self.calType,
            'value': self.value,
            # 'plu': self.plu,
        }


class LoyaltyProgramSettings(models.Model):
    is_active = models.BooleanField(default=False)
    amount_spent_in_rupees_to_earn_unit_point = models.PositiveSmallIntegerField(default=10)
    unit_point_value_in_rupees = models.PositiveSmallIntegerField(default=1)
    points_expiry_days = models.PositiveSmallIntegerField(default=30)
    redeem_limit_applied_on = models.CharField(max_length=15, choices=(('subtotal', 'subtotal'), ('final_total', 'final_total')), default="subtotal")
    redeem_limit_in_percentage = models.PositiveSmallIntegerField(default=10)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_id_loyalty_program_settings")


class LoyaltyPointsCreditHistory(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_id_credit_history")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_id_credit_history")
    points_credited = models.PositiveIntegerField(default=0)
    credit_datetime = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField()
    is_expired = models.BooleanField(default=False)
    total_points_redeemed = models.PositiveIntegerField(default=0)
    balance_points = models.PositiveIntegerField(default=0)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_id_credit_history")


class LoyaltyPointsRedeemHistory(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_id_redeem_history")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_id_redeem_history")
    credit_history = models.ForeignKey(LoyaltyPointsCreditHistory, on_delete=models.CASCADE, related_name="credit_history_id")
    points_redeemed = models.PositiveIntegerField(default=0)
    redeem_datetime = models.DateTimeField(auto_now_add=True)
    redeemed_by = models.CharField(max_length=20, choices=(('restaurant_personnal', 'restaurant_personnal'), ('self', 'self')))
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_id_redeem_history")


# class LoyaltyPointsTransactionHistory(models.Model):
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     credit_history = models.ForeignKey(LoyaltyPointsCreditHistory, on_delete=models.CASCADE)
#     redeem_history = models.ForeignKey(LoyaltyPointsRedeemHistory, on_delete=models.CASCADE)
#     points_redeemed = models.IntegerField()
#     points_balance = models.IntegerField()
#     vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class SplitOrderItem(models.Model):
    order_id = models.ForeignKey("order.Order", on_delete=models.CASCADE)
    order_content_id = models.ForeignKey("koms.Order_content", on_delete=models.CASCADE)
    order_content_qty = models.FloatField(default=0)
    def __str__(self):
        return f"({self.order_id.pk}) ({ self.order_content_id.pk})"
    class Meta:
            indexes = [
                models.Index(fields=['order_id',]),
                models.Index(fields=['order_content_id',]),
                models.Index(fields=['order_id','order_content_id']),
    ]