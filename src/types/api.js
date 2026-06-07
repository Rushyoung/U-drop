/**
 * @typedef {Object} LoginRequest
 * @property {string} account
 * @property {string} password
 * @property {string} device_id
 * @property {number} device_type
 * @property {string} [device_name]
 * @property {number} [expire_time]
 * @property {number} [expire_in]
 * @property {boolean} [single_use]
 * @property {boolean} [remember_me]
 */

/**
 * @typedef {Object} LoginResponse
 * @property {string|null} bearer
 */

/**
 * @typedef {Object} LogoutRequest
 * @property {string} bearer
 */

/**
 * @typedef {Object} UserPublic
 * @property {string} account
 * @property {string} uuid
 * @property {string} role
 * @property {boolean} is_active
 * @property {number} created_at
 * @property {number} trash_expire_days
 * @property {number} storage_quota
 * @property {number} used_storage
 * @property {number} temp_expire_hours
 * @property {number} sliding_window_days
 */

/**
 * @typedef {Object} UserSettingsUpdate
 * @property {number|null} [trash_expire_days]
 * @property {number|null} [temp_expire_hours]
 * @property {number|null} [sliding_window_days]
 */

/**
 * @typedef {Object} DeviceUpdateRequest
 * @property {string} device_name
 */

/**
 * @typedef {Object} DeviceResponse
 * @property {string} device_id
 * @property {number} device_type
 * @property {string|null} device_name
 * @property {number} last_seen
 */

/**
 * @typedef {Object} ErrorResponse
 * @property {number} code
 * @property {string} message
 * @property {null} data
 */

/**
 * @typedef {Object} SystemStatusResponse
 * @property {boolean} initialized
 * @property {string} version
 * @property {boolean} allow_registration
 * @property {number} auth_rate_limit
 * @property {number} default_token_expire
 */

/**
 * @typedef {Object} SystemSetupRequest
 * @property {string} account
 * @property {string} password
 * @property {boolean} allow_registration
 * @property {number} auth_rate_limit
 * @property {number} default_token_expire
 */

/**
 * @typedef {Object} SystemSettingsUpdateRequest
 * @property {boolean|null} allow_registration
 * @property {number|null} auth_rate_limit
 * @property {number|null} default_token_expire
 */

/**
 * @typedef {Object} UserQuotaUpdateRequest
 * @property {number} storage_quota
 */

/**
 * @typedef {Object} UserStatusUpdateRequest
 * @property {boolean} is_active
 */

/**
 * @typedef {Object} UserManageResponse
 * @property {string} uuid
 * @property {string} account
 * @property {string} role
 * @property {boolean} is_active
 * @property {number} used_storage
 * @property {number} storage_quota
 * @property {number} created_at
 */

/**
 * @typedef {Object} FactoryResetRequest
 * @property {string} admin_password
 */

/**
 * @typedef {Object} WSInitData
 * @property {number} sync_seq
 * @property {number} timestamp
 */

/**
 * @typedef {Object} WSMsgNewData
 * @property {number} message_id
 * @property {string} [file_hash]
 */

/**
 * @typedef {Object} WSMsgDeleteData
 * @property {number} message_id
 */

/**
 * @typedef {Object} WSDeviceUpdateData
 * @property {string} device_id
 * @property {string} device_name
 */

/**
 * @typedef {Object} WSUploadProgressData
 * @property {string} upload_id
 * @property {number} received_size
 * @property {number} total_size
 */

/**
 * @typedef {Object} UdropWSMessage
 * @property {'INIT'|'MSG_NEW'|'MSG_DELETE'|'UPLOAD_PROGRESS'|'DEVICE_UPDATE'|'PONG'} type
 * @property {number|null} [sync_seq]
 * @property {WSInitData|WSMsgNewData|WSMsgDeleteData|WSUploadProgressData|WSDeviceUpdateData|any} [data]
 */

/**
 * @typedef {Object} FileInfoShort
 * @property {string} full_hash
 * @property {number} file_size
 * @property {string|null} [mime_type]
 */

/**
 * @typedef {Object} AttachmentResponse
 * @property {number} id
 * @property {string} file_hash
 * @property {string} display_name
 * @property {FileInfoShort} file_info
 */

/**
 * @typedef {Object} BigFileReference
 * @property {number} message_id
 * @property {number} attachment_id
 * @property {string} display_name
 */

/**
 * @typedef {Object} BigFileResponse
 * @property {string} full_hash
 * @property {number} file_size
 * @property {string|null} mime_type
 * @property {number} refer_count
 * @property {BigFileReference[]} references
 */

/**
 * @typedef {Object} FileUploadIntent
 * @property {string} file_name
 * @property {number} total_size
 * @property {string} sparse_hash
 * @property {string|null} [mime_type]
 */

/**
 * @typedef {Object} MessageCreateRequest
 * @property {string|null} [content]
 * @property {number|null} [type]
 * @property {FileUploadIntent[]} [files]
 * @property {string[]} [tags]
 */

/**
 * @typedef {Object} UploadTaskInfo
 * @property {string} upload_id
 * @property {string} file_name
 */

/**
 * @typedef {Object} MessageCreateResponse
 * @property {'created'|'accepted'} status
 * @property {number} message_id
 * @property {UploadTaskInfo[]} upload_tasks
 */

/**
 * @typedef {Object} MessageResponse
 * @property {number} id
 * @property {number} type
 * @property {string|null} content
 * @property {number} timestamp
 * @property {string} device_name
 * @property {number} device_type
 * @property {string[]} tags
 * @property {AttachmentResponse[]} attachments
 */

/**
 * @template T
 * @typedef {Object} ResponseSchema
 * @property {boolean} success
 * @property {number} code
 * @property {string} message
 * @property {T|null} data
 */

/**
 * @typedef {'initial'|'after'|'before'} TimelineMode
 */

/**
 * @typedef {Object} ListMessagesParams
 * @property {TimelineMode} [mode]
 * @property {number|null} [anchor_id]
 * @property {number} [limit]
 * @property {string|null} [keyword]
 * @property {string|null} [hashtag]
 */

/**
 * @typedef {Object} ShareCreateRequest
 * @property {number} attachment_id
 * @property {string} display_name
 * @property {number|null} [expire_in]
 * @property {number} [max_uses]
 * @property {string|null} [password]
 */

/**
 * @typedef {Object} ShareCreateResponse
 * @property {string} share_id
 * @property {string} share_url
 * @property {number|null} expire_time
 */

/**
 * @typedef {Object} ShareItemResponse
 * @property {string} share_id
 * @property {string} target_type
 * @property {string} target_payload
 * @property {string|null} display_name
 * @property {number|null} expire_time
 * @property {number} max_uses
 * @property {number} use_count
 * @property {number} created_at
 * @property {number|null} file_size
 */
