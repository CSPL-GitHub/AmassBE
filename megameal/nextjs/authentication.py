from rest_framework.authentication import TokenAuthentication
from nextjs.models import User
from rest_framework import HTTP_HEADER_ENCODING, exceptions

class UserAuthentication(TokenAuthentication):

    def authenticate(self, request):
        secret_token = request.META.get('HTTP_AUTHORIZATION')
        if not secret_token:
            return None
        try:
            ua = User.objects.get(key=secret_token)
        except User.DoesNotExist:
            print('fail')
            raise exceptions.AuthenticationFailed('Unauthorized')

        return (ua, None)