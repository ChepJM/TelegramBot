import datetime
import requests
import re
from telethon import client, events
from telethon.hints import Entity
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import Channel, InputMediaPoll, MessageMediaPoll, MessageEntityUrl, Message
from telethon import functions, types
from telethon.errors.rpcerrorlist import MsgIdInvalidError
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from typing import List, Tuple, Dict

import warnings
warnings.filterwarnings("ignore")


class NTAStat:
    
    # Id и Hash приложения Telegram
    API_ID = "********"
    API_HASH = "********************************"

    # Id канала
    CHAT_ID = -1001127464933
    
    # StringSession are a convenient way to embed your login credentials directly into your code for extremely easy portability, since all they take is a string to be able to login without asking for your phone and code (or faster start if you’re using a bot token).
    SESSION_STRING = "****="
    
    def __init__(self):
        self.client = client = TelegramClient(StringSession(NTAStat.SESSION_STRING), NTAStat.API_ID, NTAStat.API_HASH).start()
        self.channel = self.client.get_entity(NTAStat.CHAT_ID)
    
    def _get_session_string(self):
        """Функция позволяет получить SESSION_STRING."""
        with TelegramClient(StringSession(), NTAStat.API_ID, NTAStat.API_HASH) as client:
                print(client.session.save())
        
    def _get_urls(self, message: MessageEntityUrl) -> List[str]:
        """Функция возвращает списка url из сообщения, которые содержат 'newtechaudit'."""
        entities = message.entities
        nta_urls = list()
        if entities:
            urls = [(url.offset, url.offset + url.length) for url in entities if isinstance(url, MessageEntityUrl)]
            nta_urls = [message.message[nta_url[0]: nta_url[1]] for nta_url in urls if "newtechaudit" in message.message[nta_url[0]: nta_url[1]]]
        return nta_urls
    
    def _get_messages(self) -> List[Message]:
        """Функция возвращает список всех сообщений в канале."""
        messages = list()
        for message in self.client.iter_messages(self.channel):
            messages.append(message)
        return messages
        
    def _get_title(self, url: str) -> str:
        """Функция возвращает заголовок страницы."""
        try:
            response = requests.get(url, verify=False)
            return re.search('(?<=<title>).+?(?=</title>)', response.text, re.DOTALL).group().strip()
        except:
            return None
        
    def _get_all_views(self) -> int:
        """Функция считает суммарное количество просмотров по всем постам 'newtechaudit'."""
        messages = self._get_messages()
        views = 0
        for message in messages:
            if message.views:
                views += message.views
        return views
    
    def _get_message_comments(self, message: Message) -> List[Message]:
        """Функция возвращает список всех комментариев к конкретному сообщению."""
        try:
            message_comments = list()
            offset = 0
            limit = 100
            while True:
                comments_batch = self.client(functions.messages.GetRepliesRequest(
                                                    peer=self.channel,
                                                    msg_id=message.id,
                                                    offset_id=offset,
                                                    offset_date=0,
                                                    add_offset=0,
                                                    limit=limit,
                                                    max_id=0,
                                                    min_id=0,
                                                    hash=0
                ))
                if not comments_batch.messages:
                    break
                message_comments.extend(comments_batch.messages)
                offset = comments_batch.messages[-1].id
            return message_comments
        except MsgIdInvalidError:
            return []
            
    def get_posts_data(self) -> Dict:
        """
            Функция формирует словарь с данными по всем постам.
            
            post_data = {
                            'tg_post_data': [
                                                {
                                                    'post_id': int,
                                                    'post_link': str,
                                                    'post_title': str,
                                                    'post_stat': int,
                                                    'post_date': str
                                                },
                                                ...
                                                {
                                                    ...
                                                }
                                            ]
                        }
        """
        posts_data = {'tg_posts_data': []}
        messages = self._get_messages()
        for message in messages:
            urls = self._get_urls(message)
            if len(urls) == 1:
                posts_data['tg_posts_data'].append({
                                                'post_id': message.id,
                                                'post_link': urls[0],
                                                'post_title': self._get_title(urls[0]),
                                                'post_stat': message.views,
                                                'post_date': message.date.strftime("%Y-%m-%d %H:%M:%S")
                })
        return posts_data
        
    def get_comments_data(self) -> Dict:
        """Функция формирует словарь с данными по всем комментариям к постам.
        
        comments = {
                        'tg_comments': [
                                            {
                                                'post_title': str,
                                                'post_link': str,
                                                'post_commentary_id': int,
                                                'post_commentary': str,
                                                'post_commentary_author': int,
                                                'post_commentary_date': str
                                            },
                                            ...
                                            {
                                                ...
                                            }
                                        ]
                    }
        
        Если нужны названия постов, то надо раскомментить строку '#title = self._get_title(urls[0])' и в строке ''post_title': None,' заменить None на title.
        """
        comments = {'tg_comments': []}
        
        for message in self._get_messages():
            urls = self._get_urls(message)
            if len(urls) == 1:
                #title = self._get_title(urls[0])
                for comment in self._get_message_comments(message):
                    comments['tg_comments'].append({
                                        'post_title': None,
                                        'post_link': urls[0],
                                        'post_commentary_id': comment.id,
                                        'post_commentary': comment.message,
                                        'post_commentary_author': comment.from_id.user_id,
                                        'post_commentary_date': comment.date.strftime("%Y-%m-%d %H:%M:%S")
                    })
        return comments

    def get_subscribers(self):
        """Функция формирует словарь с данными по подписчикам канала.
            
            number_subscribers_data = {
                            'group_id': int,
                            'subscribers_count': int,
                            'collection_date': str
                        }
        """

        channel_full_info = self.client(GetFullChannelRequest(channel=self.channel))
        subscribers_data = {
            'group_id': channel_full_info.full_chat.id, 
            'subscribers_count': channel_full_info.full_chat.participants_count,
            'collection_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return subscribers_data

        
    def test(self):
        """Функция для экспериментов."""
        messages = self._get_messages()
        for message in messages:
            entities = message.entities
            print(message.message, entities)

def main():
    nta_stat = NTAStat()
    print(nta_stat.get_posts_data())
    print(nta_stat.get_comments_data())

if __name__ == "__main__":
    main()
