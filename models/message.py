from tortoise import fields
from tortoise.models import Model

from models.newsgroup import Newsgroup


class Message(Model):
    # create table if not exists group_table_name
    # (
    #     id           bigint auto_increment
    #         primary key,
    #     `from`       text     not null,
    #     `references` text     null,
    #     message_id   text     not null,
    #     thread_id    bigint   null,
    #     parent_id    bigint   null,
    #     subject      text     not null,
    #     body         longtext not null,
    #     created_at   datetime not null,
    #     updated_at   datetime not null
    # )

    id = fields.BigIntField(pk=True)

    newsgroup: fields.ForeignKeyRelation[Newsgroup] = fields.ForeignKeyField(
        "models.Newsgroup", related_name="messages"
    )

    sender = fields.TextField(null=False)
    references = fields.TextField(null=True)
    message_id = fields.TextField(null=False)
    thread_id = fields.BigIntField(null=True)

    # more on getting the complete relationship tree here:
    # https://tortoise-orm.readthedocs.io/en/latest/examples/basic.html
    parent_id: fields.ForeignKeyNullableRelation["Message"] = fields.ForeignKeyField(
        "models.Message", related_name="children", null=True
    )
    children: fields.ForeignKeyNullableRelation["Message"]

    subject = fields.TextField(null=False)
    body = fields.TextField(null=False)
    created_at = fields.DatetimeField(null=False)
    updated_at = fields.DatetimeField(null=False)

    def __str__(self):
        return (f"Newsgroup: {self.newsgroup}\n"
                f"Sender: {self.sender}\n"
                f"Created: {self.created_at}        \n"
                f"Message ID: {self.message_id}\n"
                f"Subject: {self.subject}\n"
                f"---------------------------------------------------------\n"
                f"{self.body}\n"
                f"---------------------------------------------------------")

