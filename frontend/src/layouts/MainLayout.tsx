import { Header } from "@/layouts/Header";
import { Outlet } from "react-router-dom";

export const MainLayout = () => (
  <div className="flex flex-col min-h-screen">
    <Header /> {/* 你的 HeroUI 导航栏 */}
    <main className="w-full">
      <Outlet /> {/* 这里会渲染具体的路由页面 */}
    </main>
  </div>
);
