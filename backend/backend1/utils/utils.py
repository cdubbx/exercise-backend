from django.core.mail import send_mail
from django.conf import settings
import random
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json
from backend1.models import Exercise
from openai import OpenAI

logger = logging.getLogger(__name__)

def send_otp(email:str, otp:int) -> bool:
    """Send the OTP to the specific email address. """
    subject = "Your One time pin code"
    message = f'Your One-Time Pin (OTP) is: {otp}'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as e:
        logger.error(f'An unexpected error occurred: {e}', exc_info=True)
        print(e)
        return False
    
def generate_otp(length=4) -> str:
    """Generate a numeric OTP of a specified length as a string"""
    otp: str = ''.join([str(random.randint(0, 9)) for _ in range(length)])
    return otp



def send_track_update(user_id, track_name, artist_name, album_image_url):
    """Sends a WebSocket update when a track changes."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "spotify_updates",  # WebSocket group name
        {
            "type": "update.track",  # 🔥 Must match the method in consumer
            "message": {
                "user_id": user_id,
                "track_name": track_name,
                "artist_name": artist_name,
                "album_image_url": album_image_url,
            },
        }
    )

def join_json(field):
    """
    Join a JSON field (string or list) into a comma-separated string.
    This is used for generating embeddings.
    """
    if field:
        if isinstance(field, str):
            try:
                data = json.loads(field)
            except Exception:
                return str(field)
        else:
            data = field
        if isinstance(data, list):
            return ", ".join(str(item) for item in data)
        return str(data)
    return None

def exercise_to_string(exercise):
    """
    Convert an exercise object to a string representation.
    This is used for generating embeddings.
    """
    primary_muscles = join_json(getattr(exercise, "primary_muscles", None))
    return f"""
    Exercise: {exercise.name}
    Description: {exercise.description}
    Category: {exercise.category}
    Force: {exercise.force}
    Equipment: {exercise.equipment}
    Primary Muscles: {primary_muscles}
    """


def generate_and_store_embeddings():
    """
    This function generates and stores embeddings for all exercises in the database.
    It retrieves all exercises, generates embeddings using the OpenAI API, and updates the database.
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    exercises = Exercise.objects.all()
    for exercise in exercises:
        if not exercise.embedding or exercise.embedding is None:
            text = exercise_to_string(exercise)
            response = client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            embedding = response.data[0].embedding
            exercise.embedding = embedding
            exercise.save()