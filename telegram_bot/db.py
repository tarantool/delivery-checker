from enum import Enum

from peewee import (
    Model,
    SqliteDatabase,
    PostgresqlDatabase,
    AutoField,
    IntegerField,
)


class SubscribeType(Enum):
    ALL = 0
    FAILED = 1


class DB:
    def __init__(self, config):
        db_name = config.get('name')
        if db_name is None:
            db_file = config.get('file')
            if db_file is None:
                db_file = 'bot.db'
            db = SqliteDatabase(db_file)
        else:
            db_user = config.get('user', 'delivery_checker_bot')
            db_password = config.get('password')
            db = PostgresqlDatabase(db_name, user=db_user, password=db_password)

        class BaseModel(Model):
            class Meta:
                database = db

        class User(BaseModel):
            id = AutoField()
            chat_id = IntegerField(unique=True)
            subscribe_type = IntegerField()

        self.User = User
        self.User.create_table()

    def subscribe(self, chat_id: int, subscribe_type: SubscribeType):
        user = self.User.get_or_none(self.User.chat_id == chat_id)
        if user is not None:
            user.subscribe_type = subscribe_type.value
            user.save()
        else:
            user = self.User(
                chat_id=chat_id,
                subscribe_type=subscribe_type.value,
            )
            user.save()

        return user

    def unsubscribe(self, chat_id: int):
        test = self.User.delete().where(self.User.chat_id == chat_id)
        return test.execute()

    def get_subscribers_for_all(self):
        users = []
        for user in self.User.select(self.User.chat_id).where(self.User.subscribe_type == SubscribeType.ALL.value):
            users.append(user.chat_id)
        return users

    def get_subscribers_for_failed(self):
        users = []
        for user in self.User.select(self.User.chat_id):
            users.append(user.chat_id)
        return users
