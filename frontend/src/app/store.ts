import { configureStore } from "@reduxjs/toolkit";
import { baseApi } from "./baseApi";
import authReducer from "@/services/auth/redux/slices/authSlice";

export const store = configureStore({
  reducer: {
    // RTK Query API reducer
    [baseApi.reducerPath]: baseApi.reducer,
    // Auth state
    auth: authReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(baseApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
