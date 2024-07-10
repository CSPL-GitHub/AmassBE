from django.shortcuts import render, redirect
from django.contrib.auth import logout
from .models import *
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login
from core.models import Vendor, Platform, VendorType
from useradmin.forms import ServiceForm, VendorForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.utils import CorePlatform, OrderAction
from django.core.paginator import Paginator


def signin(request):
    # if request.method=="POST":
    #     name = request.POST.get('username')
    #     password = request.POST.get('password')
    #     try:
    #         result = VendorLog.objects.get(Q(password=password)&(Q(userName=name)|Q(email=name)))
    #         if result:
    #             request.session['user_id'] = result.pk
    #             return redirect(home)
    #         else:
    #             messages.warning(request,'user doesnt exist!')
    #             return render(request,"signin.html")
    #     except:
    #         messages.warning(request,'user doesnt exist!')
    #         return render(request,"signin.html")
    # return render(request,'signin.html')

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            user_obj = User.objects.get(username=username)
            if user_obj.is_superuser == True:
                login(request, user)
                request.session["user_id"] = user_obj.pk
                messages.success(request, "Login successful!")
                return redirect(home)
            else:
                messages.error(request, "Access denied!")
                return render(request, "useradmin/login.html")
        else:
            messages.error(request, "User not registered!")
            return render(request, "useradmin/login.html")
    else:
        return render(request, "useradmin/login.html")


def logout_view(request):
    logout(request)
    # del request.session['user_id']
    return redirect(signin)


def home(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect(signin)
    moduleList = []
    for user in VendorLog.objects.filter(id=user_id):
        for singleModule in user.module.all():
            moduleList.append(singleModule.pk)
        for group in user.groups.all():
            for groupModule in group.group_modules.all():
                moduleList.append(groupModule.pk)
                # print(moduleList)
    # print(moduleList)
    return render(request, "admin-lte/index.html", {"moduleList": moduleList})


def get_vendor(request):
    page = int(request.GET.get('pageIndex', 1)) # pageIndex variable should not be renamed as it is required for jsGrid plugin
    page_size = int(request.GET.get('pageSize', 10)) # pageSize variable should not be renamed as it is required for jsGrid plugin

    vendors = Vendor.objects.all().order_by('pk')

    paginated_data = []
    
    paginator = Paginator(vendors, page_size)
    page = paginator.get_page(page)

    for data in page:
        paginated_data.append({
            "id": data.pk,
            "Name": data.Name,
            "Email": data.Email,
            "vendor_type": data.vendor_type.pk if data.vendor_type else 0,
            "phone_number": data.phone_number,
            "gst_number": data.gst_number,
            "address_line_1": data.address_line_1,
            "address_line_2": data.address_line_2,
            "city": data.city,
            "state": data.state,
            "country": data.country,
            "contact_person_name": data.contact_person_name,
            "contact_person_phone_number": data.contact_person_phone_number,
            "is_active": data.is_active
        })

    return JsonResponse({
        "data": paginated_data, # data key should not be renamed as it is required for jsGrid plugin
        "itemsCount": paginator.count # itemsCount key should not be renamed as it is required for jsGrid plugin
    })

def create_vendor(request):
    vendor_types = VendorType.objects.all()

    if request.method == "POST":
        form = VendorForm(request.POST or None)

        if form.is_valid():
            form.save()

            messages.success(request, "Vendor Created!")

            return redirect("/vendor/")
        else:
            messages.warning(request, "Please fill all the fields!")

            form = VendorForm()

            return render(
                request, "adminlte/vendor.html", {"form": form, "vendor_types":vendor_types}
            )

    form = VendorForm(None)

    return render(request, "adminlte/vendor.html", {"form": form, "vendor_types":vendor_types})


def update_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)

    if request.method == "POST":
        form = VendorForm(request.POST, instance=vendor)

        if form.is_valid():
            vendor.save()

            serialized_data = {}

            serialized_data["id"] = vendor.pk
            serialized_data["Name"] = vendor.Name
            serialized_data["Email"] = vendor.Email
            serialized_data["vendor_type"] = vendor.vendor_type.pk
            serialized_data["phone_number"] = vendor.phone_number
            serialized_data["gst_number"] = vendor.gst_number
            serialized_data["address_line_1"] = vendor.address_line_1
            serialized_data["address_line_2"] = vendor.address_line_2
            serialized_data["city"] = vendor.city
            serialized_data["state"] = vendor.state
            serialized_data["country"] = vendor.country
            serialized_data["contact_person_name"] = vendor.contact_person_name
            serialized_data["contact_person_phone_number"] = vendor.contact_person_phone_number
            serialized_data["is_active"] = vendor.is_active

            messages.success(request, "Vendor updated successfully")
            return JsonResponse(serialized_data, content_type="application/json", safe=False)
        
        else:
            print(form.errors)
            messages.error(request, "Please fill the details correctly!")

            return JsonResponse({'error': 'Please fill the details correctly'}, status=400, content_type="application/json")

    else:
        messages.error(request, "Invalid request method!")

        return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")


