from django.db import models
import secrets
from core.models import Vendor
from order.models import Order as MasterOrder
from woms.models import Hotal_Tables


# All KOMS model here.

class Order_point(models.Model):
    name = models.CharField(max_length=50)
    activation_status = models.BooleanField(default=False)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)


class Order_point_cred(models.Model):
    pointId = models.ForeignKey(Order_point, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=500)
    


class Stations(models.Model):
    station_name = models.CharField(max_length=50)
    client_id = models.CharField(max_length=200, unique=True) #username
    client_secrete = models.CharField(max_length=200) #password
    tag = models.CharField(max_length=20)
    color_code = models.CharField(max_length=10, default=0xFF2E2E48)
    isStation = models.BooleanField(default=True)
    key = models.CharField(max_length=16, unique=True, blank=True, null=True)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)
        
    @property
    def is_authenticated(self):
        return True
    
    def __str__(self):
        return self.station_name


class Order(models.Model):
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE,related_name='orderVendor')
    externalOrderId = models.IntegerField(unique=True)
    pickupTime = models.DateTimeField(auto_now=False)
    deliveryIsAsap = models.BooleanField(default=False)
    # order_point = models.ForeignKey(Order_point, on_delete=models.CASCADE)
    arrival_time = models.DateTimeField(auto_now=False)
    estimated_time = models.DateTimeField(auto_now=False, null=True)
    externalOrderStatus = models.CharField(max_length=100, blank=True, null=True)
    order_status = models.IntegerField()
    order_note = models.CharField(max_length=100,null=True,blank=True)
    order_type = models.IntegerField()
    guest = models.IntegerField(default=1)
    server = models.CharField(max_length=50,null=True,blank=True)
    tableNo = models.CharField(max_length=50,null=True,blank=True)
    isHigh=models.BooleanField(default=False)
    master_order = models.ForeignKey(MasterOrder, on_delete= models.CASCADE, related_name="master_order_id")


class Original_order(models.Model):
    orderId = models.ForeignKey(Order, on_delete=models.CASCADE)
    OrderJSON = models.CharField(max_length=1000)
    update_time = models.CharField(max_length=20)
    externalOrderId = models.CharField(max_length=30)
    parent = models.CharField(max_length=30)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)


class Order_content(models.Model):
    orderId = models.ForeignKey(Order, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    quantity = models.IntegerField()
    quantityStatus = models.IntegerField()
    unit = models.CharField(max_length=20)
    note = models.TextField(null=True,blank=True)
    SKU = models.CharField(max_length=30)
    tag = models.CharField(max_length=30)
    categoryName = models.CharField(max_length=30)
    stationId = models.ForeignKey(Stations, on_delete=models.CASCADE)
    status = models.CharField(max_length=30)
    isrecall=models.BooleanField(default=False)
    isEdited=models.BooleanField(default=False)

class Order_modifer(models.Model):
    contentID = models.ForeignKey(Order_content, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    quantityStatus = models.IntegerField()
    unit = models.CharField(max_length=20)
    note = models.CharField(max_length=50, null=True, blank=True)
    SKU = models.CharField(max_length=30)
    status = models.CharField(max_length=30)
    quantity=models.IntegerField(default=1)
    isEdited=models.BooleanField(default=False)
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
    orderId=models.ForeignKey(Order,on_delete=models.CASCADE)
    tableId=models.ForeignKey(Hotal_Tables,on_delete=models.CASCADE)

class KOMS_config(models.Model):
    print_or_display = models.IntegerField()
    default_prepration_time = models.CharField(max_length=20)
    licence_key = models.CharField(max_length=200)
    activation_status = models.IntegerField()
    central_url = models.CharField(max_length=30)
    send_order_to_cs = models.BooleanField()
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)


class Prepration_time(models.Model):
    externalID = models.CharField(max_length=20)
    tag = models.CharField(max_length=50)
    prepration_time = models.CharField(max_length=100)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

class Staff(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    station_id = models.ForeignKey(Stations, on_delete=models.CASCADE, null=True, blank=True)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

class Content_assign(models.Model):
    staffId = models.ForeignKey(Staff, on_delete=models.CASCADE)
    contentID = models.ForeignKey(Order_content, on_delete=models.CASCADE)


class UserSettings(models.Model):
    notification = models.BooleanField(default=True)
    cooking = models.CharField(max_length=100, default=0xFF2E2E48)
    incoming = models.CharField(max_length=100, default=0xFF2E2E48)
    dragged = models.CharField(max_length=100, default=0xFF2E2E48)
    complete = models.CharField(max_length=100, default=0xFF2E2E48)
    cancel = models.CharField(max_length=100, default=0xFF2E2E48)
    recall = models.CharField(max_length=100, default=0xFF2E2E48)
    priority = models.CharField(max_length=100, default=0xFF2E2E48)
    nearTo = models.CharField(max_length=100, default=0xFF2E2E48)
    stationId = models.ForeignKey(Stations, on_delete=models.CASCADE, default=1, unique=True)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

class OrderStatusName(models.Model):
    orderName = models.CharField(max_length=50)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

class OrderHistory(models.Model):
    order_id=models.ForeignKey(Order,on_delete=models.CASCADE)
    order_status=models.ForeignKey(OrderStatusName,on_delete=models.CASCADE)
    timestamp=models.DateTimeField(auto_now=False)
    delay=models.IntegerField()
    recall=models.IntegerField()
    staff_id=models.ForeignKey(Staff,on_delete=models.CASCADE,default=1)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

class Message_type(models.Model):
    massage_type=models.CharField(max_length=50)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

class massage_history(models.Model):
    massage_type=models.ForeignKey(Message_type, on_delete=models.CASCADE,default=3)
    order_id=models.ForeignKey(Order, on_delete=models.CASCADE)
    recallno=models.IntegerField()
    status=models.ForeignKey(OrderStatusName, on_delete=models.CASCADE)
    staffid=models.ForeignKey(Staff, on_delete=models.CASCADE,null=True)
    mgs=models.TextField()
    isdelayed=models.BooleanField(default=False)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)
    