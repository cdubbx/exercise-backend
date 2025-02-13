from django.db import models
from django.contrib.auth.models import AbstractUser
from backend.backend1.managers import CustomerUserManager
from django.conf import settings
import random 
from datetime import date, timedelta
import string

from uuid import uuid4
import uuid
# Create your models here.
class User(AbstractUser):
    email = models.CharField(max_length = 255, unique = True)
    password = models.CharField(max_length = 255)
    username = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Make username optional
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    otp = models.CharField(null=True, blank=True, max_length=255)
    is_social_authenticated = models.BooleanField(default=False, help_text="Indicates if the user logged socially.", blank=True, null=True)   
    REQUIRED_FIELDS = []
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True, help_text="Adding the create at field")
    USERNAME_FIELD = 'email'
    image_url = models.CharField(max_length=255, blank=True, null=True)
    height = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)  
    weight = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True) 
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    streak = models.IntegerField(default=0) 
    is_trainer = models.BooleanField(default=False, blank=True, null=True)
    last_active = models.DateField(null=True, blank=True)
    streak = models.IntegerField(default=0, null=True, blank=True)
    goal_weight = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    is_private = models.BooleanField(default=False, null=True, blank=True)
    is_searchable = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self) -> str:
        return self.email
    def update_streak(self):
        today = date.today()
        if self.last_active is None:
            self.streak = 1
        elif self.last_active == today:
            return self.streak
        elif self.last_active == today - timedelta(days=1):
            self.streak += 1
        else:
            self.streak = 1

        self.last_active = today
        self.save() 
        return self.streak

    def make_random_password(self, length=8, allowed_chars=string.ascii_letters + string.digits):
        """Custom password generator"""
        return ''.join(random.choice(allowed_chars) for _ in range(length))

class Exercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    aliases = models.JSONField(blank=True, null=True)
    primaryMuscles = models.JSONField(blank = True, null = True)
    secondaryMuscles = models.JSONField(blank=True, null=True)
    force = models.CharField(max_length=50, blank= True, null = True)
    level = models.CharField(max_length=50, blank= True, null = True)
    mechanic = models.CharField(max_length=50, blank=True, null=True)
    equipment = models.CharField(max_length=50,blank= True , null =True)
    category = models.CharField(max_length=50, blank= True , null = True)
    instructions = models.JSONField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    tips = models.JSONField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    img_url = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name
    
class UserUploadWorkedouts(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_workouts', null=True)
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    aliases = models.JSONField(blank=True, null=True)
    primaryMuscles = models.JSONField(blank = True, null = True)
    secondaryMuscles = models.JSONField(blank=True, null=True)
    force = models.CharField(max_length=50, blank= True, null = True)
    level = models.CharField(max_length=50, blank= True, null = True)
    mechanic = models.CharField(max_length=50, blank=True, null=True)
    equipment = models.CharField(max_length=50,blank= True,null =True)
    category = models.CharField(max_length=50, blank= True, null = True)
    instructions = models.JSONField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    tips = models.JSONField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    img_url = models.JSONField(null=True, blank=True)
    is_public = models.BooleanField(default=False, blank=True, null=True)
    trainer_verified = models.BooleanField(default=False, blank=True, null=True)
   

    def __str__(self):
        return f"{self.user.email}-{self.name}-uploaded_workout"
    
    
class SavedWorkout(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_saved')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='saved_workouts')
    date_saved = models.DateTimeField(auto_now_add=True)
    reps = models.CharField(max_length=250, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exercise')  # Optional: ensures a user can't save the same exercise multiple times

    def __str__(self):
        return f"{self.user.email} - {self.exercise.name}"

class PlannedWorkout(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='planned_workouts')
    saved_workout = models.ForeignKey(SavedWorkout, on_delete=models.CASCADE, related_name='planned_workouts')
    day_of_the_week = models.CharField(max_length=9)
    reps = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.saved_workout.exercise.name} on {self.day_of_the_week}"
    
class NowPlayingTrack(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    track_name = models.CharField(max_length=255, null=True, blank=True)
    artist_name = models.CharField(max_length=255, null=True, blank=True)
    album_image_url = models.URLField(blank=True, null=True)
    album_name = models.CharField(max_length=255, null=True, blank=True)
    preview_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.track_name}"