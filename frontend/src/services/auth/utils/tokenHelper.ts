/**
 * 设备 ID 管理工具
 * - 用于在登录时标识设备边界，防止 Refresh Token 跨设备重放攻击
 * - 配合 HTTPOnly Cookie 使用
 */

const DEVICE_ID_KEY = "shotmemory_device_id";

/**
 * 生成极其安全的 UUID v4
 */
function generateSecureUUID(): string {
  // 🌟 现代浏览器首选：原生密码学级别的 UUID 生成器
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  // 🛡️ 兼容性降级：使用 getRandomValues 替代不安全的 Math.random()
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
      (
        Number(c) ^
        (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (Number(c) / 4)))
      ).toString(16)
    );
  }

  // ⚠️ 终极降级（基本不会触发，除非在极老旧或非 HTTPS 环境）
  console.warn("[ShotMemory Auth] 警告：当前环境不支持 Web Crypto API，退化为伪随机 UUID");
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
    deviceId = generateSecureUUID();
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }

  return deviceId;
}

/**
 * 清除设备ID
 * ⚠️ 注意：通常不需要调用此方法！
 * 因为即使注销登录，这台物理设备依然是这台物理设备。
 * 除非你想彻底“伪装”成一台新设备，才会清除它。
 */
export function clearDeviceId(): void {
  localStorage.removeItem(DEVICE_ID_KEY);
}