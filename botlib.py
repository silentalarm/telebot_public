import time
import psycopg2
import boto3
import telebot
from config import *


class Connection(object):
    """Connection to database"""
    client = {
        "ENDPOINT": ENDPOINT,
        "PORT": PORT,
        "USER": USER,
        "REGION": REGION,
        "DBNAME": DBNAME,
        "AWS_ACCESS_ID": AWS_ACCESS_ID,
        "AWS_SECRET_KEY": AWS_SECRET_KEY
    }

    def __init__(self):
        self.connection = None
        self.cursor = None

    @staticmethod
    def __connect(client):
        """Connection to database

        Generate aws token, and create connection to DB with aws rds session
        :param client: client params
        :return: connection
        """
        try:
            session = boto3.Session(
                region_name=client["REGION"],
                aws_access_key_id=client["AWS_ACCESS_ID"],
                aws_secret_access_key=client["AWS_SECRET_KEY"]
            )
            rds_client = session.client('rds')
            auth_token = rds_client.generate_db_auth_token(
                DBHostname=client["ENDPOINT"],
                Port=client["PORT"],
                DBUsername=client["USER"],
                Region=client["REGION"],
            )
            connection = psycopg2.connect(
                host=client["ENDPOINT"],
                port=client["PORT"],
                database=client["DBNAME"],
                user=client["USER"],
                password=auth_token,
            )
        except Exception as error:
            print("Error with connection to aws rds in Connection.__connect", error)
        else:
            return connection

    @staticmethod
    def __disconnect(self):
        """Disconnect

        Close connection from DB
        :param self: self
        :return: none
        """
        if self.connection:
            self.cursor.close()
            self.connection.close()

    def __enter__(self):
        self.connection = self.__connect(Connection.client)
        self.cursor = self.connection.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__disconnect(self)


class Log(Connection):
    """Logging

    Save logs into table log
    """
    def __init__(self):
        Connection.__init__(self)

    def add(self, chat_id, cause, cur_time):
        """Inset row in log

        Send getting chat id, cause and time and
        insert into log
        :param chat_id: chat id
        :param cause: cause
        :param cur_time: cur_time
        :return: none
        """
        with Connection() as conn:
            try:
                sql_query = """insert into log(chat_id, cause, cur_time) values(%s, %s, %s);"""
                send_query = (
                    chat_id,
                    cause,
                    cur_time,
                )
                print("log" + str((chat_id, cause, cur_time)))
                conn.cursor.execute(sql_query, send_query)
                conn.connection.commit()
            except Exception as error:
                print("Error with PostgreSQL in Log.add", error)


class Whitelist(Connection):
    """Whitelist of groups

    Event for init whitelist
    """
    def __init__(self):
        Connection.__init__(self)

    def get_list(self):
        """Getting white list

        Connect to DB table "whitelist" and return string
        array of chat id
        :param self: -
        :return: string array
        """
        with Connection() as conn:
            try:
                conn.cursor.execute("select chat_id from whitelist;")
                white_list = [i[0] for i in conn.cursor.fetchall()]
            except Exception as error:
                print("Error with PostgreSQL in Whitelist.__get_list", error)
            else:
                return white_list

    def add(self, chat_id):
        with Connection() as conn:
            try:
                sql_query = """insert into whitelist(chat_id) values(%s);"""
                conn.cursor.execute(sql_query, (chat_id,))
                conn.connection.commit()
            except Exception as error:
                print("Error with PostgreSQL in Whitelist.add", error)

    def remove(self, chat_id):
        with Connection() as conn:
            try:
                sql_query = """DELETE FROM whitelist WHERE chat_id = %s;"""
                conn.cursor.execute(sql_query, (chat_id,))
                conn.connection.commit()
            except Exception as error:
                print("Error with PostgreSQL in Whitelist.remove", error)


