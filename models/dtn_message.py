from tortoise import fields
from tortoise.models import Model


class DTNMessage(Model):
    id = fields.IntField(pk=True)

    # DTN related fields
    source = fields.CharField(max_length=255, null=False)
    destination = fields.CharField(max_length=255, null=False)
    data = fields.JSONField(null=False)
    delivery_notification = fields.BooleanField(default=False, null=False)
    lifetime = fields.IntField(default=24 * 3600 * 1000, null=False)

    # housekeeping fields
    retries = fields.IntField(default=0, null=False)
    error_log = fields.TextField(null=True)
    hash = fields.CharField(max_length=64, null=False)
    created_at = fields.DatetimeField(auto_now_add=True, null=False)
