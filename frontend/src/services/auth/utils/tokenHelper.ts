/**
 * 设备ID管理工具
 * - 用于在登录时标识设备
 * - Token 已改为 HTTPOnly Cookie 方式，前端无法直接访问
 */

const DEVICE_ID_KEY = "earth_diary_device_id";

/**
 * 生成 UUID v4
 */
function generateUUID(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * 获取或创建设备ID
 * - 如果本地存储中有设备ID，则返回
 * - 如果没有，则生成一个新的并存储
 */
export function getDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);

  if (!deviceId) {
    deviceId = generateUUID();
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }

  return deviceId;
}

/**
 * 清除设备ID（用于完全注销设备）
 */
export function clearDeviceId(): void {
  localStorage.removeItem(DEVICE_ID_KEY);
}
