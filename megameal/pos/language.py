order_type_english = {
    "All": "All",
    1: "Pickup",
    2: "Delivery",
    3: "DineIn"
}

order_type_locale = {
    "All": "الجميع",
    1: "يلتقط",
    2: "توصيل",
    3: "تناول الطعام في"
}

koms_order_status_english = {
    "All": "All",
    1: 'Pending',
    2: 'Processing',
    3: 'Ready',
    4: 'Onhold',
    5: 'Canceled',
    6: 'Recall',
    7: 'High',
    8: 'Assign',
    9: 'Incoming',
    10: 'Close'
}

koms_order_status_locale = {
    "All": "الجميع",
    1: 'قيد الانتظار',
    2: 'يعالج',
    3: 'مستعد',
    4: 'في الانتظار',
    5: 'ألغيت',
    6: 'يتذكر',
    7: 'عالي',
    8: 'تعيين',
    9: 'وارد',
    10: 'يغلق'
}

payment_status_english = {
    'True': 'Paid',
    'False': 'Pending',
    'Unknown': 'Unknown'
}

payment_status_locale = {
    'True': 'مدفوع',
    'False': 'قيد الانتظار',
    'Unknown': 'مجهول'
}

payment_type_english = {
    1: 'Cash',
    2: 'Online',
    3: 'Card'
}

payment_type_locale = {
    1: 'نقدي',
    2: 'متصل',
    3: 'بطاقة'
}

all_platform_locale = {'All': 'الجميع'}

platform_locale = (
    ('نقاط البيع', 'POS'), ('وومز', 'WOMS'), ('يأتي', 'KOMS'), ('كشك', 'Kiosk'),
    ('جرد', 'Inventory'), ('تطبيق الجوال', 'Mobile App'), ('موقع إلكتروني', 'Website')
)

sort_by_locale_for_report_excel = {
    "ascending": "تصاعدي",
    "descending": "تنازلي"
}

order_type_locale_for_excel = {
    "All": "الجميع",
    "all": "الجميع",
    "delivery": "توصيل",
    "pickup": "يلتقط",
    "dinein": "تناول الطعام في",
    "online": "متصل",
    "offline": "غير متصل على الانترنت"
}

