import telebot
from flask import Flask, request
import config
from botlib import ChatHandler, CallHandler

TOKEN = config.TELEGRAM_TOKEN
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

print("App ready...")

@bot.message_handler(commands=["menu"])
def send_menu(message):
    with ChatHandler(bot) as handler:
        handler.show_menu(str(message.chat.id))


@bot.message_handler(commands=["add"])
def add_chat(message):
    with ChatHandler(bot) as handler:
        handler.add_chat(str(message.from_user.id), str(message.chat.id))


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    CallHandler(bot, call).callback()


@server.route("/" + TOKEN, methods=["POST"])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="your heroku app" + TOKEN)
    return "!", 200


if __name__ == "__main__":
    bot.polling(none_stop=True)
