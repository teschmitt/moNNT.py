from tortoise import fields
from tortoise.models import Model

from models.newsgroup import Newsgroup


class Message(Model):
    id = fields.BigIntField(pk=True)

    # mandatory headers
    from_ = fields.CharField(source_field="from", max_length=255, null=False)
    created_at = fields.DatetimeField(auto_now_add=True, null=False)
    subject = fields.CharField(max_length=255, null=False)
    message_id = fields.CharField(max_length=255, null=False)
    path = fields.TextField(null=True)

    newsgroup: fields.ForeignKeyRelation[Newsgroup] = fields.ForeignKeyField(
        "models.Newsgroup", related_name="messages"
    )

    # optional headers
    references = fields.TextField(null=True)
    reply_to = fields.CharField(max_length=255, null=True)
    organization = fields.CharField(max_length=255, null=True)
    x_ref = fields.CharField(max_length=255, null=True)
    user_agent = fields.CharField(max_length=255, null=True)

    # more on getting the complete relationship tree here:
    # https://tortoise-orm.readthedocs.io/en/latest/examples/basic.html
    # parent_id: fields.ForeignKeyNullableRelation["Message"] = fields.ForeignKeyField(
    #     "models.Message", related_name="children", null=True
    # )
    # children: fields.ForeignKeyNullableRelation["Message"]

    body = fields.TextField(null=False)

    def __str__(self):
        return (
            f"Newsgroup: {self.newsgroup.name}\n"
            f"From: {self.from_}\n"
            f"Date: {self.created_at}\n"
            f"Message-ID: {self.message_id}\n"
            f"Subject: {self.subject}\n"
            "---------------------------------------------------------\n"
            f"{self.body}\n"
            "---------------------------------------------------------"
        )

    class PydanticMeta:
        exclude = ("newsgroup",)
        computed = ()
