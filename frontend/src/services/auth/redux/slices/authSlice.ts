import { type PayloadAction, createSlice } from "@reduxjs/toolkit";
import type { AuthState } from "../../types/authType";
import { authApi } from "../api/authApi";

const initialState: AuthState = {
  isAuthenticated: false,
  isInitializing: true, // 初始为 true，等待首次认证检查
};
/**
 * authSlice 负责管理认证状态（如是否已认证、是否正在初始化等），
 * 并处理登录、登出、刷新 token 等异步操作的结果，进而更新全局认证相关状态。
 * 这样可以方便地通过 Redux 获取和控制用户的登录状态、初始化状态等信息。
 */

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setAuthenticated: (state, action: PayloadAction<boolean>) => {
      state.isAuthenticated = action.payload;
      state.isInitializing = false;
    },
    setInitializing: (state, action: PayloadAction<boolean>) => {
      state.isInitializing = action.payload;
    },

    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isInitializing = action.payload;
    },

    resetAuth: (state) => {
      state.isAuthenticated = false;
      state.isInitializing = false;
    },
  },
  extraReducers: (builder) => {
    builder.addMatcher(authApi.endpoints.login.matchFulfilled, (state) => {
      state.isAuthenticated = true;
    });

    builder.addMatcher(authApi.endpoints.login.matchRejected, (state) => {
      state.isAuthenticated = false;
    });

    builder.addMatcher(authApi.endpoints.refreshToken.matchFulfilled, (state) => {
      state.isAuthenticated = true;
    });

    builder.addMatcher(authApi.endpoints.refreshToken.matchRejected, (state) => {
      state.isAuthenticated = false;
    });

    builder.addMatcher(authApi.endpoints.logout.matchFulfilled, (state) => {
      state.isAuthenticated = false;
    });

    builder.addMatcher(authApi.endpoints.getMe.matchFulfilled, (state) => {
      state.isAuthenticated = true;
    });

    builder.addMatcher(authApi.endpoints.getMe.matchRejected, (state) => {
      state.isAuthenticated = false;
    });
  },
});

export const { setAuthenticated, setInitializing, setLoading, resetAuth } =
  authSlice.actions;
export default authSlice.reducer;
