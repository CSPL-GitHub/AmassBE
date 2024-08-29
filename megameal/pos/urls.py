from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter


router = DefaultRouter()

router.register("setting/waiter", views.WaiterViewSet, basename="waiter")
router.register("setting/floor", views.FloorViewSet, basename="floor")
router.register("setting/table", views.HotelTableViewSet, basename="table")
router.register("setting/product_category", views.ProductCategoryViewSet, basename="product_category")
router.register("setting/modifier_group", views.ModifierGroupViewSet, basename="modifier_group")
router.register("setting/discount_coupon", views.DiscountCouponModelViewSet, basename="discount_coupon")
router.register("setting/station", views.StationModelViewSet, basename="station")
router.register("setting/chef", views.ChefModelViewSet, basename="chef")
router.register("setting/banner", views.BannerModelViewSet, basename="banner")
router.register("setting/departments", views.DepartmentModelViewSet, basename="departments")
router.register("setting/working_shift", views.WorkingShiftModelViewSet, basename="working_shift")
router.register("setting/users", views.CoreUserModelViewSet, basename="core_users")


urlpatterns = [
   path('', include(router.urls)),
   path('login/', views.pos_user_login),
   path('permission/', views.get_pos_permissions, name="permission"),
   path('allCategory/',views.allCategory), # All Category api for POS
   path('productByCategory/',views.productByCategory), # all Category product api for POS
   path('productByCategory/<int:id>/',views.productByCategory), # Single Category product api for POS
   path('dashboard/', views.dashboard, name="dashboard"),
   path('dashboard/top_selling_product_details/', views.top_selling_product_details, name="top_selling_product_details"),
   path('dashboard/order_status_type_summary/', views.order_status_type_summary, name="order_status_type_summary"),
   path('modifier_update/', views.modifier_update, name="modifier_update"),
   path('dashboard/excel_download/', views.excel_download_for_dashboard, name="excel_download_for_dashboard"),
   path('table/',views.showtabledetails), # show tables details
   path('tableCapacity/',views.show_tableCapacity), # show products 
   path('productStatusChange/',views.productStatusChange), # activate / deactivate products
   path('createOrder/',views.createOrder), # create new order
   path('platform_list/', views.platform_list, name="platform_list"),
   path('order_details/', views.order_details, name="order_details"),
   path('updatePaymentDetails/', views.updatePaymentDetails, name="updatePaymentDetails"),
   path('splitOrderPayment/', views.splitOrderPayment, name="splitOrderPayment"),
   path('update_order_koms/', views.update_order_koms, name="update_order_koms"),
   path('store_status/', views.update_store_status, name="store_status"),
   path('order_data/', views.get_order_data, name="order_data"),
   path('excel_upload/', views.excel_upload, name="excel_upload"),
   path('excel_delete/', views.delete_excel, name="excel_delete"),
   path('get_store_timings', views.get_store_timings, name='get_store_timings'),
   path('set_store_timings', views.set_store_timings, name='set_store_timings'),
   path('delete_store_timings', views.delete_store_timings, name='delete_store_timings'),
   path('setting/tax/get/', views.get_tax, name='get_tax'),
   path('setting/tax/create/', views.create_tax, name='create_tax'),
   path('setting/tax/update/', views.update_tax, name='update_tax'),
   path('setting/tax/delete/', views.delete_tax, name='delete_tax'),
   path('setting/product/get/', views.get_products, name='get_product'),
   path('setting/product/create/', views.create_product, name='create_product'),
   path('setting/product/update/<int:product_id>/', views.update_product, name='update_product'),
   path('setting/product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
   path('setting/modifier/get/', views.get_modifiers, name='get_modifiers'),
   path('setting/modifier/create/', views.create_modifier, name='create_modifier'),
   path('setting/modifier/update/<int:modifier_id>/', views.update_modifier, name='update_modifier'),
   path('setting/modifier/delete/<int:modifier_id>/', views.delete_modifier, name='delete_modifier'),
   path('setting/customer/get/', views.get_customers, name='get_customer'),
   path('setting/customer/create/', views.create_customer, name='create_customer'),
   path('setting/customer/update/', views.update_customer, name='update_customer'),
   path('setting/customer/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),
   path('setting/customer/orders/get/', views.get_orders_of_customer, name='orders_of_customer'),
   path('setting/customer/loyalty_points_history/get/', views.get_loyalty_point_transactions_of_customer, name='orders_of_customer'),
   path('setting/loyaltyprogramsettings/get/', views.get_loyalty_points_settings, name='get_loyalty_program_settings'),
   path('setting/loyaltyprogramsettings/create/', views.create_loyalty_points_settings, name='create_loyalty_program_settings'),
   path('setting/loyaltyprogramsettings/update/', views.update_loyalty_points_settings, name='update_loyalty_program_settings'),
   path('setting/delivery/get/', views.get_delivery_settings, name='get_delivery_charge'),
   path('setting/delivery/update/', views.update_delivery_settings, name='update_delivery_charge'),
   path('setting/product_excel_upload/', views.product_excel_upload_for_pos, name='product_excel_upload_for_pos'),
   path('setting/product_excel_template_download/', views.download_product_excel_upload_template, name='download_product_excel_upload_template'),
   path('setting/product_data_excel_download/', views.download_product_data_excel, name='download_product_data_excel'),
   path('setting/register_cash/', views.register_cash, name='register_cash'),
   path('setting/cash_register_history/', views.get_cash_register_history, name='cash_register_history'),
   path('setting/user_category/get/', views.get_core_user_categories, name='get_core_user_categories'),
   path('setting/user_category/create/', views.create_core_user_category, name='create_core_user_category'),
   path('setting/user_category/update/', views.update_core_user_category, name='update_core_user_category'),
   path('setting/user_category/delete/', views.delete_core_user_category, name='delete_core_user_category'),
   path('redeem_loyalty_points/', views.redeem_loyalty_points, name='redeem_loyalty_points'),
   path('reports/top_selling_products/', views.top_selling_products_report, name='top_selling_products_report'),
   path('reports/most_repeating_customers/', views.most_repeating_customers_report, name='most_repeating_customers_report'),
   path('reports/customers_redeemed_most_points/', views.customers_redeemed_most_points_report, name='customers_redeemed_most_points_report'),
   path('reports/finance/', views.finance_report, name='finance_report'),
   path('reports/footfall_revenue/', views.footfall_revenue_report, name='footfall_revenue_report'),
   path('reports/order/', views.order_report, name='order_report'),
   path('reports/cancel_order/', views.cancel_order_report, name='cancel_order_report'),
   path('reports/pincode/', views.pincode_report, name='pincode_report'),
   path('is_platform/', views.is_platform, name='is_platform'),
   path('translate_excel/', views.generate_language_translation_excel, name='translate_excel'),
]



