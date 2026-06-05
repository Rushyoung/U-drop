import client from './client';
import type { 
  LoginRequest, 
  LoginResponse, 
  MessageCreateRequest, 
  MessageCreateResponse, 
  MessageResponse, 
  ResponseSchema,
  ListMessagesParams,
  ShareCreateRequest,
  ShareCreateResponse,
  ShareItemResponse,
  UserPublic,
  UserSettingsUpdate,
  DeviceUpdateRequest,
  SystemStatusResponse,
  SystemSetupRequest,
  SystemSettingsUpdateRequest,
  UserManageResponse,
  UserQuotaUpdateRequest,
  UserStatusUpdateRequest,
  FactoryResetRequest,
  BigFileResponse,
  DeviceResponse
} from '../types/api';

export const AuthService = {
  login: (data: LoginRequest) => 
    client.post<ResponseSchema<LoginResponse>>('/auth/login', data),
  
  register: (data: LoginRequest) => 
    client.post<ResponseSchema<LoginResponse>>('/auth/register', data),

  logout: (token: string) =>
    client.post<ResponseSchema<null>>('/auth/logout', { bearer: token }),

  me: () =>
    client.get<ResponseSchema<UserPublic>>('/auth/me'),

  updateSettings: (data: UserSettingsUpdate) =>
    client.put<ResponseSchema<null>>('/auth/settings', data),

  listDevices: () =>
    client.get<ResponseSchema<DeviceResponse[]>>('/auth/devices'),

  revokeDevice: (deviceId: string) =>
    client.delete<ResponseSchema<null>>(`/auth/devices/${deviceId}`),

  updateDevice: (data: DeviceUpdateRequest) =>
    client.put<ResponseSchema<null>>('/auth/device', data),
};

export const MessageService = {
  list: (params: ListMessagesParams) =>
    client.get<ResponseSchema<MessageResponse[]>>('/messages', { params }),
  
  /**
   * 模拟获取单条：由于后端未提供 GET /messages/{id}，通过 list 接口定位锚点实现
   */
  getOne: async (id: number) => {
    return client.get<ResponseSchema<MessageResponse[]>>('/messages', { 
      params: { mode: 'initial', anchor_id: id, limit: 1 } 
    }).then(res => {
      // 适配层：在返回的列表中精准匹配目标 ID
      const list = res.data.data || [];
      const target = list.find(m => m.id === id) || null;
      return {
        ...res,
        data: {
          ...res.data,
          data: target as any
        }
      };
    });
  },

  create: (data: MessageCreateRequest) =>
    client.post<ResponseSchema<MessageCreateResponse>>('/messages', data),

  delete: (id: number) =>
    client.delete<ResponseSchema<null>>(`/messages/${id}`),

  restore: (id: number) =>
    client.post<ResponseSchema<null>>(`/messages/${id}/restore`),

  getTrash: () =>
    client.get<ResponseSchema<MessageResponse[]>>('/messages/trash'),

  emptyTrash: () =>
    client.delete<ResponseSchema<null>>('/messages/trash/empty'),
};

export const FileService = {
  uploadChunk: (uploadId: string, chunk: Blob, fullHash?: string) => {
    const headers: any = { 'Content-Type': 'application/octet-stream' };
    if (fullHash) headers['X-Full-Hash'] = fullHash;
    return client.patch<ResponseSchema<any>>(`/files/upload/${uploadId}`, chunk, { headers });
  },

  commit: (uploadId: string, fullHash: string) =>
    client.post<ResponseSchema<any>>(`/files/upload/${uploadId}/commit`, null, {
      headers: { 'X-Full-Hash': fullHash }
    }),

  download: (attachmentId: number) =>
    client.get(`/files/attachments/${attachmentId}/download`, { responseType: 'blob' }),

  getThumbnail: (attachmentId: number) =>
    client.get(`/files/attachments/${attachmentId}/thumbnail`, { responseType: 'blob' }),

  getLargeFiles: (limit: number = 20) =>
    client.get<ResponseSchema<BigFileResponse[]>>('/files/large', { params: { limit } }),

  detachAttachment: (messageId: number, attachmentId: number) =>
    client.delete<ResponseSchema<null>>(`/files/messages/${messageId}/attachments/${attachmentId}`),
};

export const ShareService = {
  create: (data: ShareCreateRequest) =>
    client.post<ResponseSchema<ShareCreateResponse>>('/share/file', data),

  list: () =>
    client.get<ResponseSchema<ShareItemResponse[]>>('/share/list'),

  revoke: (shareId: string) =>
    client.delete<ResponseSchema<null>>(`/share/${shareId}`),

  download: (shareId: string, password?: string) =>
    client.get(`/share/${shareId}`, { 
      params: { pwd: password || null },
      responseType: 'blob' 
    }),
};

export const SystemService = {
  status: () => 
    client.get<ResponseSchema<SystemStatusResponse>>('/system/status'),
  setup: (data: SystemSetupRequest) =>
    client.post<ResponseSchema<null>>('/system/setup', data),
};

export const ManageService = {
  getSettings: () =>
    client.get<ResponseSchema<any>>('/manage/settings'),
  updateSettings: (data: SystemSettingsUpdateRequest) =>
    client.put<ResponseSchema<null>>('/manage/settings', data),
  listUsers: () =>
    client.get<ResponseSchema<UserManageResponse[]>>('/manage/users'),
  updateUserQuota: (userUuid: string, data: UserQuotaUpdateRequest) =>
    client.put<ResponseSchema<null>>(`/manage/users/${userUuid}/quota`, data),
  updateUserStatus: (userUuid: string, data: UserStatusUpdateRequest) =>
    client.put<ResponseSchema<null>>(`/manage/users/${userUuid}/status`, data),
  deleteUser: (userUuid: string) =>
    client.delete<ResponseSchema<null>>(`/manage/users/${userUuid}`),
  factoryReset: (data: FactoryResetRequest) =>
    client.post<ResponseSchema<null>>('/manage/factory_reset', data),
};
