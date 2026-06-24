from database.connect import Database as db
from peewee import (
    SQL,
    BareField,
    BigIntegerField,
    CharField,
    CompositeKey,
    ForeignKeyField,
    IntegerField,
    Model,
    PrimaryKeyField,
    TextField,
)


class BaseModel(Model):
    class Meta:
        database = db()


class FileInfo(BaseModel):
    file_size = BigIntegerField()
    full_hash = TextField(null=True, primary_key=True)
    mime_type = TextField(null=True)
    refer_count = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    sparse_hash = TextField(index=True, null=True)
    storage_path = TextField()

    class Meta:  # type:ignore
        table_name = "file_info"


class Users(BaseModel):
    account = TextField(unique=True)
    created_at = IntegerField()
    is_active = IntegerField(constraints=[SQL("DEFAULT 1")], null=True)
    password_hash = TextField()
    role = TextField(constraints=[SQL("DEFAULT 'user'")], null=True)
    sliding_window_days = IntegerField(constraints=[SQL("DEFAULT 30")], null=True)
    storage_quota = BigIntegerField(constraints=[SQL("DEFAULT 5368709120")], null=True)
    temp_expire_hours = IntegerField(constraints=[SQL("DEFAULT 24")], null=True)
    trash_expire_days = IntegerField(constraints=[SQL("DEFAULT 30")], null=True)
    used_storage = BigIntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    uuid = TextField(null=True, primary_key=True)

    class Meta:  # type:ignore
        table_name = "users"


class Devices(BaseModel):
    device_id = TextField(null=True, primary_key=True)
    device_name = TextField(null=True)
    device_type = IntegerField()
    last_seen = IntegerField()
    user_uuid = ForeignKeyField(column_name="user_uuid", field="uuid", model=Users)

    class Meta:  # type:ignore
        table_name = "devices"


class Messages(BaseModel):
    # [TODO] 无法还原表原本设计
    # id = PrimaryKeyField(IntegerField())
    content = TextField(null=True)
    deleted_at = IntegerField(null=True)
    device = ForeignKeyField(column_name="device_id", field="device_id", model=Devices)
    sender_uuid = ForeignKeyField(column_name="sender_uuid", field="uuid", model=Users)
    timestamp = IntegerField(index=True)
    type = IntegerField()

    class Meta:  # type:ignore
        table_name = "messages"
        indexes = ((("sender_uuid", "deleted_at", "id"), False),)


class Attachments(BaseModel):
    display_name = TextField()
    file_hash = ForeignKeyField(
        column_name="file_hash", field="full_hash", model=FileInfo
    )
    message = ForeignKeyField(column_name="message_id", field="id", model=Messages)
    sort_order = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:  # type:ignore
        table_name = "attachments"


class Hashtags(BaseModel):
    tag_name = TextField()
    user_uuid = ForeignKeyField(column_name="user_uuid", field="uuid", model=Users)

    class Meta:  # type:ignore
        table_name = "hashtags"
        indexes = (
            (("user_uuid", "tag_name"), True),
            (("user_uuid", "tag_name"), True),
        )


class MessagesTags(BaseModel):
    message = ForeignKeyField(column_name="message_id", field="id", model=Messages)
    tag = ForeignKeyField(column_name="tag_id", field="id", model=Hashtags)

    class Meta:  # type:ignore
        table_name = "messages_tags"
        indexes = ((("message", "tag"), True),)
        primary_key = CompositeKey("message", "tag")


class SchemaMigrations(BaseModel):
    applied_at = IntegerField()
    version = TextField(null=True, primary_key=True)

    class Meta:  # type:ignore
        table_name = "schema_migrations"


class Sessions(BaseModel):
    bearer_token = TextField(null=True, primary_key=True)
    device_id = TextField(null=True)
    expire_time = IntegerField()
    is_single_use = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    is_sliding = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    user_uuid = ForeignKeyField(column_name="user_uuid", field="uuid", model=Users)

    class Meta:  # type:ignore
        table_name = "sessions"


class Shares(BaseModel):
    created_at = IntegerField()
    creator_uuid = ForeignKeyField(
        column_name="creator_uuid", field="uuid", model=Users
    )
    display_name = TextField(null=True)
    expire_time = IntegerField(null=True)
    max_uses = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    password_hash = TextField(null=True)
    share_id = TextField(null=True, primary_key=True)
    target_payload = TextField()
    target_type = TextField()
    use_count = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:  # type:ignore
        table_name = "shares"


class SqliteSequence(BaseModel):
    name = BareField(null=True)
    seq = BareField(null=True)

    class Meta:  # type:ignore
        table_name = "sqlite_sequence"
        primary_key = False


class SysSettings(BaseModel):
    key = TextField(null=True, primary_key=True)
    value = TextField()

    class Meta:  # type:ignore
        table_name = "sys_settings"


class UploadTasks(BaseModel):
    created_at = IntegerField()
    message_id = IntegerField(null=True)
    received_size = IntegerField()
    temp_path = CharField()
    total_size = IntegerField()
    upload_id = CharField(primary_key=True)
    user_uuid = CharField()

    class Meta:  # type:ignore
        table_name = "upload_tasks"


ALL_MODELS = BaseModel.__subclasses__()
