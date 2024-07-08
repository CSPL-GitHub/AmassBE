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

product_tag_locale = {
    "veg": "نباتي",
    "non-veg": "غير نباتي"
}

all_platform_locale = {'All': 'الجميع'}

platform_locale = (
    ('نقاط البيع', 'POS'), ('وومز', 'WOMS'), ('يأتي', 'KOMS'), ('كشك', 'Kiosk'),
    ('جرد', 'Inventory'), ('تطبيق الجوال', 'Mobile App'), ('موقع إلكتروني', 'Website')
)

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
