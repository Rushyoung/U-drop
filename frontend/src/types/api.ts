export interface LoginRequest {
  account: string;
  password: string;
  device_id: string;
  device_type: number;
  device_name?: string | null;
  expire_time?: number | null;
  expire_in?: number | null;
  single_use?: boolean;
  remember_me?: boolean;
}

export interface LoginResponse {
  bearer: string | null;
}

export interface LogoutRequest {
  bearer: string;
}

export interface UserPublic {
  account: string;
  uuid: string;
  role: string; // admin | user
  is_active: boolean; // 用户状态: 启用或禁用
  created_at: number;
  trash_expire_days: number;
  storage_quota: number;
  used_storage: number;
  temp_expire_hours: number;
  sliding_window_days: number;
}

export interface UserSettingsUpdate {
  trash_expire_days?: number | null;
  temp_expire_hours?: number | null;
  sliding_window_days?: number | null;
}

export interface DeviceUpdateRequest {
  device_name: string;
}

export interface DeviceResponse {
  device_id: string;
  device_type: number; // 0:Web, 1:Android, 2:PC
  device_name: string | null;
  last_seen: number;
}

export interface ErrorResponse {
  code: number;
  message: string;
  data: null;
}

export interface SystemStatusResponse {
  initialized: boolean;
  version: string;
  allow_registration: boolean;
  auth_rate_limit: number;
  default_token_expire: number;
}

export interface SystemSetupRequest {
  account: string;
  password: string;
  allow_registration: boolean;
  auth_rate_limit: number;
  default_token_expire: number;
}

export interface SystemSettingsUpdateRequest {
  allow_registration: boolean | null;
  auth_rate_limit: number | null;
  default_token_expire: number | null;
}

export interface UserQuotaUpdateRequest {
  storage_quota: number;
}

export interface UserStatusUpdateRequest {
  is_active: boolean;
}

export interface UserManageResponse {
  uuid: string;
  account: string;
  role: string;
  is_active: boolean;
  used_storage: number;
  storage_quota: number;
  created_at: number;
}

export interface FactoryResetRequest {
  admin_password: string;
}

export interface WSInitData {
  sync_seq: number;
  timestamp: number;
}

export interface WSMsgNewData {
  message_id: number;
  file_hash?: string | null;
}

export interface WSMsgDeleteData {
  message_id: number;
}

export interface WSDeviceUpdateData {
  device_id: string;
  device_name: string;
}

export interface WSUploadProgressData {
  upload_id: string;
  received_size: number;
  total_size: number;
}

export interface UdropWSMessage {
  type: 'INIT' | 'MSG_NEW' | 'MSG_DELETE' | 'UPLOAD_PROGRESS' | 'DEVICE_UPDATE' | 'PONG';
  sync_seq?: number | null;
  data?: WSInitData | WSMsgNewData | WSMsgDeleteData | WSUploadProgressData | WSDeviceUpdateData | any;
}

export interface FileInfoShort {
  full_hash: string;
  file_size: number;
  mime_type?: string | null;
}

export interface AttachmentResponse {
  id: number;
  file_hash: string;
  display_name: string;
  file_info: FileInfoShort;
}

export interface BigFileReference {
  message_id: number;
  attachment_id: number;
  display_name: string;
}

export interface BigFileResponse {
  full_hash: string;
  file_size: number;
  mime_type: string | null;
  refer_count: number;
  references: BigFileReference[];
}

export interface FileUploadIntent {
  file_name: string;
  total_size: number;
  sparse_hash: string;
  mime_type?: string | null;
}

export interface MessageCreateRequest {
  content?: string | null;
  type?: number | null; // 0: 纯文本, 1: 混合/带附件
  files?: FileUploadIntent[]; // 多附件支持
  tags?: string[];
}

export interface UploadTaskInfo {
  upload_id: string;
  file_name: string;
}

export interface MessageCreateResponse {
  status: 'created' | 'accepted';
  message_id: number;
  upload_tasks: UploadTaskInfo[];
}

export interface MessageResponse {
  id: number;
  type: number; 
  content: string | null;
  timestamp: number;
  device_name: string;
  device_type: number;
  tags: string[];
  attachments: AttachmentResponse[];
}

export interface ResponseSchema<T> {
  success: boolean;
  code: number;
  message: string;
  data: T | null;
}

export type TimelineMode = 'initial' | 'after' | 'before';

export interface ListMessagesParams {
  mode?: TimelineMode;
  anchor_id?: number | null;
  limit?: number;
  keyword?: string | null;
  hashtag?: string | null;
}

export interface ShareCreateRequest {
  attachment_id: number;
  display_name: string;
  expire_in?: number | null;
  max_uses?: number;
  password?: string | null;
}

export interface ShareCreateResponse {
  share_id: string;
  share_url: string;
  expire_time: number | null;
}

export interface ShareItemResponse {
  share_id: string;
  target_type: string;
  target_payload: string;
  display_name: string | null;
  expire_time: number | null;
  max_uses: number;
  use_count: number;
  created_at: number;
  file_size: number | null;
}
