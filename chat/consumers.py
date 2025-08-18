import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
  async def connect(self):
      self.user = self.scope["user"]
      if not self.user.is_authenticated:
          await self.close() # Close connection if user is not authenticated
          return

      # Each user joins a personal channel group for direct messages
      self.user_channel_name = f"chat_{self.user.id}"
      await self.channel_layer.group_add(
          self.user_channel_name,
          self.channel_name
      )
      await self.accept()

  async def disconnect(self, close_code):
      if self.user.is_authenticated:
          await self.channel_layer.group_discard(
              self.user_channel_name,
              self.channel_name
          )

  async def receive(self, text_data):
      """
      Receives messages from the WebSocket and broadcasts them.
      """
      data = json.loads(text_data)
      message_type = data.get('type')

      if message_type == 'chat_message':
          receiver_id = data['receiver_id']
          message_content = data['message']

          # Save message to database asynchronously
          message = await self.save_message(self.user, receiver_id, message_content)

          # Prepare message data for broadcasting
          message_data = {
              'type': 'chat_message_echo', # Method name in this consumer
              'message': message_content,
              'sender_id': self.user.id,
              'receiver_id': receiver_id,
              'timestamp': message.timestamp.isoformat(), # ISO format for easy JS parsing
          }

          # Send message to sender's channel (to display their own message)
          await self.channel_layer.group_send(
              self.user_channel_name,
              {**message_data, 'is_self': True} # Indicate it's the sender's own message
          )

          # Send message to receiver's channel (to display the received message)
          receiver_channel_name = f"chat_{receiver_id}"
          await self.channel_layer.group_send(
              receiver_channel_name,
              {**message_data, 'is_self': False} # Indicate it's from another user
          )

  async def chat_message_echo(self, event):
      """
      Sends the message back to the WebSocket client.
      """
      await self.send(text_data=json.dumps({
          'type': 'chat_message',
          'message': event['message'],
          'sender_id': event['sender_id'],
          'receiver_id': event['receiver_id'],
          'timestamp': event['timestamp'],
          'is_self': event['is_self']
      }))

  @sync_to_async
  def save_message(self, sender, receiver_id, content):
      """
      Helper function to save the message to the database.
      Runs synchronously in an async context.
      """
      from .models import Message # Import here to avoid circular dependency
      receiver = User.objects.get(id=receiver_id)
      message = Message.objects.create(sender=sender, receiver=receiver, content=content)
      return message
