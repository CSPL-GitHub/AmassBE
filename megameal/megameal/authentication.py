from rest_framework.authentication import TokenAuthentication
from koms.models import Station
from rest_framework import HTTP_HEADER_ENCODING, exceptions

class UserAuthentication(TokenAuthentication):

    def authenticate(self, request):
        secret_token = request.META.get('HTTP_AUTHORIZATION')
        if not secret_token:
            return None
        try:
            ua = Station.objects.get(key=secret_token)
        except Station.DoesNotExist:
            print('fail')
            ua = Station.objects.all().first()#TODO addVendor
        return (ua, None)