from django.contrib import admin
from nextjs.models import *


admin.site.register(User)

@admin.register(AboutUsSection)
class AboutUsSectionAdmin(admin.ModelAdmin):
    
    list_display = ('sectionHeading','sectionSubHeading','vendor',)
    list_filter = ('vendor',)
    # search_fields = ('name','username')
    # show_facets = admin.ShowFacets.ALWAYS
    
@admin.register(SectionTwoCoverImage)
class SectionTwoCoverImageAdmin(admin.ModelAdmin):
    
    list_display = ('sectionText','vendor',)
    list_filter = ('vendor',)
    
    
@admin.register(FeaturesSection)
class FeaturesSectionAdmin(admin.ModelAdmin):
    
    list_display = ('headingText','vendor',)
    list_filter = ('vendor',)
    
@admin.register(FeaturesSectionItems)
class FeaturesSectionItemsAdmin(admin.ModelAdmin):
    
    list_display = ('featuresSection','featureHeading',)


@admin.register(TestimonialsSection)
class TestimonialsSectionAdmin(admin.ModelAdmin):
    list_display = ('sectionHeading','sectionSubHeading','vendor',)
    
@admin.register(TestimonialsSectionItems)
class TestimonialsSectionItemsAdmin(admin.ModelAdmin):
    list_display = ('testimonialsSection','testimonialsName','testimonialsReview',)



@admin.register(HomePageOfferSection)
class HomePageOfferSectionAdmin(admin.ModelAdmin):
    list_display = ('vendor','offerTitle','discountTextColor',)