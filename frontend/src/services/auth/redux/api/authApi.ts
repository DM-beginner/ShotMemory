import { baseApi } from "@/app/baseApi.ts";
import type {
  ApiResponse,
  AuthResponse,
  LoginRequest,
  MeResponseData,
  RegisterRequest,
  RegisterResponseData,
} from "../../types/authType.ts";

/**
 * 认证相关 API
 * - 登录/登出/刷新 Token/注册
 * - Token 存储在 HTTPOnly Cookie 中，前端无法直接访问
 */
export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    register: builder.mutation<ApiResponse<RegisterResponseData>, RegisterRequest>({
      query: (userData) => ({
        url: "/auth/register",
        method: "POST",
        body: userData,
      }),
    }),

    login: builder.mutation<ApiResponse<AuthResponse>, LoginRequest>({
      query: (credentials) => ({
        url: "/auth/login",
        method: "POST",
        body: credentials,
      }),
      invalidatesTags: ["Auth", "Photo"],
    }),

    refreshToken: builder.mutation<ApiResponse<AuthResponse>, void>({
      query: () => ({
        url: "/auth/refresh",
        method: "POST",
      }),
    }),

    logout: builder.mutation<ApiResponse<AuthResponse>, void>({
      query: () => ({
        url: "/auth/logout",
        method: "POST",
      }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        await queryFulfilled;
        // 清空整个 RTK Query 缓存，防止退出后残留照片等数据
        dispatch(baseApi.util.resetApiState());
      },
    }),

    getMe: builder.query<ApiResponse<MeResponseData>, void>({
      query: () => ({
        url: "/auth/me",
        method: "GET",
      }),
      providesTags: ["Auth"],
    }),

    uploadAvatar: builder.mutation<ApiResponse<MeResponseData>, FormData>({
      query: (body) => ({
        url: "/auth/avatar",
        method: "PUT",
        body,
      }),
      invalidatesTags: ["Auth"],
    }),
  }),
});

export const {
  useRegisterMutation,
  useLoginMutation,
  useRefreshTokenMutation,
  useLogoutMutation,
  useUploadAvatarMutation,
} = authApi;
