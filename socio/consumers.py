# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from django.contrib.auth.models import User
# from asgiref.sync import sync_to_async
# from accounts.models import Message, UserDetails

# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope['user']
#         self.chat_with = self.scope['url_route']['kwargs']['username']
        
#         # Sort usernames to create a consistent room name
#         usernames = sorted([self.user.username, self.chat_with])
#         self.room_name = f"chat_{usernames[0]}_{usernames[1]}"
#         self.room_group_name = f"chat_{self.room_name}"

#         # Join room group
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json['message']
#         sender = self.user
#         receiver = await sync_to_async(UserDetails.objects.get)(username=self.chat_with)

#         # Save message to database
#         message_obj = await sync_to_async(Message.objects.create)(
#             sender=sender,
#             receiver=receiver,
#             content=message
#         )

#         # Send message to room group
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 'type': 'chat_message',
#                 'message': message,
#                 'sender': sender.username,
#                 'timestamp': str(message_obj.timestamp)
#             }
#         )

#     async def chat_message(self, event):
#         # Send message to WebSocket
#         await self.send(text_data=json.dumps({
#             'message': event['message'],
#             'sender': event['sender'],
#             'timestamp': event['timestamp']
#         }))