class Message(Whitelist, Log):
    """Send message from bot"""
    def __init__(self):
        Whitelist.__init__(self)
        Log.__init__(self)

    def send(self, bot, target, text):
        """Send message from bot

        Check white list and if access approved send message,
        else chat_id not in whitelist send "Access denied" and
        sent int log table chat id and time

        :param bot: getting bot object
        :param target: targer chat id
        :param text: text
        :return: none
        """
        try:
            white_list = Whitelist.get_list(self)
            if target in white_list:
                bot.send_message(target, text)
            else:
                bot.send_message(target, "Access denied")
                cur_time = time.strftime("%d.%M.%y - %H:%M:%S")
                Log.add(self, str(target), "access_denied", str(cur_time))
        except Exception as error:
            print("Error with bot in SendMessage.__message", error)


class User(object):
    """User info

    Telegram user info
    """
    def __init__(self, tele_id, tele_name, tele_tag):
        """
        :param tele_id: telgram unique user id
        :param tele_name: nelegram first name
        :param tele_tag: telegram @tag
        """
        self.tele_id = tele_id
        self.tele_name = tele_name
        self.tele_tag = tele_tag


class Access(Connection):
    """Access

    Event get/set admin access
    """
    def __init__(self):
        Connection.__init__(self)

    def list(self, query, access):
        """Getting white list

        Connect to DB table "whitelist" and return string
        array of chat id
        :param access: list by access 2 - admins
        :return:
        """
        with Connection() as conn:
            try:
                sql_query = """select tele_id from admin_access where access""" + query + access
                conn.cursor.execute(sql_query)
                access_list = [i[0] for i in conn.cursor.fetchall()]
            except Exception as error:
                print("Error with PostgreSQL in AdminAccess.__get_access", error)
            else:
                return access_list

    def add(self, user: User, access):
        """Add admin access

        For only super admin access or hight
        :param bot: bot objrct
        :param target: chat id
        :param user: telegram user
        :param access: access 3 - admin 2 - super 0 - god
        :return:
        """
        with Connection() as conn:
            try:
                sql_query = """insert into admin_access(tele_id, tele_name, tele_tag, access) values(%s, %s, %s, %s);"""
                send_query = (
                    user.tele_id,
                    user.tele_name,
                    user.tele_tag,
                    access
                )
                conn.cursor.execute(sql_query, send_query)
                conn.connection.commit()
            except Exception as error:
                print("Error with PostgreSQL in AdminAccess.add", error)

    def remove(self, admin_access, tele_id):
        """Remove admin access

        For only super admin access
        :param admin_access: admin id who send command to remove
        :param tele_id: telegram id to delete
        :return:
        """
        with Connection() as conn:
            try:
                admin_list = self.list("<=", "2")

                if admin_access in admin_list:
                    print(1)
                    sql_query = """DELETE FROM admin_access WHERE tele_id = %s;"""
                    conn.cursor.execute(sql_query, (tele_id,))
                    conn.connection.commit()
            except Exception as error:
                print("Error with PostgreSQL in AdminAccess.remove", error)


class ChatHandler(Access, Whitelist, Log):
    """
    Handler of commands from chat
    """
    def __init__(self, bot):
        Access.__init__(self)
        Log.__init__(self)
        Whitelist.__init__(self)
        self.bot = bot

    def show_menu(self, tele_id):
        """
        Open menu to send message, edit groups and access
        :param chat_id:
        :return:
        """
        admin_ids = Access().list(">=", "0")
        super_admin_ids = Access().list("<=", "2")
        try:
            if tele_id in admin_ids:
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(text="Chats", callback_data="list_groups"))
                if tele_id in super_admin_ids:
                    markup.add(telebot.types.InlineKeyboardButton(text="Access",
                                                                  callback_data="list_access"))
                markup.add(telebot.types.InlineKeyboardButton(text="Cancel", callback_data="cancel"))
                self.bot.send_message(chat_id=tele_id, text="Menu", reply_markup=markup)
            else:
                self.bot.send_message(tele_id, "Access denied")
                cur_time = time.strftime("%d.%M.%y - %H:%M:%S")
                Log.add(self, str(tele_id), "access_denied command: /menu", str(cur_time))
        except Exception as error:
            print("Error with bot in ChatHandler.show_menu", error)

    def add_chat(self, user_id, chat_id):
        """
        add chat to white list from chat
        :param user_id:
        :param chat_id:
        :return:
        """
        admin_ids = Access().list(">=", "0")
        try:
            if user_id in admin_ids:
                self.bot.send_message(chat_id, "Chat added!")
                Whitelist().add(chat_id)
            else:
                self.bot.send_message(chat_id, "Access denied")
                cur_time = time.strftime("%d.%M.%y - %H:%M:%S")
                Log.add(self, str(chat_id), "access_denied command: /add", str(cur_time))
        except Exception as error:
            print("Error with bot in ChatHandler.add_chat", error)


