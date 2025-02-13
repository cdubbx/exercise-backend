from channels.generic.websocket import AsyncJsonWebsocketConsumer

class SpotifyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["username"]
        self.group_name = f"user_{self.user_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    async def receive_json(self, content, ):
        track_name = content.get('track_name')
        artist_name = content.get('artist_name')
        album_image_url = content.get('album_image_url')

        await self.channel_layer.group_send(
            self.group_name, 
            {
                "type": "send.update",
                "track_name": track_name,
                "artist_name": artist_name,
                "album_image_url": album_image_url,
            }
        )
    async def send_update(self, event):
        await self.send_json(event)