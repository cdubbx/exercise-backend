from django.shortcuts import render
from rest_framework import viewsets,status
from .models import Exercise, User, SavedWorkout,PlannedWorkout, NowPlayingTrack, UserUploadWorkedouts
from .serializers import ExerciseSerializer, UserSerializer, SavedWorkoutSerializer,PlannedWorkoutSerializer, UserUploadWorkoutsSerializer, NowPlayingTrackSerializer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import get_authorization_header, TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from uuid import uuid4
from .utils.utils import send_otp, generate_otp, send_track_update
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import requests
from .backends import AppleAuthenticationBackend
import logging
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync 

logger = logging.getLogger(__name__)

import jwt
import datetime



class ExerciseCursorPagination(CursorPagination):
    page_size = 20  # Adjust as needed
    ordering = 'date_created'  # Ensure ordering by a unique, indexed field (e.g., timestamp)

class ExerciseListView(ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ExerciseSerializer
    pagination_class = ExerciseCursorPagination  # Use CursorPagination

    def get_queryset(self):
        cursor = self.request.query_params.get("cursor", "first_page")
        primaryMuscle = self.request.query_params.get("primaryMuscles")  # Get muscle filter

        # Generate a cache key based on cursor and filter parameters
        cache_key = f"exercise_cursor_{cursor}_muscle_{primaryMuscle}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return cached_data  # Return cached data
        queryset = Exercise.objects.all()
        if primaryMuscle:
            queryset = queryset.filter(primaryMuscles__icontains=primaryMuscle)  # Ensure case-insensitive match
        queryset = queryset.order_by('-date_created')  # Order for CursorPagination
        cache.set(cache_key, queryset, timeout=60 * 15)
        return queryset
# Create your views here.

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            serializer = UserSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save(is_active=False)            
            email = serializer.validated_data['email']
            otp = generate_otp()
            cache.set(f'otp_{email}', otp, timeout=300)
            send_otp(email, otp)
            
            return Response({'message': 'Account created. Verify OTP to activate.'})
        except ValidationError as ve:
            return Response({'error': ve.detail}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
class VerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')
            
            if not email or not otp:
                raise ValidationError({'error': 'Email and OTP are required.'})
            
            cached_otp = cache.get(f'otp_{email}')
            if not cached_otp or cached_otp != otp:
                raise ValidationError({'otp': 'Invalid or expired OTP.'})            
            user = User.objects.get(email=email)
            if not user.is_active:  # Check if the user is inactive
                user.is_active = True  # Activate the user
                user.save()
            else:
                return Response({'message': 'User is already activated.'})            
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            
            user_data = UserSerializer(user).data
            return Response({
                'message': 'Account successfully verified and activated.',
                'user': user_data,
                'refresh': str(refresh),
                'access': str(access),
            })
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)
        except ValidationError as ve:
            return Response({'error': ve.detail}, status=400)
        except Exception as e:
            logger.error('Unexpected error occurred in VerifyOTPAPIView', exc_info=True)
            return Response({'error': str(e)}, status=500)
        
class LoginAPIView(APIView):
    permission_classes = [AllowAny]  # Allow any user to access this view

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = User.objects.filter(email=email).first()

        if user is None:
            logger.error('User not found with email: %s', email)
            raise AuthenticationFailed('User not found')
        if not user.check_password(password):
            logger.error('Invalid password for user: %s', email)
            raise AuthenticationFailed('Invalid password')

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response = Response()

        response.data = {
            'refresh': str(refresh),
            'access': str(access),
        }

        return response

class UserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
            authenticated_user = request.user
            try:
                user = User.objects.get(id=authenticated_user.id)
                serializer = UserSerializer(user)
                return Response(serializer.data, status=200)
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=404)

class UserCursorPagination(CursorPagination):
    page_size = 10
    ordering = "date_joined"

class UserListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all().order_by("date_joined")
    serializer_class = UserSerializer
    pagination_class = UserCursorPagination

    def get_queryset(self):
        cursor = self.request.query_params.get("cursor", "first_page")        
        cached_users = cache.get(f"user_list:{cursor}")
        if cached_users:
            return cached_users
        users = super().get_queryset()
        cache.set(f"user_list:{cursor}", users, timeout=60 * 60)
        return users

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, user_id):
        cache_key = f"user_{user_id}"
        cached_user = cache.get(cache_key)
        if cached_user:
            return Response(cached_user)
        try:
            user = User.objects.get(id=user_id)
            serializer = UserSerializer(user)
            cache.set(cache_key, serializer.data, timeout=60* 60)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
class EditUserView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            user = request.user
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "User information updated successfully"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class UserSavedWorkoutsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # Use select_related to fetch related Exercise objects efficiently
        saved_workouts = SavedWorkout.objects.filter(user=user).select_related('exercise')
        serializer = SavedWorkoutSerializer(saved_workouts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
class LogoutView(APIView):
    def post(self,request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {
            'message': 'successful'
        }
        return response

class TokenRefreshView(APIView):
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if refresh_token is None:
            raise AuthenticationFailed('Refresh token required')
        try:
            payload = jwt.decode(refresh_token, 'refresh_secret', algorithms = ["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Expire refresh token, please login again')
        
        user = User.objects.filter(id=payload['id']).first()
        if not user:
            raise AuthenticationFailed('Unauthenticated')
        
        access_token_payload = {
            "id": user.id,
            "exp":datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
            "iat": datetime.datetime.utcnow()
        }

        new_acccess_token = jwt.encode(access_token_payload, 'access_secret', algorithm = "HS256")
        new_refresh_token_payload = {
            "id": payload['id'],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
            "iat": datetime.datetime.utcnow()
        }

        new_refresh_token = jwt.encode(new_refresh_token_payload,"refresh_secret", algorithm = 'HS256')


        return Response({
            'access_token': new_acccess_token,
            'refresh_token': new_refresh_token
        })
        
class UploadWorkOutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            user = request.user
            workout_data = request.data
            serializer = UserUploadWorkoutsSerializer(data=workout_data)
            if serializer.is_valid():
                workout = serializer.save(user=user)
                return Response({"message": f'Workout with {workout.id} has been saved!'}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f'An error has occurred {e}')
            logger.debug(f'An error has occured {e}')
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserUploadedWorkoutsCursorPagination(CursorPagination):
    page_size = 10
    ordering = 'date_created'

class GetUserUploadedWorkOutView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserUploadWorkoutsSerializer
    pagination_class = UserUploadedWorkoutsCursorPagination
    
    def get_queryset(self):
        cursor = self.request.query_params.get('cursor', 'first_page')
        is_public = self.request.query_params.get('is_public','false').lower() == 'true'
        cache_key = f"workoutlist_{'public' if is_public else self.request.user.id}_{cursor}"
        cached_workouts = cache.get(cache_key)
        if cached_workouts:
            return cached_workouts
        if is_public:
            workouts = UserUploadWorkedouts.objects.filter(is_public = True).order_by("-date_created")
        workouts = UserUploadWorkedouts.objects.filter(user=self.request.user).order_by("-date_created")
        cache.set(cache_key, workouts, timeout=60 * 60)
        return workouts

class GetTrainerVerifiedWorkkouts(ListAPIView):
    authentication_classes = [IsAuthenticated]
    serializer_class = UserUploadWorkoutsSerializer
    pagination_class = UserUploadedWorkoutsCursorPagination

    def get_queryset(self):
        cursor = self.request.query_params.get('cursor', 'first_page')
        cache_key = f"trainer_verfied_workouts {cursor}"
        cached_workouts = cache.get(cache_key)
        if cached_workouts:
            return cached_workouts
        workouts = UserUploadWorkedouts.objects.filter(trainer_verified=True).order_by("-date_created")
        cache.set(cache_key)
        return workouts

class GetBodyPartWorkOutView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            bodyPart = request.data.get('bodyPart')
            exercises = Exercise.objects.all()
            if bodyPart:
                exercises = exercises.filter(primaryMuscles__overlap=bodyPart)
            serializer = ExerciseSerializer(exercises, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(f'An internal error has occurred {e}')
            print(f'An internal error has occurred {e}')
            return Response({"error": f"f'An internal error has occurred {e}'"})

class SaveWorkOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        logger.debug(f'Authenticated user: {user}')  # Debugging line

        if not user:
            return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        workout_data = request.data.get('workout', {})
        exercise_id = workout_data.get('id')
        
        if not exercise_id:
            return Response({"error": "Exercise ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        saved_workout_data = {'exercise_id': exercise_id}

        serializer = SavedWorkoutSerializer(data=saved_workout_data)
        if serializer.is_valid():
            workout = serializer.save(user=user)
            return Response({"workout": workout.id}, status=status.HTTP_201_CREATED)
        else:
            logger.debug(f'Serializer errors: {serializer.errors}')  # Debugging line
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserPlannedWorkoutsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        planned_workouts = PlannedWorkout.objects.filter(user=user).select_related('saved_workout', 'saved_workout__exercise')
        serializer = PlannedWorkoutSerializer(planned_workouts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = request.user
        request.data['user'] = user.id  # Set the user
        workout_data = request.data.get('workout', {}) 
        workout = workout_data.get('exercise', {})
        exercise_id = workout.get('id')
        day_of_the_week = workout_data.get('day')
        reps = workout_data.get('reps')
        saved_workout_instance = get_object_or_404(SavedWorkout, exercise_id=exercise_id, user=user)       
        saved_workout_id = saved_workout_instance.id

        
        if not saved_workout_id or not day_of_the_week:
            return Response({"error": "Both saved_workout and day_of_the_week are required."}, status=status.HTTP_400_BAD_REQUEST)
        
     
        data = {
            'user': user.id,
            'saved_workout': saved_workout_id,
            'day_of_the_week': day_of_the_week,
            'reps': reps
        }
        

        serializer = PlannedWorkoutSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckAuthenticationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # At this point, DRF's authentication mechanisms have already checked the token
        # and populated request.user based on the token's validity.
        
        if request.user.is_authenticated:
            # The user is authenticated
            return Response({
                "authenticated": True,
                "user": str(request.user),  # Or any user-specific information you want to include
            })
        else:
            # The user is not authenticated; with IsAuthenticated, you would typically not get to this point,
            # as an unauthenticated request would be rejected before hitting the view logic.
            return Response({"authenticated": False}, status=401)

class SigninWIthApple(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            id_token = request.data.get('id_token')
            if not id_token:
                return Response({'error': 'Missing id token'}, status=400)
            
            backend = AppleAuthenticationBackend()
            user = backend.authenticate(request, id_token)
            if user:
                refresh = RefreshToken.for_user(user)
                access = refresh.access_token
                return Response({
                        'refresh': str(refresh),
                        'access': str(access),
                    }, status=200)
            else:
                return Response({"error": "Authentication failed"}, status=401)
        except Exception as e:
            print(f"An error has occured {e}")
            return Response({"error": "Internal server error"})
        
class RequestPasswordResetAPIView(APIView):
        permission_classes = [AllowAny]
        def post(self, request):
            email = request.data.get('email')        
            if not email:
                raise ValidationError({'email': 'This field is required'})
            try:
                user = User.objects.get(email=email)
                token_generator = PasswordResetTokenGenerator()
                token = token_generator.make_token(user)

                reset_link = f"exercisefrontend://reset-password?token={token}&email={email}"
                email_subject = "Password Reset Request"
                email_body = f"""
                    <p>Click the link below to reset your password:</p>
                    <a href="{reset_link}">{reset_link}</a>
                """
                email = EmailMessage(
                    subject=email_subject,
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email.content_subtype = "html"  # Set the email content to HTML
                email.send()
                return Response({'message': 'Password reset link sent to your email'})
            except User.DoesNotExist:
                raise ValidationError({'email': 'User with this email does not exist'})
            except Exception as e:
                print( f"There is an internal error {e}")
                return Response({'message': f"There is an internal error {e}"}, status=500)
            
class ResetPasswordAPIView(APIView):
        permission_classes = [AllowAny]
        def post(self, request):
            email = request.data.get('email')
            token = request.data.get('token')
            new_password = request.data.get('new_password')

            if not email or not token or not new_password:
                raise ValidationError({'message': 'Email, token, and new password are required'})
            try:
                user = User.objects.get(email=email)
                token_generator = PasswordResetTokenGenerator()
                if not token_generator.check_token(user, token):
                    raise ValidationError({'error': 'Invalid or expired token'})
                user.set_password(new_password)
                user.save()
                return Response({'message': 'Password has been reset successfully'}, status=200)
            except User.DoesNotExist:
                raise ValidationError({'email': 'User with this email does not exist'})
            except Exception as e:
                print( f"There is an internal error {e}")
                return Response({'message': f"There is an internal error {e}"}, status=500)

class TrackStreakView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
             user = request.user
             streak_user = User.objects.get(user=user)
             streak_user.update_streak()
             serializer = UserSerializer(streak_user)
             return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(f"An error has occurred {e}")
            print(f"An error has occurred {e}")
            return Response({"error": f"An error has occured {e}"}, status=status.HTTP_400_BAD_REQUEST)
   
class SpotifySwapTokenView(APIView):

    permission_classes = [AllowAny]  # ✅ Allow all users (ensure API is public)

    def post(self, request):
        try:
            code = request.data.get('code')
            print("🚀 Received request at /api/token/swap/")
            print("🔍 Request headers:", request.headers)
            print("🔍 Request body:", request.data)  # ✅ Print 
            print(code)

            payload = {
                'grant_type': 'authorization_code',
                 'code': code,
                 'redirect_uri': settings.FRONTEND_REDIRECT_URL,
                 'client_id': settings.SPOTIFY_CLIENT_ID,
                 'client_secret': settings.SPOTIFY_CLIENT_SECRET
            }
            
            response = requests.post('https://accounts.spotify.com/api/token', data=payload)
            return Response(response.json())
        except Exception as e: 
            logger.debug(f'An error has occurred {e}')
            print(f'An error has occurred {e}')
            Response({"error": f"An error has occurred {e}"})

class SpotifyRefreshTokenView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            payload = {
                'grant_type':'refresh_token',
                'refresh_token': refresh_token,
                'client_id': settings.SPOTIFY_CLIENT_ID,
                'client_secret': settings.SPOTIFY_CLIENT_SECRET,
            }
            response = requests.post('https://accounts.spotify.com/api/token', data=payload)
            try:
                response_data = response.json()
            except ValueError:  # If response is not JSON
                return Response({"error": "Invalid JSON response from Spotify"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if response.status_code != 200:
                return Response(response_data, status=response.status_code)
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class UpdateNowPlayingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            track_name = request.data.get('track_name')
            artist_name = request.data.get('artist_name')
            album_image_url = request.data.get('album_image_url')
            album_name = request.data.get('album_name')
            user = get_object_or_404(User, id=request.user.id) 
            send_track_update(user.id, track_name, artist_name, album_image_url)
            return Response({"message":"Track updated successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.debug(f'An error has occurred {e}')
            print(f'An error has occurred {e}')
            Response({"error": f"An error has occurred {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class NowPlayingForUserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            track = NowPlayingTrack.objects.filter(user=user).order_by("-timestamp").first()
            if track:
                serializer = NowPlayingTrackSerializer(track)
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response({"message": "User is currently not playing any track"}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({"error":"User doesn't exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Internal server error {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)