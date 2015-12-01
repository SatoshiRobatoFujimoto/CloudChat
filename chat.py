import os.path

import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.options
from tornado.options import define, options

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

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []

    def open(self):
        ChatSocketHandler.waiters.add(self)
        self.write_message({"chats": ChatSocketHandler.cache})

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)

    @classmethod
    def send_updates(cls, chat):
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        chat = {
            "body": parsed["body"],
            }

        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates({
          "chats": [chat]
        })

def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
