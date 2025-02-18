from channels.generic.websocket import AsyncJsonWebsocketConsumer

class SpotifyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["username"]
        self.group_name = f"user_{self.user_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    async def receive_json(self, content):
        print("📩 Received JSON:", content)  # ✅ Debugging: Log received data
        track_data = content.get('track')  # 🔥 Fix: Extract from `track` key
        if track_data:
            track_name = track_data.get('track_name')
            artist_name = track_data.get('artist_name')
            album_image_url = track_data.get('album_image_url')
        else:
            print("❌ No track data found in JSON:", content)
            return  # Stop processing if track data is missing
        if not track_name or not artist_name:
            print("❌ Missing track data:", track_data)
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
        print("📡 Broadcasting update:", event)  # ✅ Check outgoing message
        await self.send_json(event)