from django.contrib import admin
from backend.backend1.models import Exercise, User,SavedWorkout, PlannedWorkout, NowPlayingTrack, UserUploadWorkedouts

admin.site.register(Exercise)
admin.site.register(User)
admin.site.register(SavedWorkout)
admin.site.register(PlannedWorkout)
admin.site.register(NowPlayingTrack)
admin.site.register(UserUploadWorkedouts)