excel_headers_locale = {
    "Order ID": "رقم الطلب",
    "Platform": "منصة",
    "Start Date": "تاريخ البدء",
    "End Date": "تاريخ الانتهاء",
    "Order Type": "نوع الطلب",
    "Order Status": "حالة الطلب",
    "Order Time": "وقت الطلب",
    "Top": "قمة",
    "Sorted by": "مرتبة حسب",
    "Total": "المجموع",
    "Total records": "إجمالي السجلات",
    "Total orders": "إجمالي الطلبات",
    "Total Orders": "إجمالي الطلبات",
    "Total revenue": "إجمالي الإيرادات",
    "Total Points Credited": "إجمالي النقاط المعتمدة",
    "Total Points Redeemed": "إجمالي النقاط المستردة",
    "Total Online Orders": "إجمالي الطلبات عبر الإنترنت",
    "Total Offline Orders": "إجمالي الطلبات غير المتصلة بالإنترنت",
    "Total Delivery Orders": "إجمالي طلبات التسليم",
    "Total Pickup Orders": "إجمالي طلبات الاستلام",
    "Total DineIn Orders": "إجمالي طلبات تناول الطعام",
    "Total Tax Collected": "إجمالي الضريبة المحصلة",
    "Total Revenue Generated": "إجمالي الإيرادات المتولدة",
    "Cash Payment Orders": "أوامر الدفع النقدي",
    "Online Payment Orders": "أوامر الدفع عبر الإنترنت",
    "Card Payment Orders": "أوامر الدفع بالبطاقة",
    "Quantity Sold": "الكمية المباعة",
    "Quantity Cancelled": "تم إلغاء الكمية",
    "Unit Price": "سعر الوحدة",
    "Total Sale": "إجمالي البيع",
    "Amount": "كمية",
    "Payment Type": "نوع الدفع",
    "Payment Status": "حالة السداد",
    "Transaction ID": "رقم المعاملة",
    "Customer Name": "اسم الزبون",
    "Phone Number": "رقم التليفون",
    "Email ID": "عنوان الايميل",
    "Address": "عنوان",
    "Most Ordered Items": "العناصر الأكثر طلبًا",
    "Complete Orders": "أوامر كاملة",
    "Cancelled Orders": "الطلبات الملغاة",
    "Processing Orders": "تجهيز الطلبات",
    "Delivery Orders": "أوامر التسليم",
    "Pickup Orders": "أوامر الالتقاط",
    "DineIn Orders": "طلبات داين إن",
    "Cancelled Products": "المنتجات الملغاة",
    "Loss Made": "الخسارة التي تم تحقيقها",
    "Revenue": "ربح",
    "Estimated Revenue": "الإيرادات المقدرة",
    "Revenue Generated": "الإيرادات المتولدة",
    "Cancelled Product Details": "تفاصيل المنتج الملغاة",
    "Most Ordered Products": "المنتجات الأكثر طلبا",
    "Category": "فئة",
    "Product Name": "اسم المنتج",
    "Orders": "طلبات",
    "Pincode": "الرمز السري",
    "Locality": "محلية",
    "Tax Collected": "الضرائب المحصلة",
    "Cash Payment": "دفع نقدا",
    "Online Payment": "Online Payment",
    "Card Payment": "بطاقه ائتمان",
    "Online Orders": "الطلبات عبر الإنترنت",
    "Offline Orders": "الطلبات دون اتصال بالإنترنت",
    "Filtered by": "تمت التصفية بواسطة",
    "Instance": "مثال",
    "Order Count Data": "بيانات عدد الطلبات",
    "Tax Collection Data": "بيانات تحصيل الضرائب",
    "Tax Collection from Delivery": "تحصيل الضرائب من التسليم",
    "Tax Collection from Pickup": "تحصيل الضرائب من بيك اب",
    "Tax Collection from DineIn": "تحصيل الضرائب من داين إن",
    "Tax Collection from Offline Orders": "تحصيل الضرائب من الطلبات غير المتصلة بالإنترنت",
    "Tax Collection from Online Orders": "تحصيل الضرائب من الطلبات عبر الإنترنت",
    "Tax Collection from Cash Payment": "تحصيل الضرائب من الدفع النقدي",
    "Tax Collection from Online Payment": "تحصيل الضرائب من الدفع عبر الإنترنت",
    "Tax Collection from Card Payment": "تحصيل الضرائب من دفع البطاقة",
    "Revenue Generation Data": "بيانات توليد الإيرادات",
    "Revenue from Delivery": "الإيرادات من التسليم",
    "Revenue from Pickup": "الإيرادات من بيك اب",
    "Revenue from DineIn": "الإيرادات من داين إن",
    "Revenue from Offline Orders": "الإيرادات من الطلبات دون اتصال بالإنترنت",
    "Revenue from Online Orders": "الإيرادات من الطلبات عبر الإنترنت",
    "Revenue from Cash Payment": "الإيرادات من الدفع النقدي",
    "Revenue from Online Payment": "الإيرادات من الدفع عبر الإنترنت",
    "Revenue from Card Payment": "الإيرادات من دفع البطاقة",
}

weekdays_locale = {
    "Monday": "الاثنين",
    "Tuesday": "يوم الثلاثاء",
    "Wednesday": "الأربعاء",
    "Thursday": "يوم الخميس",
    "Friday": "جمعة",
    "Saturday": "السبت",
    "Sunday": "الأحد"
}


def order_has_arrived_locale(external_order_id):
    return f"انه وصل .. او انها وصلت {external_order_id} رقم الأمر"

def table_created_locale(table_number, floor_name):
    return f"{floor_name} تم إنشاؤها على {table_number} الجدول رقم."

def table_deleted_locale(table_number, floor_name):
    return f"{floor_name} حذف على {table_number} الجدول رقم."

def get_key_value(language, dictionary, key):
    if language == "English":
        if dictionary == "order_type":
            value = order_type_english[key]

        elif dictionary == "koms_order_status":
            value = koms_order_status_english[key]

        elif dictionary == "payment_status":
            value = payment_status_english[key]

        elif dictionary == "payment_type":
            value = payment_type_english[key]

    else:
        if dictionary == "order_type":
            value = order_type_locale[key]

        elif dictionary == "koms_order_status":
            value = koms_order_status_locale[key]

        elif dictionary == "payment_status":
            value = payment_status_locale[key]

        elif dictionary == "payment_type":
            value = payment_type_locale[key]

    return value


def check_key_exists(language, dictionary, key):
    if language == "English":
        if dictionary == "order_type":
            value = key in order_type_english.keys()

        elif dictionary == "koms_order_status":
            value = koms_order_status_english.keys()

    else:
        if dictionary == "order_type":
            value = key in order_type_locale.keys()

        elif dictionary == "koms_order_status":
            value = koms_order_status_locale.keys()

    return value
