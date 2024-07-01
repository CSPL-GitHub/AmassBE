from rest_framework.authentication import TokenAuthentication
from koms.models import Stations
from rest_framework import HTTP_HEADER_ENCODING, exceptions

class UserAuthentication(TokenAuthentication):

    def authenticate(self, request):
        secret_token = request.META.get('HTTP_AUTHORIZATION')
        if not secret_token:
            return None
        try:
            ua = Stations.objects.get(key=secret_token)
        except Stations.DoesNotExist:
            print('fail')
            ua = Stations.objects.all().first()#TODO addVendor
        return (ua, None)