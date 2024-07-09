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
    sectionSubHeading = models.CharField(max_length=200)
    sectionDescription = models.TextField()
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class SectionTwoCoverImage(models.Model):
    sectionImage = models.URLField(max_length=500,null=True, blank=True)
    sectionText = models.TextField()
    buttonText = models.CharField(max_length=100)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class FeaturesSection(models.Model):
    headingText = models.CharField(max_length=100)
    subHeadingText = models.CharField(max_length=250)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class FeaturesSectionItems(models.Model):
    featureIcon = models.URLField(max_length=500,null=True, blank=True)
    featureHeading = models.CharField(max_length=250)
    featurePara = models.TextField()
    featuresSection = models.ForeignKey(FeaturesSection,on_delete=models.CASCADE)


class TestimonialsSection(models.Model):
    sectionHeading = models.CharField(max_length=100)
    sectionSubHeading = models.CharField(max_length=200)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class TestimonialsSectionItems(models.Model):
    testimonialsImageUrl = models.URLField(max_length=500,null=True, blank=True)
    testimonialsName = models.CharField(max_length=200)
    testimonialsReview = models.TextField()
    testimonialsSection = models.ForeignKey(TestimonialsSection,on_delete=models.CASCADE)


class HomePageOfferSection(models.Model):
    discountTextColor = models.CharField(max_length=100)
    offerDiscountText = models.TextField()
    offerImage = models.URLField(max_length=500,null=True, blank=True)
    offerTitle = models.CharField(max_length=100)
    offerDescription = models.TextField()
    buttonLocation = models.CharField(max_length=100)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)