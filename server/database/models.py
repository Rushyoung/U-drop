from peewee import (
    AutoField,
    BigIntegerField,
    CharField,
    CompositeKey,
    IntegerField,
    Model,
    TextField,
)

from server.database.connect import Database


class BaseModel(Model):
    class Meta:
        database = Database()


class SysSetting(BaseModel):
    key = CharField(primary_key=True)
    value = TextField()

    class Meta:  # type: ignore
        table_name = "sys_settings"


class User(BaseModel):
    uuid = CharField(primary_key=True)
    account = CharField(unique=True)
    password_hash = TextField()
    role = CharField(default="user")
    is_active = IntegerField(default=1)
    created_at = IntegerField()
    temp_expire_hours = IntegerField(default=24)
    sliding_window_days = IntegerField(default=30)
    trash_expire_days = IntegerField(default=30)
    storage_quota = BigIntegerField(default=5368709120)
    used_storage = BigIntegerField(default=0)

    class Meta:  # type: ignore
        table_name = "users"


class Device(BaseModel):
    device_id = CharField(primary_key=True)
    user_uuid = CharField(index=True)
    device_type = IntegerField()
    device_name = CharField(null=True)
    last_seen = IntegerField()

    class Meta:  # type: ignore
        table_name = "devices"


class FileInfo(BaseModel):
    full_hash = CharField(primary_key=True)
    sparse_hash = CharField(null=True, index=True)
    file_size = BigIntegerField()
    mime_type = CharField(null=True)
    storage_path = CharField()
    refer_count = IntegerField(default=0)

    class Meta:  # type: ignore
        table_name = "file_info"


class Message(BaseModel):
    id = AutoField()
    sender_uuid = CharField(index=True)
    device_id = CharField()
    type = IntegerField()
    content = TextField(null=True)
    timestamp = IntegerField(index=True)
    deleted_at = IntegerField(null=True)

    class Meta:  # type: ignore
        table_name = "messages"


class Attachment(BaseModel):
    id = AutoField()
    message_id = IntegerField(index=True)
    file_hash = CharField(index=True)
    display_name = CharField()
    sort_order = IntegerField(default=0)

    class Meta:  # type: ignore
        table_name = "attachments"


class Hashtag(BaseModel):
    id = AutoField()
    user_uuid = CharField()
    tag_name = CharField()

    class Meta:  # type: ignore
        table_name = "hashtags"
        indexes = ((("user_uuid", "tag_name"), True),)


class MessageTag(BaseModel):
    message_id = IntegerField()
    tag_id = IntegerField()

    class Meta:  # type: ignore
        table_name = "messages_tags"
        primary_key = CompositeKey("message_id", "tag_id")


class Session(BaseModel):
    bearer_token = CharField(primary_key=True)
    user_uuid = CharField(index=True)
    device_id = CharField(null=True)
    expire_time = IntegerField()
    is_single_use = IntegerField(default=0)
    is_sliding = IntegerField(default=0)

    class Meta:  # type: ignore
        table_name = "sessions"


class Share(BaseModel):
    share_id = CharField(primary_key=True)
    creator_uuid = CharField()
    target_type = CharField()
    target_payload = CharField()
    display_name = CharField(null=True)
    expire_time = IntegerField(null=True)
    max_uses = IntegerField(default=0)
    use_count = IntegerField(default=0)
    password_hash = CharField(null=True)
    created_at = IntegerField()

    class Meta:  # type: ignore
        table_name = "shares"


class UploadTask(BaseModel):
    upload_id = CharField(primary_key=True)
    user_uuid = CharField()
    temp_path = CharField()
    received_size = IntegerField()
    total_size = IntegerField()
    created_at = IntegerField()
    message_id = IntegerField(null=True)

    class Meta:  # type: ignore
        table_name = "upload_tasks"


ALL_MODELS = BaseModel.__subclasses__()
