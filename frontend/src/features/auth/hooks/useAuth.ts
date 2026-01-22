import { useCallback } from "react";
import { useSelector } from "react-redux";
import type { RootState } from "@/app/store";
import {
  useLoginMutation,
  useLogoutMutation,
  useRefreshTokenMutation,
} from "@/services/auth";
import type { LoginRequest } from "@/services/auth";

/**
 * 认证相关 Hook
 * 封装登录、登出、刷新 Token 等操作
 */
export function useAuth() {
  // 从 Redux 获取认证状态
  const { isAuthenticated, isLoading } = useSelector(
    (state: RootState) => state.auth
  );

  // RTK Query mutations
  const [loginMutation, { isLoading: isLoginLoading }] = useLoginMutation();
  const [logoutMutation, { isLoading: isLogoutLoading }] = useLogoutMutation();
  const [refreshMutation] = useRefreshTokenMutation();

  /**
   * 登录
   */
  const login = useCallback(
    async (credentials: LoginRequest) => {
      try {
        await loginMutation(credentials).unwrap();
        return { success: true };
      } catch (error) {
        console.error("Login failed:", error);
        return { success: false, error };
      }
    },
    [loginMutation]
  );

  /**
   * 登出
   */
  const logout = useCallback(async () => {
    try {
      await logoutMutation().unwrap();
      return { success: true };
    } catch (error) {
      console.error("Logout failed:", error);
      return { success: false, error };
    }
  }, [logoutMutation]);

  /**
   * 手动刷新 Token
   * 通常不需要手动调用，baseApi 会自动处理
   */
  const refresh = useCallback(async () => {
    try {
      await refreshMutation().unwrap();
      return { success: true };
    } catch (error) {
      console.error("Token refresh failed:", error);
      return { success: false, error };
    }
  }, [refreshMutation]);

  return {
    // 状态
    isAuthenticated,
    isLoading: isLoading || isLoginLoading || isLogoutLoading,

    // 操作
    login,
    logout,
    refresh,
  };
}
