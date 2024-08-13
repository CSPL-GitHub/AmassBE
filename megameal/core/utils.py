from enum import IntEnum
from django.db import models
# from country_converter import CountryConverter
import pycountry
from django.core.mail import send_mail



class OrderAction(models.IntegerChoices):
  SEND = 1,'SEND'
  RECIEVE = 2,'RECIEVE'
  BOTH = 3,'BOTH'
  
  def get_order_action_value(order_action_string):
      for order_action in OrderAction.choices:
        if order_action[1] == order_action_string:
            return order_action[0]
      return None
  

class OrderStatus(models.IntegerChoices):
  OPEN = 1,'OPEN'
  COMPLETED = 2,'COMPLETED'
  CANCELED = 3,'CANCELED'
  INPROGRESS=4,'INPROGRESS'
  PREPARED=5,'PREPARED'

  def get_order_status_value(order_status_string):
      for order_status in OrderStatus.choices:
        if order_status[1] == order_status_string:
            return order_status[0]
      return None
  

class KOMSOrderStatus(models.IntegerChoices):
  PENDING = 1, 'PENDING'
  PROCESSING = 2, 'PROCESSING'
  READY = 3, 'READY'
  ONHOLD = 4, 'ONHOLD'
  CANCELED = 5, 'CANCELED'
  RECALL = 6, 'RECALL'
  HIGH = 7, 'HIGH'
  ASSIGN = 8, 'ASSIGN'
  INCOMING = 9, 'INCOMING'
  CLOSE = 10, 'CLOSE'

  def get_koms_order_status_value(order_status_string):
    for order_status in KOMSOrderStatus.choices:
      if order_status[1] == order_status_string:
        return order_status[0]
      
    return None

  
class OrderType(models.IntegerChoices):
    PICKUP = 1, 'PICKUP'
    DELIVERY = 2, 'DELIVERY'
    DINEIN = 3, 'DINEIN'

    def get_order_type_value(order_type_string):
      for order_type in OrderType.choices:
        if order_type[1] == order_type_string:
            return order_type[0]
      return None
    
class TaxLevel(models.IntegerChoices):
  PRODUCT =1,'PRODUCT'
  ORDER = 2,'ORDER'

  def get_Tax_Level_value(tax_level_string):
      for tax_level in TaxLevel.choices:
        if tax_level[1] == tax_level_string:
            return tax_level[0]
      return None


class DiscountCal(models.IntegerChoices):
  PERCENTAGE = 1,'PERCENTAGE'
  AMOUNT = 2,'AMOUNT'

  def get_discount_cal_type(dis_type_string):
      for dis_type in DiscountCal.choices:
        if dis_type[1] == dis_type_string:
            return dis_type[0]
      return None


class CorePlatform(models.IntegerChoices):
  KOMS = 1,'KOMS'
  # WOOCOMMERCE = 2,'WOOCOMMERCE'
  # SHOPIFY = 3,'SHOPIFY'
  # MAGENTO = 4,'MAGENTO' 
  KIOSK = 5,'KIOSK'
  POS = 6,'POS'
  WOMS = 7,'WOMS'
  INVENTORY = 8,'INVENTORY'
  NEXTJS = 9,'NEXTJS'


  def get_core_platform(dis_type_string):
      for dis_type in CorePlatform.choices:
        if dis_type[1] == dis_type_string:
            return dis_type[0]
      return None

class ClassNames():
  WOOCOMMERCE_CLASS="WooCommerce"
  WOMS_CLASS="WomsEcom"
  SQUARE_CLASS="SquareIntegration"  

class ModifierType():
   MULTIPLE='MULTIPLE'
   SINGLE='SINGLE'

class API_Messages():
   SUCCESSFUL="SUCCESSFUL"
   ERROR="ERROR"
   STATUS="status"
   PAYMENT="PAYMENT"
   RESPONSE="RESPONSE"

class Short_Codes():
   ERROR=1
   CONNECTED_BUT_NOTFOUND=2
   CONNECTED_AND_CREATED=3
   CONNECTED_AND_FOUND=4
   CONNECTED_AND_UPDATED=5
   SUCCESS=200
   
class UpdatePoint():
   POS="POS"
   KOMS="KOMS"
   WOOCOMERCE="WOOCOMMERCE"

class PaymentType(models.IntegerChoices):
  CASH=1,"CASH"
  ONLINE=2,"ONLINE"
  BANK=3,"CARD"
  SPLIT=4,"SPLIT"
  def get_payment_str(number):
      for order_action in PaymentType.choices:
        if order_action[0] == number:
            return order_action[1]
      return None
  def get_payment_number(str):
      for order_action in PaymentType.choices:
        if order_action[1] == str:
            return order_action[0]
      return None
class CountyConvert():
  def country_name_to_iso3166(country_name):
    try:
        country = pycountry.countries.get(name=country_name)
        if country:
            return country.alpha_2
        else:
            return None
    except pycountry.exceptions.CountryNotFoundError:
        return None


def send_order_confirmation_email(sender, receiver, subject, email_body_type, email_body):
  try:
    if email_body_type == "plain_text":
      mail_status = send_mail(
        subject,
        email_body,
        sender,
        [receiver],
        fail_silently=False,
      )
    
    elif email_body_type == "html":
      mail_status = send_mail(
        subject,
        "",
        sender,
        [receiver],
        html_message=email_body,
        fail_silently=False,
      )
    
    return mail_status
  
  except Exception as e:
    error = str(e)

    return error
