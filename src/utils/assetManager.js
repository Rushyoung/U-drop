const assetCache = new Map();

/**
 * 获取缓存的资源 URL，如果不存在则返回 null
 */
export function getCachedAsset(hash) {
  return assetCache.get(hash)?.url || null;
}

/**
 * 将 Blob 存入缓存并生成 URL
 */
export function cacheAsset(hash, blob) {
  // 如果已存在，先清理旧的
  const existing = assetCache.get(hash);
  if (existing) {
    URL.revokeObjectURL(existing.url);
  }
  
  const url = URL.createObjectURL(blob);
  assetCache.set(hash, { url, blob });
  return url;
}

/**
 * 清理所有缓存资源并释放 URL
 */
export function clearAssetCache() {
  assetCache.forEach((asset) => {
    URL.revokeObjectURL(asset.url);
  });
  assetCache.clear();
  console.log('[Asset Manager] All cached assets cleared.');
}
