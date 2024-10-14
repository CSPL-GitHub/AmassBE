from django.urls import path
from inventory import views


urlpatterns = [
    path("sync/all/", views.sync_all, name="sync_all"),
    path("sync/modifier_group/", views.modifier_group_sync, name="modifier_group_sync"),
    path("sync/modifier/", views.modifier_sync, name="modifier_sync"),
    path("sync/category/", views.category_sync, name="category_sync"),
    path("sync/product/", views.product_sync, name="product_sync"),
    path("product_status_toggle/", views.product_status_toggle, name="product_status_toggle"),
    path("modifier_status_toggle/", views.modifier_status_toggle, name="modifier_status_toggle"),
    path("disabled_items/", views.disabled_items, name="disabled_items"),
]