def delete_vendor(request, vendor_id):
    try:
        if request.method == "POST":
            vendor = Vendor.objects.filter(pk=vendor_id)

            vendor.delete()

            return JsonResponse({"message": "User deleted successfully"}, content_type="application/json", status=204)

        else:
            messages.error(request, "Invalid request method!")
            return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")
    except Exception as e:
        print(e)
        return JsonResponse({"message": "Something went wrong!"}, content_type="application/json")


def get_service(request):
    page = int(request.GET.get('pageIndex', 1)) # pageIndex variable should not be renamed as it is required for jsGrid plugin
    page_size = int(request.GET.get('pageSize', 10)) # pageSize variable should not be renamed as it is required for jsGrid plugin

    services = Platform.objects.all().order_by('pk')

    paginated_data = []
    
    paginator = Paginator(services, page_size)
    page = paginator.get_page(page)

    for data in page:
        paginated_data.append({
            "id": data.pk,
            "Name": data.Name,
            "baseUrl": data.baseUrl,
            "secreateKey": data.secreateKey,
            "secreatePass": data.secreatePass,
            "VendorId": data.VendorId.pk,
            "isActive": data.isActive,
            "expiryDate": data.expiryDate,
            "orderActionType": data.orderActionType,
        })

    return JsonResponse({
        "data": paginated_data, # data key should not be renamed as it is required for jsGrid plugin
        "itemsCount": paginator.count # itemsCount key should not be renamed as it is required for jsGrid plugin
    })


def create_service(request):
    platform_choices = []
    core_platform_choices = list(CorePlatform)

    for core_platform_type in core_platform_choices:
        key = core_platform_type
        platform_choices.append((key.name, key.value))

    order_choices = []
    order_action_choices = list(OrderAction)

    for order_action_choice in order_action_choices:
        key = order_action_choice
        order_choices.append((key.name, key.value))

    vendors = Vendor.objects.all()

    if request.method == "POST":
        form = ServiceForm(request.POST or None)

        if form.is_valid():
            form.save()

            messages.success(request, "Service Created!")

            return redirect("/service/")
        else:
            messages.warning(request, "Please fill all the fields!")

            form = ServiceForm()

            return render(
                request, "adminlte/services.html", {"form": form, "vendors": vendors, "platform_choices": platform_choices}
            )

    form = ServiceForm(None)

    return render(request, "adminlte/services.html", {"form": form, "vendors": vendors, "platform_choices": platform_choices, "order_choices": order_choices})


def update_service(request, platform_id):
    service = get_object_or_404(Platform, pk=platform_id)

    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)

        if form.is_valid():
            service.save()

            serialized_data = {}

            serialized_data["id"] = service.pk
            serialized_data["Name"] = service.Name
            serialized_data["baseUrl"] = service.baseUrl
            serialized_data["secreateKey"] = service.secreateKey
            serialized_data["secreatePass"] = service.secreatePass
            serialized_data["VendorId"] = service.VendorId.pk
            serialized_data["isActive"] = service.isActive
            serialized_data["expiryDate"] = service.expiryDate
            serialized_data["orderActionType"] = service.orderActionType

            messages.success(request, "Service updated successfully")
            return JsonResponse(serialized_data, content_type="application/json", safe=False)
        
        else:
            print(form.errors)
            messages.error(request, "Please fill the details correctly!")

            return JsonResponse({'error': 'Please fill the details correctly'}, status=400, content_type="application/json")

    else:
        messages.error(request, "Invalid request method!")

        return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")


def delete_service(request, platform_id):
    try:
        if request.method == "POST":
            service = Platform.objects.filter(pk=platform_id)

            service.delete()

            return JsonResponse({"message": "Service deleted successfully"}, content_type="application/json", status=204)

        else:
            messages.error(request, "Invalid request method!")

            return JsonResponse({"message": "Invalid request method"}, status=400, content_type="application/json")

    except Exception as e:
        print(e)
        return JsonResponse({"message": "Something went wrong!"}, content_type="application/json")
