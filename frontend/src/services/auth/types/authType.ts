/**
 * 登录请求参数
 * 必须提供 email 或 phone 其中之一
 */
export type LoginRequest = {
  password: string;
  device_id: string;
} & ({ email: string; phone?: undefined } | { email?: undefined; phone: string });

/**
 * 注册请求参数
 */
export interface RegisterRequest {
  name: string;
  email?: string;
  phone?: string;
  password: string;
}

/**
 * 注册响应数据
 */
export interface RegisterResponseData {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  created_at: string;
}

/**
 * 统一响应格式
 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

/**
 * 认证响应（Token 存在 Cookie 中，这里只返回消息）
 */
export interface AuthResponse {
  message: string;
  token_type: string;
}

/**
 * 当前登录用户信息
 */
export interface MeResponseData {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  avatar_key?: string;
}

/**
 * 认证状态
 */
export interface AuthState {
  isAuthenticated: boolean;
  isInitializing: boolean;
}