class CallHandler(Access, Whitelist, Log):
    def __init__(self, bot, call):
        Access.__init__(self)
        Log.__init__(self)
        Whitelist.__init__(self)
        self.bot = bot
        self.call = call

    def callback(self):
        """
        Call handler
        :param call:
        :return:
        """
        try:
            if self.call.data == "cancel":
                self.__cancel()
            elif self.call.data == "list_groups":
                self.__list_groups()
            elif self.call.data == "list_access":
                self.__list_access()
            elif "delete_ch_" in self.call.data:
                self.__remove_chat()
            elif "delete_ac_" in self.call.data:
                self.__remove_access()
            else:
                self.bot.send_message(self.call.message.chat.id, "Wrong call")
                cur_time = time.strftime("%d.%M.%y - %H:%M:%S")
                Log.add(self, str(self.call.message.chat.id), "wrong_call", str(cur_time))
        except Exception as error:
            print("Error with bot in CallHandler.callback", error)

    def __cancel(self):
        """
        Delete bot message
        :return:
        """
        self.bot.delete_message(self.call.message.chat.id, self.call.message.message_id)

    def __list_groups(self):
        try:
            wh = Whitelist().get_list()
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row_width = 2
            for telegram_id in wh:
                chat = self.bot.get_chat(telegram_id)
                markup.add(
                    telebot.types.InlineKeyboardButton(text=chat.title, callback_data="none"),
                    telebot.types.InlineKeyboardButton(text="Удалить", callback_data="delete_ch_" + telegram_id)
                )
            markup.add(telebot.types.InlineKeyboardButton(text="Cancel", callback_data="cancel"))
            self.bot.send_message(chat_id=self.call.message.chat.id, text="Chat list:", reply_markup=markup)
        except Exception as error:
            print("Error with bot in CallHandler.__list_groups", error)
        finally:
            self.__cancel()

    def __list_access(self):
        try:
            admin_ids = Access().list(">=", "2")
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row_width = 2
            for telegram_id in admin_ids:
                user = self.bot.get_chat_member(telegram_id, telegram_id).user
                markup.add(
                    telebot.types.InlineKeyboardButton(text=user.first_name, callback_data="none"),
                    telebot.types.InlineKeyboardButton(text="Удалить", callback_data="delete_ac_" + telegram_id)
                )
            markup.add(telebot.types.InlineKeyboardButton(text="Cancel", callback_data="cancel"))
            self.bot.send_message(chat_id=self.call.message.chat.id,
                                  text="Admin list:", reply_markup=markup)
        except Exception as error:
            print("Error with bot in CallHandler.__list_access", error)
        finally:
            self.__cancel()

    def __remove_chat(self):
        try:
            chat_id = self.call.data[10:]
            Whitelist().remove(chat_id)
        except Exception as error:
            print("Error with bot in CallHandler.__remove_chat", error)
        finally:
            self.__cancel()

    def __remove_access(self):
        try:
            tele_id = self.call.data[10:]
            print(tele_id)
            Access().remove("1337", str(tele_id))
        except Exception as error:
            print("Error with bot in CallHandler.__remove_access", error)
        finally:
            self.__cancel()
