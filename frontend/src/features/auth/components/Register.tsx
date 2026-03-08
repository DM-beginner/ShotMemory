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
  Checkbox,
} from "@heroui/react";
import { useRegisterMutation } from "@/services/auth/redux/api/authApi";

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

const UserIcon = () => (
  <svg
    className="w-5 h-5 text-emerald-400"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
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
    stroke="url(#earthGradientReg)"
    strokeWidth={1.5}
  >
    <defs>
      <linearGradient id="earthGradientReg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#22d3ee" />
        <stop offset="100%" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

const CheckIcon = () => (
  <svg
    className="w-4 h-4"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M5 13l4 4L19 7"
    />
  </svg>
);

type RegisterType = "phone" | "email";

const Register = () => {
  const navigate = useNavigate();
  const [register, { isLoading }] = useRegisterMutation();

  // 表单状态
  const [registerType, setRegisterType] = useState<RegisterType>("phone");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState("");

  // 验证用户名
  const validateName = (value: string) => {
    return value.length >= 2 && value.length <= 20;
  };

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

  // 验证密码强度
  const validatePassword = (value: string) => {
    return value.length >= 6;
  };

  // 用户名验证状态
  const nameValidation = useMemo(() => {
    if (!name) return { isInvalid: false, errorMessage: "" };
    const isValid = validateName(name);
    return {
      isInvalid: !isValid,
      errorMessage: isValid ? "" : "用户名长度需要在2-20个字符之间",
    };
  }, [name]);

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

  // 密码验证状态
  const passwordValidation = useMemo(() => {
    if (!password) return { isInvalid: false, errorMessage: "" };
    const isValid = validatePassword(password);
    return {
      isInvalid: !isValid,
      errorMessage: isValid ? "" : "密码长度不能少于6位",
    };
  }, [password]);

  // 确认密码验证状态
  const confirmPasswordValidation = useMemo(() => {
    if (!confirmPassword) return { isInvalid: false, errorMessage: "" };
    const isValid = confirmPassword === password;
    return {
      isInvalid: !isValid,
      errorMessage: isValid ? "" : "两次输入的密码不一致",
    };
  }, [confirmPassword, password]);

  // 提交注册
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // 验证用户名
    if (!name) {
      setError("请输入用户名");
      return;
    }
    if (!validateName(name)) {
      setError("用户名长度需要在2-20个字符之间");
      return;
    }

    // 验证手机号/邮箱
    const accountValue = registerType === "phone" ? phone : email;
    if (!accountValue) {
      setError(registerType === "phone" ? "请输入手机号" : "请输入邮箱");
      return;
    }

    if (registerType === "phone" && !validatePhone(phone)) {
      setError("请输入正确的手机号码");
      return;
    }

    if (registerType === "email" && !validateEmail(email)) {
      setError("请输入正确的邮箱地址");
      return;
    }

    // 验证密码
    if (!password) {
      setError("请输入密码");
      return;
    }
    if (!validatePassword(password)) {
      setError("密码长度不能少于6位");
      return;
    }

    // 验证确认密码
    if (!confirmPassword) {
      setError("请确认密码");
      return;
    }
    if (confirmPassword !== password) {
      setError("两次输入的密码不一致");
      return;
    }

    // 验证用户协议
    if (!agreedToTerms) {
      setError("请阅读并同意用户协议");
      return;
    }

    try {
      // 构建注册请求
      const registerData =
        registerType === "phone"
          ? { name, phone, password }
          : { name, email, password };

      await register(registerData).unwrap();

      // 注册成功，跳转到登录页
      navigate("/login", {
        state: { message: "注册成功，请登录" },
      });
    } catch (err: unknown) {
      const error = err as { data?: { message?: string } };
      setError(error?.data?.message || "注册失败，请稍后再试");
    }
  };

  // 切换注册类型时清除错误
  const handleTabChange = (key: React.Key) => {
    setRegisterType(key as RegisterType);
    setError("");
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-slate-900 py-8">
      {/* 背景渐变光晕 */}
      <div className="absolute inset-0 overflow-hidden">
        {/* 主光晕 - 青色 */}
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-cyan-500/20 rounded-full blur-[120px]" />
        {/* 次光晕 - 紫色 */}
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-violet-500/20 rounded-full blur-[120px]" />
        {/* 中心光晕 */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-radial from-violet-500/5 via-transparent to-transparent rounded-full" />
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

      {/* 注册卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        <Card className="bg-slate-800/60 backdrop-blur-xl border border-slate-700/50 shadow-2xl shadow-violet-500/5">
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
                创建账号
              </h1>
              <p className="text-slate-400 text-sm mt-1">加入 Earth Diary</p>
            </motion.div>
          </CardHeader>

          <CardBody className="px-6 pb-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Tab 切换 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                <Tabs
                  fullWidth
                  selectedKey={registerType}
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
                        <span>手机号注册</span>
                      </div>
                    }
                  />
                  <Tab
                    key="email"
                    title={
                      <div className="flex items-center gap-2">
                        <EmailIcon />
                        <span>邮箱注册</span>
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
                {/* 用户名输入框 */}
                <Input
                  type="text"
                  label="用户名"
                  placeholder="请输入用户名"
                  value={name}
                  onValueChange={setName}
                  isInvalid={nameValidation.isInvalid}
                  errorMessage={nameValidation.errorMessage}
                  startContent={<UserIcon />}
                  classNames={{
                    input: "text-white placeholder:text-slate-500",
                    inputWrapper:
                      "bg-slate-700/50 border-slate-600/50 hover:border-emerald-500/50 focus-within:border-emerald-500 group-data-[focus=true]:border-emerald-500",
                    label: "text-slate-400",
                    errorMessage: "text-rose-400",
                  }}
                  variant="bordered"
                />

                {/* 手机号/邮箱输入框 */}
                {registerType === "phone" ? (
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
                  placeholder="请输入密码（至少6位）"
                  value={password}
                  onValueChange={setPassword}
                  isInvalid={passwordValidation.isInvalid}
                  errorMessage={passwordValidation.errorMessage}
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
                    errorMessage: "text-rose-400",
                  }}
                  variant="bordered"
                />

                {/* 确认密码输入框 */}
                <Input
                  type={showConfirmPassword ? "text" : "password"}
                  label="确认密码"
                  placeholder="请再次输入密码"
                  value={confirmPassword}
                  onValueChange={setConfirmPassword}
                  isInvalid={confirmPasswordValidation.isInvalid}
                  errorMessage={confirmPasswordValidation.errorMessage}
                  startContent={<LockIcon />}
                  endContent={
                    <button
                      type="button"
                      onClick={() =>
                        setShowConfirmPassword(!showConfirmPassword)
                      }
                      className="text-slate-400 hover:text-slate-200 transition-colors focus:outline-none"
                    >
                      {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  }
                  classNames={{
                    input: "text-white placeholder:text-slate-500",
                    inputWrapper:
                      "bg-slate-700/50 border-slate-600/50 hover:border-slate-500/50 focus-within:border-cyan-500 group-data-[focus=true]:border-cyan-500",
                    label: "text-slate-400",
                    errorMessage: "text-rose-400",
                  }}
                  variant="bordered"
                />
              </motion.div>

              {/* 用户协议勾选 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
              >
                <Checkbox
                  isSelected={agreedToTerms}
                  onValueChange={setAgreedToTerms}
                  classNames={{
                    base: "max-w-full",
                    wrapper:
                      "border-slate-600 group-data-[selected=true]:border-cyan-500 group-data-[selected=true]:bg-gradient-to-r group-data-[selected=true]:from-cyan-500 group-data-[selected=true]:to-violet-500",
                    icon: "text-white",
                    label: "text-slate-400 text-sm",
                  }}
                  icon={<CheckIcon />}
                >
                  <span className="text-slate-400 text-sm">
                    我已阅读并同意
                    <Link
                      to="/terms"
                      className="text-cyan-400 hover:text-cyan-300 mx-1 hover:underline underline-offset-4"
                      onClick={(e) => e.stopPropagation()}
                    >
                      《用户协议》
                    </Link>
                    和
                    <Link
                      to="/privacy"
                      className="text-cyan-400 hover:text-cyan-300 mx-1 hover:underline underline-offset-4"
                      onClick={(e) => e.stopPropagation()}
                    >
                      《隐私政策》
                    </Link>
                  </span>
                </Checkbox>
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

              {/* 注册按钮 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
              >
                <Button
                  type="submit"
                  isLoading={isLoading}
                  isDisabled={!agreedToTerms}
                  className="w-full h-12 bg-linear-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white font-semibold text-base shadow-lg shadow-violet-500/20 transition-all duration-300 hover:shadow-violet-500/30 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  {isLoading ? "注册中..." : "注 册"}
                </Button>
              </motion.div>

              {/* 登录入口 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
                className="text-center pt-2"
              >
                <span className="text-slate-400 text-sm">已有账号？</span>
                <Link
                  to="/login"
                  className="text-cyan-400 hover:text-cyan-300 text-sm font-medium ml-1 transition-colors hover:underline underline-offset-4"
                >
                  立即登录
                </Link>
              </motion.div>
            </form>
          </CardBody>
        </Card>

        {/* 底部装饰文字 */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="text-center text-slate-500 text-xs mt-6"
        >
          © 2026 Earth Diary · 记录世界的每一刻
        </motion.p>
      </motion.div>
    </div>
  );
};

export default Register;
