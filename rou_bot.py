from telethon.sync import TelegramClient, events
from telethon import functions, types
from telethon.events.newmessage import NewMessage
from telethon.tl.patched import Message
from telethon.tl.types import Channel, Chat, PeerChannel, MessageFwdHeader, UpdateNewChannelMessage
from rou_models import Pickup, PickupType
from datetime import timedelta
from config import API_ID ,API_HASH, ROU_CHANNEL

client = TelegramClient('rou_session', API_ID, API_HASH)
client.start()


@client.on(events.NewMessage)
async def handler(event: NewMessage.Event):
    message: Message = event.message
    if type(event.chat) != Channel:
        return
    chat: Channel = event.chat
    if chat.id != ROU_CHANNEL:
        return
    # original_update:UpdateNewChannelMessage = event.original_update
    # peer_channel:PeerChannel = message.to_id
    message_txt = message.message
    fwd_from: MessageFwdHeader = message.fwd_from
    original_poster = fwd_from.from_id if (fwd_from and fwd_from.from_id) else ''
    original_poster_name = fwd_from.from_name if (fwd_from and fwd_from.from_name) else ''
    pickup_type = PickupType.unknown
    post_date = message.date + timedelta(hours=8) #根据文档，date为utc0时区的时间，所以需要矫正一下
    pickup = Pickup(message=message_txt, poster=original_poster, poster_name=original_poster_name,
                    post_date=post_date, type=pickup_type)
    pickup.save()


client.run_until_disconnected()
