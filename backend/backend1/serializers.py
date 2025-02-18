from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Exercise, User, SavedWorkout, PlannedWorkout,UserUploadWorkedouts, NowPlayingTrack

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Exercise
        fields = '__all__'
        
class UserUploadWorkoutsSerializer(serializers.ModelSerializer):
    img_url = serializers.ListField(child=serializers.URLField(), required=False)  # Ensures correct serialization
    primaryMuscles = serializers.ListField(child=serializers.CharField(), required=False)  # Ensures it's a proper li
    class Meta: 
        model = UserUploadWorkedouts
        fields = '__all__'
    def create(self, validated_data):
        return super().create(validated_data)

class UserSerializer(serializers.ModelSerializer):
    date_joined = serializers.SerializerMethodField()

    def get_date_joined(self, obj):
        return obj.date_joined.date().strftime("%Y-%m-%d")
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'username', 'streak', 'image_url', 'date_joined', 'streak', 'weight', 'height', 'goal_weight', 'phone_number', 'is_searchable', 'is_private']

        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': False}
        }
    def validate_username(self, value):
        """Ensure the username is unique before updating"""
        user = self.instance
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Username already taken")
        return value
    def validate(self, data):
        """If there is a null or blank value in the request and then it doesn't update it"""
        cleaned_data = {key:value for key, value in data.items() if value not in [None, ""]}
        return cleaned_data
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)

        if password is not None:
            instance.set_password(password)
        # instance.is_active = False
        instance.save()
        return instance
        
class SavedWorkoutSerializer(serializers.ModelSerializer):
    exercise_id = serializers.UUIDField(write_only=True)
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = SavedWorkout
        fields = ['id', 'user', 'exercise', 'exercise_id', 'date_saved']
        extra_kwargs = {
            'user': {'read_only': True},
            'date_saved': {'read_only': True}
        }

    def create(self, validated_data):
        exercise_id = validated_data.pop('exercise_id')
        exercise = Exercise.objects.get(id=exercise_id)
        saved_workout = SavedWorkout.objects.create(exercise=exercise, **validated_data)
        return saved_workout
    
class PlannedWorkoutSerializer(serializers.ModelSerializer):
    saved_workout = serializers.PrimaryKeyRelatedField(queryset=SavedWorkout.objects.all())
    saved_workout_details = SavedWorkoutSerializer(source='saved_workout', read_only=True)
    class Meta:
        model = PlannedWorkout
        fields = '__all__'
class NowPlayingTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = NowPlayingTrack
        fields = '__all__'