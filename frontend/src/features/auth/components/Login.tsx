import { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Card,
  CardBody,
  CardHeader,
  Input,
  Button,
  Tabs,
  Tab,
} from "@heroui/react";
import { useLoginMutation } from "@/services/auth/redux/api/authApi";
import type { LoginRequest } from "@/services/auth/types/authType";

// 图标组件
const PhoneIcon = () => (
  <svg
    className="w-5 h-5 text-cyan-400"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
    />
  </svg>
);

const EmailIcon = () => (
  <svg
    className="w-5 h-5 text-violet-400"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
    />
  </svg>
);

const LockIcon = () => (
  <svg
    className="w-5 h-5 text-slate-400"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
    />
  </svg>
);

const EyeIcon = () => (
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
      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
    />
  </svg>
);

const EyeOffIcon = () => (
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
      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
    />
  </svg>
);

const EarthIcon = () => (
  <svg
    className="w-10 h-10"
    viewBox="0 0 24 24"
    fill="none"
    stroke="url(#earthGradient)"
    strokeWidth={1.5}
  >
    <defs>
      <linearGradient id="earthGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#22d3ee" />
        <stop offset="100%" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

type LoginType = "phone" | "email";

const Login = () => {
  const navigate = useNavigate();
  const [login, { isLoading }] = useLoginMutation();

  // 表单状态
  const [loginType, setLoginType] = useState<LoginType>("phone");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  // 验证手机号（中国大陆）
  const validatePhone = (value: string) => {
    const phoneRegex = /^1[3-9]\d{9}$/;
    return phoneRegex.test(value);
  };

  // 验证邮箱
  const validateEmail = (value: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
  };

  // 手机号验证状态
  const phoneValidation = useMemo(() => {
    if (!phone) return { isInvalid: false, errorMessage: "" };
    const isValid = validatePhone(phone);
    return {
      isInvalid: !isValid,
      errorMessage: isValid ? "" : "请输入正确的手机号码",
    };
  }, [phone]);

  // 邮箱验证状态
  const emailValidation = useMemo(() => {
    if (!email) return { isInvalid: false, errorMessage: "" };
    const isValid = validateEmail(email);
    return {
      isInvalid: !isValid,
      errorMessage: isValid ? "" : "请输入正确的邮箱地址",
    };
  }, [email]);

  // 生成设备ID
  const getDeviceId = () => {
    let deviceId = localStorage.getItem("device_id");
    if (!deviceId) {
      deviceId = crypto.randomUUID();
      localStorage.setItem("device_id", deviceId);
    }
    return deviceId;
  };

  // 提交登录
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // 验证表单
    const accountValue = loginType === "phone" ? phone : email;
    if (!accountValue) {
      setError(loginType === "phone" ? "请输入手机号" : "请输入邮箱");
      return;
    }

    if (loginType === "phone" && !validatePhone(phone)) {
      setError("请输入正确的手机号码");
      return;
    }

    if (loginType === "email" && !validateEmail(email)) {
      setError("请输入正确的邮箱地址");
      return;
    }

    if (!password) {
      setError("请输入密码");
      return;
    }

    if (password.length < 6) {
      setError("密码长度不能少于6位");
      return;
    }

    try {
      // 根据登录类型构建请求体，确保只有一个字段有值
      const login_body: LoginRequest =
        loginType === "phone"
          ? {
              phone: accountValue,
              password,
              device_id: getDeviceId(),
            }
          : {
              email: accountValue,
              password,
              device_id: getDeviceId(),
            };
      await login(login_body).unwrap();

      // 登录成功，跳转到首页
      navigate("/");
    } catch (err: unknown) {
      const error = err as { data?: { message?: string } };
      setError(error?.data?.message || "登录失败，请检查账号和密码");
    }
  };

  // 切换登录类型时清除错误
  const handleTabChange = (key: React.Key) => {
    setLoginType(key as LoginType);
    setError("");
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-slate-900">
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

      {/* 登录卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        <Card className="bg-slate-800/60 backdrop-blur-xl border border-slate-700/50 shadow-2xl shadow-cyan-500/5">
          <CardHeader className="flex flex-col items-center gap-3 pt-8 pb-2">
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
                Earth Diary
              </h1>
              <p className="text-slate-400 text-sm mt-1">记录你的地球足迹</p>
            </motion.div>
          </CardHeader>

          <CardBody className="px-6 pb-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Tab 切换 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                <Tabs
                  fullWidth
                  selectedKey={loginType}
                  onSelectionChange={handleTabChange}
                  classNames={{
                    tabList:
                      "bg-slate-700/50 border border-slate-600/30 rounded-xl p-1",
                    cursor:
                      "bg-gradient-to-r from-cyan-500/80 to-violet-500/80",
                    tab: "text-slate-400 data-[selected=true]:text-white font-medium",
                    tabContent: "group-data-[selected=true]:text-white",
                  }}
                >
                  <Tab
                    key="phone"
                    title={
                      <div className="flex items-center gap-2">
                        <PhoneIcon />
                        <span>手机号登录</span>
                      </div>
                    }
                  />
                  <Tab
                    key="email"
                    title={
                      <div className="flex items-center gap-2">
                        <EmailIcon />
                        <span>邮箱登录</span>
                      </div>
                    }
                  />
                </Tabs>
              </motion.div>

              {/* 输入框区域 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="space-y-4"
              >
                {/* 手机号/邮箱输入框 */}
                {loginType === "phone" ? (
                  <Input
                    type="tel"
                    label="手机号"
                    placeholder="请输入手机号"
                    value={phone}
                    onValueChange={setPhone}
                    isInvalid={phoneValidation.isInvalid}
                    errorMessage={phoneValidation.errorMessage}
                    startContent={<PhoneIcon />}
                    classNames={{
                      input: "text-white placeholder:text-slate-500",
                      inputWrapper:
                        "bg-slate-700/50 border-slate-600/50 hover:border-cyan-500/50 focus-within:border-cyan-500 group-data-[focus=true]:border-cyan-500",
                      label: "text-slate-400",
                      errorMessage: "text-rose-400",
                    }}
                    variant="bordered"
                  />
                ) : (
                  <Input
                    type="email"
                    label="邮箱"
                    placeholder="请输入邮箱地址"
                    value={email}
                    onValueChange={setEmail}
                    isInvalid={emailValidation.isInvalid}
                    errorMessage={emailValidation.errorMessage}
                    startContent={<EmailIcon />}
                    classNames={{
                      input: "text-white placeholder:text-slate-500",
                      inputWrapper:
                        "bg-slate-700/50 border-slate-600/50 hover:border-violet-500/50 focus-within:border-violet-500 group-data-[focus=true]:border-violet-500",
                      label: "text-slate-400",
                      errorMessage: "text-rose-400",
                    }}
                    variant="bordered"
                  />
                )}

                {/* 密码输入框 */}
                <Input
                  type={showPassword ? "text" : "password"}
                  label="密码"
                  placeholder="请输入密码"
                  value={password}
                  onValueChange={setPassword}
                  startContent={<LockIcon />}
                  endContent={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="text-slate-400 hover:text-slate-200 transition-colors focus:outline-none"
                    >
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  }
                  classNames={{
                    input: "text-white placeholder:text-slate-500",
                    inputWrapper:
                      "bg-slate-700/50 border-slate-600/50 hover:border-slate-500/50 focus-within:border-cyan-500 group-data-[focus=true]:border-cyan-500",
                    label: "text-slate-400",
                  }}
                  variant="bordered"
                />
              </motion.div>

              {/* 错误提示 */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20"
                >
                  <p className="text-rose-400 text-sm text-center">{error}</p>
                </motion.div>
              )}

              {/* 登录按钮 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
              >
                <Button
                  type="submit"
                  isLoading={isLoading}
                  className="w-full h-12 bg-linear-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold text-base shadow-lg shadow-cyan-500/20 transition-all duration-300 hover:shadow-cyan-500/30 hover:scale-[1.02]"
                >
                  {isLoading ? "登录中..." : "登 录"}
                </Button>
              </motion.div>

              {/* 注册入口 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="text-center pt-2"
              >
                <span className="text-slate-400 text-sm">还没有账号？</span>
                <Link
                  to="/register"
                  className="text-cyan-400 hover:text-cyan-300 text-sm font-medium ml-1 transition-colors hover:underline underline-offset-4"
                >
                  立即注册
                </Link>
              </motion.div>
            </form>
          </CardBody>
        </Card>

        {/* 底部装饰文字 */}
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

export default Login;
