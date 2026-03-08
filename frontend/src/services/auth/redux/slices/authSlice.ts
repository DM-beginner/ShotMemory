import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { AuthState } from "../../types/authType";
import { authApi } from "../api/authApi";

/**
 * 认证状态初始值
 * - isAuthenticated: 是否已登录（由 Cookie 存在性决定）
 * - isLoading: 是否正在检查认证状态
 */
const initialState: AuthState = {
  isAuthenticated: false,
  isLoading: true, // 初始为 true，等待首次认证检查
};

/**
 * 认证状态 Slice
 * 注意：Token 存储在 HTTPOnly Cookie 中，前端只维护认证状态
 */
export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    /**
     * 设置认证状态
     */
    setAuthenticated: (state, action: PayloadAction<boolean>) => {
      state.isAuthenticated = action.payload;
      state.isLoading = false;
    },

    /**
     * 设置加载状态
     */
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },

    /**
     * 重置认证状态（用于登出）
     */
    resetAuth: (state) => {
      state.isAuthenticated = false;
      state.isLoading = false;
    },
  },
  extraReducers: (builder) => {
    // 登录成功
    builder.addMatcher(
      authApi.endpoints.login.matchFulfilled,
      (state) => {
        state.isAuthenticated = true;
        state.isLoading = false;
      }
    );

    // 登录失败
    builder.addMatcher(
      authApi.endpoints.login.matchRejected,
      (state) => {
        state.isAuthenticated = false;
        state.isLoading = false;
      }
    );

    // 刷新成功
    builder.addMatcher(
      authApi.endpoints.refreshToken.matchFulfilled,
      (state) => {
        state.isAuthenticated = true;
        state.isLoading = false;
      }
    );

    // 刷新失败（token 完全过期）
    builder.addMatcher(
      authApi.endpoints.refreshToken.matchRejected,
      (state) => {
        state.isAuthenticated = false;
        state.isLoading = false;
      }
    );

    // 登出成功
    builder.addMatcher(
      authApi.endpoints.logout.matchFulfilled,
      (state) => {
        state.isAuthenticated = false;
        state.isLoading = false;
      }
    );
  },
});

export const { setAuthenticated, setLoading, resetAuth } = authSlice.actions;
export default authSlice.reducer;
