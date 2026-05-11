from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True, index=True)
    username = fields.CharField(max_length=255, null=True)
    full_name = fields.CharField(max_length=255, null=True)
    language = fields.CharField(max_length=10, default="uz")
    hemis_login = fields.CharField(max_length=100, null=True)
    hemis_password = fields.CharField(max_length=100, null=True)
    group_name = fields.CharField(max_length=100, null=True)
    reminder_enabled = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.telegram_id} - {self.full_name}"
