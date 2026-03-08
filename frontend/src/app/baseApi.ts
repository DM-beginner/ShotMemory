import {
  createApi,
  fetchBaseQuery,
  type BaseQueryFn,
  type FetchArgs,
  type FetchBaseQueryError,
} from "@reduxjs/toolkit/query/react";

const host = import.meta.env.VITE_BACKEND_HOST || "";
const prefix = import.meta.env.VITE_BACKEND_PREFIX || "/v1";

/**
 * 基础 Query 配置
 * - credentials: 'include' 确保跨域请求携带 Cookie
 */
const baseQuery = fetchBaseQuery({
  baseUrl: `${host}${prefix}`,
  credentials: "include", // 🔐 关键：携带 HTTPOnly Cookie
});

/**
 * 带自动刷新的 BaseQuery
 * 当 access_token 过期时，自动调用 /auth/refresh 获取新 token
 */
const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await baseQuery(args, api, extraOptions);

  // 检查是否是 401 且 token 过期
  if (result.error && result.error.status === 401) {
    const errorData = result.error.data as { detail?: string } | undefined;

    // 只有 token 过期才尝试刷新，其他 401 错误直接返回
    if (errorData?.detail === "Token expired") {
      console.log("🔄 Access token expired, attempting refresh...");

      // 尝试刷新 token
      const refreshResult = await baseQuery(
        { url: "/auth/refresh", method: "POST" },
        api,
        extraOptions
      );

      if (refreshResult.data) {
        // 刷新成功，重试原请求
        console.log("✅ Token refreshed successfully, retrying request...");
        result = await baseQuery(args, api, extraOptions);
      } else {
        // 刷新失败，需要重新登录
        console.log("❌ Token refresh failed, user needs to re-login");
        // 可以在这里 dispatch 一个 logout action
        // api.dispatch(authSlice.actions.logout());
      }
    }
  }

  return result;
};

/**
 * RTK Query API 基础配置
 * 所有 feature 的 API 都从这里 injectEndpoints
 */
export const baseApi = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithReauth,
  tagTypes: ["User", "Auth"],
  endpoints: () => ({}),
});
