import { Navigate, Route, Routes } from "react-router-dom";

import { MainLayout } from "@/layouts/MainLayout";
import { useAuthCheck } from "@/services/auth/utils/tokenHelper";
import { PhotoDetail } from "@/services/photo/components/PhotoDetail";
import { PhotoWall } from "@/services/photo/components/PhotoWall";

const App = () => {
  useAuthCheck();

  return (
    <Routes>
      {/* 1. 嵌套路由组：拥有 MainLayout 外壳的页面 */}
      <Route path="/" element={<MainLayout />}>
        <Route index element={<PhotoWall />} />
        {/* <Route path="story" element={<StoryList />} /> */}
      </Route>

      {/* 2. 独立路由组：不需要 MainLayout 外壳的全屏页面 */}
      <Route path="/photo/:id" element={<PhotoDetail />} />

      {/* 3. 兜底路由：404 页面重定向 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
