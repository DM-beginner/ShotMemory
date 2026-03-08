import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Card, CardHeader, CardBody, Button } from "@heroui/react";
import { useLogoutMutation } from "@/services/auth/redux/api/authApi";

// 地球图标
const EarthIcon = () => (
  <svg
    className="w-10 h-10"
    viewBox="0 0 24 24"
    fill="none"
    stroke="url(#earthGradientHome)"
    strokeWidth={1.5}
  >
    <defs>
      <linearGradient
        id="earthGradientHome"
        x1="0%"
        y1="0%"
        x2="100%"
        y2="100%"
      >
        <stop offset="0%" stopColor="#22d3ee" />
        <stop offset="100%" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

// 登出图标
const LogoutIcon = () => (
  <svg
    className="w-5 h-5"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
    />
  </svg>
);

// 相机图标
const CameraIcon = () => (
  <svg
    className="w-6 h-6"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
    />
  </svg>
);

// 地图图标
const MapIcon = () => (
  <svg
    className="w-6 h-6"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
    />
  </svg>
);

// 相册图标
const GalleryIcon = () => (
  <svg
    className="w-6 h-6"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
    />
  </svg>
);

const Home = () => {
  const navigate = useNavigate();
  const [logout, { isLoading: isLoggingOut }] = useLogoutMutation();

  const handleLogout = async () => {
    try {
      await logout().unwrap();
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
      // 即使登出失败也跳转到登录页
      navigate("/login");
    }
  };

  // 功能卡片数据
  const features = [
    {
      icon: <CameraIcon />,
      title: "记录瞬间",
      description: "拍摄或上传照片，记录每一个美好时刻",
      color: "cyan",
    },
    {
      icon: <MapIcon />,
      title: "探索地图",
      description: "在世界地图上查看你的足迹轨迹",
      color: "violet",
    },
    {
      icon: <GalleryIcon />,
      title: "回忆相册",
      description: "按时间线浏览所有珍贵回忆",
      color: "emerald",
    },
  ];

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-slate-900 py-8">
      {/* 背景渐变光晕 */}
      <div className="absolute inset-0 overflow-hidden">
        {/* 主光晕 - 青色 */}
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-cyan-500/20 rounded-full blur-[120px]" />
        {/* 次光晕 - 紫色 */}
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-violet-500/20 rounded-full blur-[120px]" />
        {/* 中心光晕 */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-radial from-cyan-500/5 via-transparent to-transparent rounded-full" />
      </div>

      {/* 网格背景 */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
        }}
      />

      {/* 主卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 w-full max-w-2xl mx-4"
      >
        <Card className="bg-slate-800/60 backdrop-blur-xl border border-slate-700/50 shadow-2xl shadow-cyan-500/5">
          {/* 卡片头部 */}
          <CardHeader className="flex flex-col items-center gap-3 pt-8 pb-4 relative">
            {/* 退出登录按钮 - 右上角 */}
            <Button
              variant="light"
              size="sm"
              isLoading={isLoggingOut}
              onPress={handleLogout}
              className="absolute top-4 right-4 text-slate-400 hover:text-rose-400 transition-colors min-w-0"
              startContent={!isLoggingOut && <LogoutIcon />}
            >
              {isLoggingOut ? "" : "退出"}
            </Button>

            {/* Logo */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.4 }}
              className="p-3 rounded-2xl bg-linear-to-br from-cyan-500/10 to-violet-500/10 border border-slate-600/30"
            >
              <EarthIcon />
            </motion.div>

            {/* 标题 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-center"
            >
              <h1 className="text-2xl font-semibold bg-linear-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
                欢迎回来
              </h1>
              <p className="text-slate-400 text-sm mt-1">
                准备好记录你的地球足迹了吗？
              </p>
            </motion.div>
          </CardHeader>

          {/* 卡片内容 */}
          <CardBody className="px-6 pb-8">
            <div className="space-y-6">
              {/* 功能卡片区域 */}
              {features.map((feature, index) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + index * 0.1 }}
                >
                  <Card
                    isPressable
                    className="bg-slate-700/30 backdrop-blur-sm border border-slate-600/30 hover:border-slate-500/50 transition-all duration-300 hover:scale-[1.02]"
                  >
                    <CardBody className="p-5">
                      <div className="flex items-start gap-4">
                        <div
                          className={`shrink-0 w-12 h-12 rounded-xl flex items-center justify-center ${
                            feature.color === "cyan"
                              ? "bg-cyan-500/10 text-cyan-400"
                              : feature.color === "violet"
                              ? "bg-violet-500/10 text-violet-400"
                              : "bg-emerald-500/10 text-emerald-400"
                          }`}
                        >
                          {feature.icon}
                        </div>
                        <div className="flex-1">
                          <h3 className="text-base font-semibold text-white mb-1">
                            {feature.title}
                          </h3>
                          <p className="text-slate-400 text-sm">
                            {feature.description}
                          </p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                </motion.div>
              ))}

              {/* 底部提示 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="text-center pt-2"
              >
                <p className="text-slate-500 text-xs">
                  功能正在建设中，敬请期待...
                </p>
              </motion.div>
            </div>
          </CardBody>
        </Card>

        {/* 底部版权 */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-center text-slate-500 text-xs mt-6"
        >
          © 2026 Earth Diary · 记录世界的每一刻
        </motion.p>
      </motion.div>
    </div>
  );
};

export default Home;
