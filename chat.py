import json
import threading
import os.path

import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.options
from tornado.options import define, options
from redis import Redis

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            xsrf_cookies=True,
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class Listener(threading.Thread):
    def __init__(self, r):
        threading.Thread.__init__(self)
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(["chats"])
    def work(self, item):
        if item["type"] == "message":
            chat = json.loads(item["data"])
            ChatSocketHandler.send_updates(chat)
    def run(self):
        for item in self.pubsub.listen():
            if item['data'] == "KILL":
                self.pubsub.unsubscribe()
            else:
                self.work(item)

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    redis = Redis(decode_responses=True)
    client = Listener(redis)
    client.start()

    def open(self):
        ChatSocketHandler.waiters.add(self)
        self.write_message({"chats": ChatSocketHandler.get_caches()})

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        chat_id = cls.redis.incr("nextChatId")
        redis_chat_key = "chat:{}".format(chat_id)

        cls.redis.set(redis_chat_key, json.dumps(chat))
        cls.redis.rpush("chats", redis_chat_key)

    @classmethod
    def get_caches(cls):
      chat_ids = cls.redis.lrange("chats", 0, -1)
      chats = []
      for chat_id in chat_ids:
        chat = json.loads(cls.redis.get(chat_id))
        chats.append(chat)
      return chats

    @classmethod
    def send_updates(cls, chat):
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                print("Error sending message")

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        chat = {
            "body": parsed["body"],
        }

        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.redis.publish("chats", json.dumps({
            "chats": [chat]
        }))
        
def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
