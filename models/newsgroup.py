from tortoise import fields
from tortoise.models import Model


class Newsgroup(Model):
    # create table if not exists newsgroups
    # (
    #     id          int auto_increment
    #         primary key,
    #     group_name  varchar(255)      not null,
    #     table_name  varchar(255)      not null,
    #     is_active   tinyint default 1 not null,
    #     description text              null,
    #     created_at  datetime          not null,
    #     updated_at  datetime          not null
    # )

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)
    is_active: fields.BooleanField(null=False, default=True)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, null=False)
    updated_at = fields.DatetimeField(auto_now=True, null=False)

    messages: fields.ReverseRelation["Message"]

    class Meta:
        ordering = ["name"]

    def count_messages(self):
        return

    def __repr__(self):
        return f"Newsgroup <{self.name}>"
