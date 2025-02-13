from django.contrib.auth.models import BaseUserManager
class CustomerUserManager(BaseUserManager):
    def create_user(self,email, password = None, **extra_fields):
        if not email:
            raise ValueError("The Email Field must be set")
        email = self.normalize_email(email)
        user = self.model(email = email, **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user