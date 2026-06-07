import client from "./client";

export const AuthService = {
  login: (data) => client.post("/auth/login", data),

  register: (data) => client.post("/auth/register", data),

  logout: (token) => client.post("/auth/logout", { bearer: token }),

  me: () => client.get("/auth/me"),

  updateSettings: (data) => client.put("/auth/settings", data),

  listDevices: () => client.get("/auth/devices"),

  revokeDevice: (deviceId) => client.delete(`/auth/devices/${deviceId}`),

  updateDevice: (data) => client.put("/auth/device", data),
};

export const MessageService = {
  list: (params) => client.get("/messages", { params }),

  /**
   * 模拟获取单条：由于后端未提供 GET /messages/{id}，通过 list 接口定位锚点实现
   */
  getOne: async (id) => {
    return client
      .get("/messages", {
        params: { mode: "initial", anchor_id: id, limit: 1 },
      })
      .then((res) => {
        // 适配层：在返回的列表中精准匹配目标 ID
        const list = res.data.data || [];
        const target = list.find((m) => m.id === id) || null;
        return {
          ...res,
          data: {
            ...res.data,
            data: target,
          },
        };
      });
  },

  create: (data) => client.post("/messages", data),

  delete: (id) => client.delete(`/messages/${id}`),

  restore: (id) => client.post(`/messages/${id}/restore`),

  getTrash: () => client.get("/messages/trash"),

  emptyTrash: () => client.delete("/messages/trash/empty"),
};

export const FileService = {
  uploadChunk: (uploadId, chunk, fullHash) => {
    const headers = { "Content-Type": "application/octet-stream" };
    if (fullHash) headers["X-Full-Hash"] = fullHash;
    return client.patch(`/files/upload/${uploadId}`, chunk, { headers });
  },

  commit: (uploadId, fullHash) =>
    client.post(`/files/upload/${uploadId}/commit`, null, {
      headers: { "X-Full-Hash": fullHash },
    }),

  download: (attachmentId) =>
    client.get(`/files/attachments/${attachmentId}/download`, {
      responseType: "blob",
    }),

  getThumbnail: (attachmentId) =>
    client.get(`/files/attachments/${attachmentId}/thumbnail`, {
      responseType: "blob",
    }),

  getLargeFiles: (limit = 20) =>
    client.get("/files/large", { params: { limit } }),

  detachAttachment: (messageId, attachmentId) =>
    client.delete(`/files/messages/${messageId}/attachments/${attachmentId}`),
};

export const ShareService = {
  create: (data) => client.post("/share/file", data),

  list: () => client.get("/share/list"),

  revoke: (shareId) => client.delete(`/share/${shareId}`),

  download: (shareId, password) =>
    client.get(`/share/${shareId}`, {
      params: { pwd: password || null },
      responseType: "blob",
    }),
};

export const SystemService = {
  status: () => client.get("/system/status"),
  setup: (data) => client.post("/system/setup", data),
};

export const ManageService = {
  getSettings: () => client.get("/manage/settings"),
  updateSettings: (data) => client.put("/manage/settings", data),
  listUsers: () => client.get("/manage/users"),
  updateUserQuota: (userUuid, data) =>
    client.put(`/manage/users/${userUuid}/quota`, data),
  updateUserStatus: (userUuid, data) =>
    client.put(`/manage/users/${userUuid}/status`, data),
  deleteUser: (userUuid) => client.delete(`/manage/users/${userUuid}`),
  factoryReset: (data) => client.post("/manage/factory_reset", data),
};
