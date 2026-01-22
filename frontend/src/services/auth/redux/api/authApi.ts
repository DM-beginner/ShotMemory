import { baseApi } from "@/app/baseApi.ts";
import type {
  LoginRequest,
  AuthResponse,
  RegisterRequest,
  RegisterResponseData,
  ApiResponse
} from "../../types/authType.ts";

/**
 * 认证相关 API
 * - 登录/登出/刷新 Token/注册
 * - Token 存储在 HTTPOnly Cookie 中，前端无法直接访问
 */
export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * 用户注册
     * POST /auth/register
     */
    register: builder.mutation<ApiResponse<RegisterResponseData>, RegisterRequest>({
      query: (userData) => ({
        url: "/auth/register",
        method: "POST",
        body: userData,
      }),
    }),

    /**
     * 用户登录
     * POST /auth/login
     */
    login: builder.mutation<ApiResponse<AuthResponse>, LoginRequest>({
      query: (credentials) => ({
        url: "/auth/login",
        method: "POST",
        body: credentials,
      }),
      invalidatesTags: ["Auth"],
    }),

    /**
     * 刷新 Token
     * POST /auth/refresh
     * Refresh Token 从 Cookie 中自动读取
     */
    refreshToken: builder.mutation<ApiResponse<AuthResponse>, void>({
      query: () => ({
        url: "/auth/refresh",
        method: "POST",
      }),
    }),

    /**
     * 用户登出
     * POST /auth/logout
     * 清除服务端的 Cookie
     */
    logout: builder.mutation<ApiResponse<AuthResponse>, void>({
      query: () => ({
        url: "/auth/logout",
        method: "POST",
      }),
      invalidatesTags: ["Auth", "User"],
    }),
  }),
});

export const {
    useRegisterMutation,
    useLoginMutation,
    useRefreshTokenMutation,
    useLogoutMutation
} = authApi;
