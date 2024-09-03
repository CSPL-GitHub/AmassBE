from django.db import models
from core.models import Vendor
from order.models import Order as MasterOrder
from woms.models import HotelTable



class Station(models.Model):
    station_name = models.CharField(max_length=200)
    station_name_locale = models.CharField(max_length=200, null=True, blank=True)
    client_id = models.CharField(max_length=200, unique=True) #username
    client_secrete = models.CharField(max_length=200) #password
    tag = models.CharField(max_length=20)
    color_code = models.CharField(max_length=10, default=0xFF2E2E48)
    isStation = models.BooleanField(default=True)
    key = models.CharField(max_length=16, unique=True, blank=True, null=True)
    vendorId = models.ForeignKey(Vendor, on_delete = models.CASCADE)
        
    def save(self, *args, **kwargs):
        if not self.station_name_locale:
            self.station_name_locale = self.station_name
        
        super().save(*args, **kwargs)
        
        return self
    
    @property
    def is_authenticated(self):
        return True
    
    def __str__(self):
        return self.station_name


class Order(models.Model):
    master_order = models.ForeignKey(MasterOrder, on_delete=models.CASCADE, related_name="master_order_id")
    externalOrderId = models.PositiveBigIntegerField(unique=True)
    order_status = models.IntegerField()
    order_note = models.CharField(max_length=100, null=True, blank=True)
    order_type = models.IntegerField()
    pickupTime = models.DateTimeField(auto_now=False)
    arrival_time = models.DateTimeField(auto_now=False)
    deliveryIsAsap = models.BooleanField(default=False)
    tableNo = models.CharField(max_length=50, null=True, blank=True)
    guest = models.IntegerField(default=1)
    server = models.CharField(max_length=50, null=True, blank=True)
    isHigh = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(auto_now=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='orderVendor')


class Order_content(models.Model):
    orderId = models.ForeignKey(Order, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    quantity = models.IntegerField()
    quantityStatus = models.IntegerField()
    unit = models.CharField(max_length=20, default="units")
    note = models.TextField(null=True, blank=True)
    SKU = models.CharField(max_length=30)
    tag = models.CharField(max_length=30)
    categoryName = models.CharField(max_length=30)
    stationId = models.ForeignKey(Station, on_delete=models.CASCADE)
    status = models.CharField(max_length=30)
    isrecall = models.BooleanField(default=False)
    isEdited = models.BooleanField(default=False)


class Order_modifer(models.Model):
    contentID = models.ForeignKey(Order_content, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    quantityStatus = models.IntegerField()
    unit = models.CharField(max_length=20)
    note = models.CharField(max_length=50, null=True, blank=True)
    SKU = models.CharField(max_length=30)
    status = models.CharField(max_length=30)
    quantity = models.IntegerField(default=1)
    isEdited = models.BooleanField(default=False)
    group = models.CharField(max_length=50, null=True, blank=True)


class Content_history(models.Model):
    contentID = models.ForeignKey(Order_content, on_delete=models.CASCADE)
    update_time = models.CharField(max_length=30)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=20)


class Modifer_history(models.Model):
    mod_id = models.ForeignKey(Order_modifer, on_delete=models.CASCADE)
    update_time = models.CharField(max_length=30)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=20)


class Order_tables(models.Model):
    orderId = models.ForeignKey(Order, on_delete = models.CASCADE)
    tableId = models.ForeignKey(HotelTable, on_delete = models.CASCADE)


class Staff(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    station_id = models.ForeignKey(Station, on_delete = models.CASCADE, null=True, blank=True)
    vendorId = models.ForeignKey(Vendor, on_delete = models.CASCADE)


class Content_assign(models.Model):
    staffId = models.ForeignKey(Staff, on_delete=models.CASCADE)
    contentID = models.ForeignKey(Order_content, on_delete=models.CASCADE)
