import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, useNavigate } from "react-router-dom";
import { Provider } from "react-redux";
import { HeroUIProvider } from "@heroui/react";
import { store } from "./app/store.ts";
import App from "./App.tsx";
import "./index.css";

// 一个小技巧：为了让 HeroUI 的内部链接组件能使用 react-router-dom 的跳转
// 我们创建一个 Wrapper 组件来处理 navigate
const HeroUIProviderWithRouter = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const navigate = useNavigate();
  return <HeroUIProvider navigate={navigate}>{children}</HeroUIProvider>;
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* 1. Redux Store: 最底层的数据仓库 */}
    <Provider store={store}>
      {/* 2. Router: 提供 URL 路由能力 */}
      <BrowserRouter>
        {/* 3. UI Library: 依赖 Router (用于 Link 组件) */}
        <HeroUIProviderWithRouter>
          <App />
        </HeroUIProviderWithRouter>
      </BrowserRouter>
    </Provider>
  </StrictMode>
);
