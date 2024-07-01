from django.contrib import admin
from .models import *


admin.site.register(Order_Discount)
admin.site.register(Order)
admin.site.register(LoyaltyProgramSettings)
admin.site.register(LoyaltyPointsCreditHistory)
admin.site.register(LoyaltyPointsRedeemHistory)
admin.site.register(Customer)
admin.site.register(Address)