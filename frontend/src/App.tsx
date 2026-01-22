import { Routes, Route, Navigate } from "react-router-dom";

// --- 组件导入 ---
import Login from "./features/auth/components/Login";
import Register from "./features/auth/components/Register";
import Home from "./features/home/Home";

const App = () => {
  return (
    <Routes>
      {/* 首页 */}
      <Route path="/" element={<Home />} />
      {/* 登录页 */}
      <Route path="/login" element={<Login />} />
      {/* 注册页 */}
      <Route path="/register" element={<Register />} />
      {/* 404 页面 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
