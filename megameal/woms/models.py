from django.db import models
from core.models import Vendor
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError


class Floor(models.Model):
    name = models.CharField(max_length=50)
    name_locale = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.name_locale:
            self.name_locale = self.name
        
        super().save(*args, **kwargs)
        
        return self
    
    def __str__(self):
        return self.name


class Waiter(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    token = models.TextField(max_length=100, null=True, blank=True, default='')
    name = models.CharField(max_length=200)
    name_locale = models.CharField(max_length=200, null=True, blank=True)
    phone_number = models.PositiveBigIntegerField()
    email = models.CharField(max_length=100, null=True, blank=True)
    image = models.ImageField(max_length=100, null=True, blank=True, upload_to="waiter")
    is_waiter_head = models.BooleanField(default=False) 
    is_active = models.BooleanField(default=False)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.name_locale:
            self.name_locale = self.name
        
        super().save(*args, **kwargs)
        
        return self
    
    def __str__(self):
        return self.name


class HotelTable(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE)
    tableNumber = models.IntegerField(null=True, blank=True)
    tableCapacity = models.IntegerField(null=True, blank=True)
    guestCount = models.IntegerField(null=True, blank=True, default=0)
    status = models.IntegerField(max_length=30, default=1, choices=(
        (1, 'Empty'), (2, 'Booked'), (3, 'Occupied'),
        (4, 'Cleaning'), (5, 'Out of service')
    ))
    waiterId = models.ForeignKey(Waiter, null=True, blank=True, on_delete=models.SET_NULL)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["floor", "tableNumber", "vendorId"]

    def __str__(self):
        return str(self.tableNumber)


class Token_date(models.Model):
       Date=models.DateTimeField()
       Token=models.IntegerField(max_length=200,)
       vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)


@receiver(pre_save, sender=HotelTable)
def validate_hotel_table(sender, instance, **kwargs):
    if instance.floor.vendorId != instance.vendorId:
        raise ValidationError('The vendor IDs of the Floor and Hotel_Table are not matching.')
    

@receiver(post_save, sender=Floor)
def update_hotel_table_status(sender, instance, **kwargs):
    tables = HotelTable.objects.filter(floor=instance)

    if instance.is_active == False:
        tables.update(status=5)
    else:
        tables.update(status=1)


# @receiver(pre_save, sender=HotelTable)
# def update_waiter_id(sender, instance, **kwargs):
#     if instance.pk is not None:
#         old_instance = HotelTable.objects.get(pk=instance.pk)

#         if old_instance.status != instance.status and instance.status != 3:
#             instance.waiterId = None
