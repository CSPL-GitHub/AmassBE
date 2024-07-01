from django.urls import path, include
from useradmin import views
from django.views.generic import TemplateView

urlpatterns = [
    # Admin Panel
    path('',views.signin,name="signin"),
    path('logout',views.logout_view,name='logout'),
    path('home/', views.home,name='home'),
    path('vendor/', views.create_vendor, name='vendor'),
    path('vendor/get/', views.get_vendor, name='get_vendor'),
    path('vendor/update/<int:vendor_id>/', views.update_vendor, name='update_vendor'),
    path('vendor/delete/<int:vendor_id>/', views.delete_vendor, name='delete_vendor'),
    path('service/', views.create_service, name='service'),
    path('service/get/', views.get_service, name='get_service'),
    path('service/update/<int:platform_id>/', views.update_service, name='update_service'),
    path('service/delete/<int:platform_id>/', views.delete_service, name='delete_service'),

    # path('ml',views.dfmodule),

    
    # path('ml',views.dfmodule),
    path('custom-admin/dashboard2',TemplateView.as_view(template_name='admin-lte/index2.html'),name='home2'),
    path('custom-admin/dashboard3',TemplateView.as_view(template_name='admin-lte/index3.html'),name='home3'),
    path('calender',TemplateView.as_view(template_name='admin-lte/pages/calendar.html'),name='calender'),

    # gallery
    path('custom-admin/pages/gallery.html',TemplateView.as_view(template_name='admin-lte/pages/gallery.html'),name='gallery'),

    path('custom-admin/pages/widgets.html',TemplateView.as_view(template_name='admin-lte/pages/widgets.html'),name='widgets'),

    path('custom-admin/index3.html',TemplateView.as_view(template_name='admin-lte/index3.html'),name='index3'),
    path('custom-admin/index2.html',TemplateView.as_view(template_name='admin-lte/index2.html'),name='index2'),


    # forms
    path('custom-admin/pages/forms/general.html',TemplateView.as_view(template_name='admin-lte/pages/forms/general.html'),name='general'),
    path('custom-admin/pages/forms/advanced.html',TemplateView.as_view(template_name='admin-lte/pages/forms/advanced.html'),name='advanced'),
    path('custom-admin/pages/forms/editors.html',TemplateView.as_view(template_name='admin-lte/pages/forms/editors.html'),name='editors'),
    path('custom-admin/pages/forms/validation.html',TemplateView.as_view(template_name='admin-lte/pages/forms/validation.html'),name='editors'),


    # chaer

    path('custom-admin/pages/charts/chartjs.html',TemplateView.as_view(template_name='admin-lte/pages/charts/chartjs.html'),name='chaets'),
    path('custom-admin/pages/charts/flot.html',TemplateView.as_view(template_name='admin-lte/pages/charts/flot.html'),name='flot'),
    path('custom-admin/pages/charts/inline.html',TemplateView.as_view(template_name='admin-lte/pages/charts/inline.html'),name='inline'),



# table

    path('custom-admin/pages/tables/simple.html',TemplateView.as_view(template_name='admin-lte/pages/tables/simple.html'),name='simple'),
    path('custom-admin/pages/tables/data.html',TemplateView.as_view(template_name='admin-lte/pages/tables/data.html'),name='data'),
    path('custom-admin/pages/tables/jsgrid.html',TemplateView.as_view(template_name='admin-lte/pages/tables/jsgrid.html'),name='jsgrid'),


    # layout = Layout

    path('custom-admin/pages/layout/top-nav.html',TemplateView.as_view(template_name='admin-lte/pages/layout/top-nav.html'),name='top-nav'),
    path('custom-admin/pages/layout/top-nav-sidebar.html',TemplateView.as_view(template_name='admin-lte/pages/layout/top-nav-sidebar.html'),name='sidebar'),
    path('custom-admin/pages/layout/boxed.html',TemplateView.as_view(template_name='admin-lte/pages/layout/boxed.html'),name='boxed'),
    path('custom-admin/pages/layout/fixed-sidebar.html',TemplateView.as_view(template_name='admin-lte/pages/layout/fixed-sidebar.html'),name='fixed-siderbar'),
    path('custom-admin/pages/layout/fixed-topnav.html',TemplateView.as_view(template_name='admin-lte/pages/layout/fixed-topnav.html'),name='fixed-topnav'),
    path('custom-admin/pages/layout/fixed-footer.html',TemplateView.as_view(template_name='admin-lte/pages/layout/fixed-footer.html'),name='fixed-footer'),
    path('custom-admin/pages/layout/collapsed-sidebar.html',TemplateView.as_view(template_name='admin-lte/pages/layout/collapsed-sidebar.html'),name='sidebar-collapsed'),



    # memail
    path('custom-admin/pages/mailbox/mailbox.html',TemplateView.as_view(template_name='admin-lte/pages/mailbox/mailbox.html'),name='mailbox'),
    path('custom-admin/pages/mailbox/compose.html',TemplateView.as_view(template_name='admin-lte/pages/mailbox/compose.html'),name='compose'),
    path('custom-admin/pages/mailbox/read-mail.html',TemplateView.as_view(template_name='admin-lte/pages/mailbox/read-mail.html'),name='read-mail'), 



# page

    path('custom-admin/pages/examples/invoice.html',TemplateView.as_view(template_name='admin-lte/pages/examples/invoice.html'),name='invoice'), 
    path('custom-admin/pages/examples/e-commerce.html',TemplateView.as_view(template_name='admin-lte/pages/examples/e-commerce.html'),name='e-commerce'), 
    path('custom-admin/pages/examples/profile.html',TemplateView.as_view(template_name='admin-lte/pages/examples/profile.html'),name='profile'), 

    # ui
    path('custom-admin/pages/UI/general.html',TemplateView.as_view(template_name='admin-lte/pages/UI/general.html'),name='genreal'),
    path('custom-admin/pages/UI/icons.html',TemplateView.as_view(template_name='admin-lte/pages/UI/icons.html'),name='icons'),
    path('custom-admin/pages/UI/buttons.html',TemplateView.as_view(template_name='admin-lte/pages/UI/buttons.html'),name='buttons'),
    path('custom-admin/pages/UI/modals.html',TemplateView.as_view(template_name='admin-lte/pages/UI/modals.html'),name='modals'),
    path('custom-admin/pages/UI/navbar.html',TemplateView.as_view(template_name='admin-lte/pages/UI/navbar.html'),name='navbar'),
    path('custom-admin/pages/UI/ribbons.html',TemplateView.as_view(template_name='admin-lte/pages/UI/ribbons.html'),name='ribbons'),
    path('custom-admin/pages/UI/gallery.html',TemplateView.as_view(template_name='admin-lte/pages/UI/gallery.html'),name='gallery'),
    # path('custom-admin/documentation',TemplateView.as_view(template_name='build/html/index.html'),name='Documentation'),
    # path('custom-admin/py-modindex.html',TemplateView.as_view(template_name='build/html/py-modindex.html'),name='Documentation'),
    # path('custom-admin/search.html',TemplateView.as_view(template_name='build/html/search.html'),name='Documentation'),
    # path('custom-admin/documentation',TemplateView.as_view(template_name='build/html/index.html'),name='Documentation'),
    # path('custom-admin/documentation',TemplateView.as_view(template_name='build/html/index.html'),name='Documentation'),

        
    
]
