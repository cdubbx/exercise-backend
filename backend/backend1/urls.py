from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExerciseListView, LoginAPIView, RegisterAPIView, UserView,LogoutView, SaveWorkOutView,  UserPlannedWorkoutsView, UserSavedWorkoutsView, SigninWIthApple, VerifyOTPAPIView, UploadWorkOutView, GetBodyPartWorkOutView, SpotifyRefreshTokenView, SpotifySwapTokenView
from .views import ResetPasswordAPIView, RequestPasswordResetAPIView, UserListView, UserDetailView, NowPlayingForUserView, UpdateNowPlayingView, EditUserView, GetUserUploadedWorkOutView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

# Using `router.register(r'exercises', ExerciseViewSet)` registers the `ExerciseViewSet` with the router,
# which automatically creates all the CRUD (Create, Read, Update, Delete) operation URLs for your `Exercise` model.
# Accessing `/exercises/` will now allow clients to perform these operations as allowed by your viewset configuration.
router = DefaultRouter()



urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('saveWorkOuts', SaveWorkOutView.as_view(), name = 'saveWorkout'),
    path('exercises/', ExerciseListView.as_view(), name='exercises'),
    path('login/', LoginAPIView.as_view()),
    path('user/', UserView.as_view(), name='user'),
    path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),
    path('social-login/', SigninWIthApple.as_view(), name='social-login'),
    path('token/swap/', SpotifySwapTokenView.as_view(), name='token-swap'),
    path('token/refresh/', SpotifyRefreshTokenView.as_view(), name='token-refresh'),
    path('user-upload-workout/', UploadWorkOutView.as_view(), name='user-upload-workout'),
    path('user-upload-workouts/', GetUserUploadedWorkOutView.as_view(), name='user-upload-workouts'), 
    path('user/update/', EditUserView.as_view(), name='user-update'),
    path("users/", UserListView.as_view(), name="user_list"),  # ✅ Paginated user list
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user_detail"),  # ✅ Fetch user by ID
    path('request-password-reset/', RequestPasswordResetAPIView.as_view(), name='request-password-reset'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset-password'),
    path('get-specific-exercises/', GetBodyPartWorkOutView.as_view(), name='GetBodyPartWorkOutView'),
    path('logout/', LogoutView.as_view()),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('userSavedWorkouts/', UserSavedWorkoutsView.as_view(), name= 'userSavedWorkOuts'),
    path('plannedWorkouts/', UserPlannedWorkoutsView.as_view(), name='planned_workouts'),
    path("now_playing/<int:user_id>/", NowPlayingForUserView.as_view(), name="now_playing_for_user"),
    path("now_playing/update", UpdateNowPlayingView.as_view(), name="update-now_playing"),
]
