import App from "@/App";
import { store } from "@/app/store";
import { HeroUIProvider } from "@heroui/react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { BrowserRouter, useNavigate } from "react-router-dom";
import "@/styles/global.css";

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

const rootElement = document.getElementById("root");

if (!rootElement) {
  // 2. 严谨的空值校验 (Type Guard)
  // 如果找不到，抛出明确的错误，方便后续错误监控系统捕获
  throw new Error("Failed to find the root element. Please check your index.html");
}
createRoot(rootElement).render(
  <StrictMode>
    {/* 1. Redux Store: 最底层的数据仓库 */}
    <Provider store={store}>
      {/* 2. Router: 提供 URL 路由能力 */}
      <BrowserRouter>
        {/* 3. UI Library: 依赖 Router (用于 Link 组件) */}
        <HeroUIProviderWithRouter>
          {/* attribute="class" 告诉它通过切换 class 来控制主题，这完美契合 Tailwind */}
          {/* defaultTheme="system" 可以让它默认跟随用户的操作系统颜色 */}
          <NextThemesProvider attribute="class" defaultTheme="system">
            <App />
          </NextThemesProvider>
        </HeroUIProviderWithRouter>
      </BrowserRouter>
    </Provider>
  </StrictMode>
);
