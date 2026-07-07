from django.contrib.auth.backends import BaseBackend
from my_psc_kerala.models import PSCUser

class EmailAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get('email')
        if not email:
            return None
        try:
            user = PSCUser.objects.get(email=email)
            if user.check_password(password):
                return user
        except PSCUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return PSCUser.objects.get(pk=user_id)
        except PSCUser.DoesNotExist:
            return None
