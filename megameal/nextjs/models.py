from django.db import models
from core.models import Vendor
from order.models import Customer
from uuid import uuid4


class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to="user_profile", max_length=1000, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    token = models.UUIDField(default=uuid4, editable=False, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    Customer = models.ForeignKey(Customer, on_delete=models.CASCADE)


class AboutUsSection(models.Model):
    sectionImage = models.URLField(max_length=500,null=True, blank=True)
    sectionHeading = models.CharField(max_length=200)
    sectionHeading_locale = models.CharField(max_length=200,null=True, blank=True)
    sectionSubHeading = models.CharField(max_length=200)
    sectionSubHeading_locale = models.CharField(max_length=200,null=True, blank=True)
    sectionDescription = models.TextField()
    sectionDescription_locale = models.TextField(null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if not self.sectionHeading_locale:
            self.sectionHeading_locale = self.sectionHeading
        if not self.sectionSubHeading_locale:
            self.sectionSubHeading_locale = self.sectionSubHeading
        if not self.sectionDescription_locale:
            self.sectionDescription_locale = self.sectionDescription
        super().save(*args, **kwargs)
        return self
    

class SectionTwoCoverImage(models.Model):
    sectionImage = models.URLField(max_length=500,null=True, blank=True)
    sectionText = models.TextField()
    sectionText_locale = models.TextField(null=True, blank=True)
    buttonText = models.CharField(max_length=100)
    buttonText_locale = models.CharField(max_length=100,null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if not self.sectionText_locale:
            self.sectionText_locale = self.sectionText
        if not self.buttonText_locale:
            self.buttonText_locale = self.buttonText
        super().save(*args, **kwargs)
        return self
    

class FeaturesSection(models.Model):
    headingText = models.CharField(max_length=100)
    headingText_locale = models.CharField(max_length=100,null=True, blank=True)
    subHeadingText = models.CharField(max_length=250)
    subHeadingText_locale = models.CharField(max_length=250,null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    

class FeaturesSectionItems(models.Model):
    featureIcon = models.URLField(max_length=500,null=True, blank=True)
    featureHeading = models.CharField(max_length=250)
    featureHeading_locale = models.CharField(max_length=250,null=True, blank=True)
    featurePara = models.TextField()
    featurePara_locale = models.TextField(null=True, blank=True)
    featuresSection = models.ForeignKey(FeaturesSection,on_delete=models.CASCADE)


class TestimonialsSection(models.Model):
    sectionHeading = models.CharField(max_length=100)
    sectionHeading_locale = models.CharField(max_length=100,null=True, blank=True)
    sectionSubHeading = models.CharField(max_length=200)
    sectionSubHeading_locale = models.CharField(max_length=200,null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class TestimonialsSectionItems(models.Model):
    testimonialsImageUrl = models.URLField(max_length=500,null=True, blank=True)
    testimonialsName = models.CharField(max_length=200)
    testimonialsName_locale = models.CharField(max_length=200,null=True, blank=True)
    testimonialsReview = models.TextField()
    testimonialsReview_locale = models.TextField(null=True, blank=True)
    testimonialsSection = models.ForeignKey(TestimonialsSection,on_delete=models.CASCADE)


class HomePageOfferSection(models.Model):
    discountTextColor = models.CharField(max_length=100)
    discountTextColor_locale = models.CharField(max_length=100,null=True, blank=True)
    offerDiscountText = models.TextField()
    offerDiscountText_locale = models.TextField(null=True, blank=True)
    offerImage = models.URLField(max_length=500,null=True, blank=True)
    offerTitle = models.CharField(max_length=100)
    offerTitle_locale = models.CharField(max_length=100,null=True, blank=True)
    offerDescription = models.TextField()
    offerDescription_locale = models.TextField(null=True, blank=True)
    buttonLocation = models.CharField(max_length=100)
    buttonLocation_locale = models.CharField(max_length=100,null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)