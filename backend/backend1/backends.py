import jwt 
import jwt.algorithms
import requests 
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from backend1.models import User
import logging

logger = logging.getLogger(__name__)

class AppleAuthenticationBackend(BaseBackend):
    def authenticate(self, request, id_token=None):
        if id_token is None:
            print("ID token is None.")
            return None

        print("Verifying ID token...")
        decoded_token = self._verify_id_token(id_token)
        if not decoded_token:
            print("Failed to decode ID token.")
            return None

        apple_user_id = decoded_token.get('sub')
        email = decoded_token.get('email')

        if not apple_user_id or not email:
            print("Missing user ID or email in the decoded token.")
            return None

        print(f"User ID: {apple_user_id}, Email: {email}")
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': apple_user_id,
                'password': User().make_random_password(),
                'is_social_authenticated': True,
            }
        )
        if created:
            print(f"Created new user: {user}")
        else:
            print(f"Authenticated existing user: {user}")

        return user
   
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def _verify_id_token(self, id_token):
        try:
            print("Fetching Apple public keys...")
            response = requests.get("https://appleid.apple.com/auth/keys")
            response.raise_for_status()
            apple_keys = response.json()["keys"]
            print(f"Apple keys: {apple_keys}")

            header = jwt.get_unverified_header(id_token)
            print(f"JWT Header: {header}")

            key = next((k for k in apple_keys if k["kid"] == header["kid"]), None)
            if not key:
                print("Invalid Apple key ID")
                raise ValueError("Invalid Apple key ID")
            print(f"Matching key: {key}")

            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            decoded_token = jwt.decode(
                id_token,  # Fixing typo: should use `id_token`, not `id`
                public_key,
                algorithms=["RS256"],
                audience=settings.SOCIAL_AUTH_APPLE_CLIENT_ID,
                issuer="https://appleid.apple.com"
            )
            print(f"Decoded token: {decoded_token}")
            return decoded_token

        except Exception as e:
            print(f"Error verifying ID token: {str(e)}")
            return None
