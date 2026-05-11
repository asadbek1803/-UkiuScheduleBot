from tortoise.models import Model
from tortoise import fields
from models.user import User


class Schedule(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="schedules")
    week_id = fields.CharField(max_length=20)
    day = fields.CharField(max_length=50)
    pair_number = fields.IntField(default=0)
    subject = fields.TextField(default="")
    teacher = fields.CharField(max_length=255, null=True)
    room = fields.CharField(max_length=100, null=True)
    lesson_type = fields.CharField(max_length=100, null=True)
    lesson_time = fields.CharField(max_length=50, default="")
    cached_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "schedules"

    def __str__(self):
        return f"{self.day} #{self.pair_number} - {self.subject}"
