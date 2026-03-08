import { useState, useCallback, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Input,
  Button,
  Tabs,
  Tab,
  Link,
  Divider,
  addToast,
} from "@heroui/react";
import { useNavigate } from "react-router-dom";
import { useLoginMutation, useRegisterMutation } from "@/services/auth/redux/api/authApi";
import { getDeviceId } from "@/services/auth/utils/tokenHelper";

// --- 图标组件 ---
const EyeIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" height="20" viewBox="0 0 24 24" width="20" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" fill="currentColor" />
  </svg>
);
const EyeSlashIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" height="20" viewBox="0 0 24 24" width="20" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z" fill="currentColor" />
  </svg>
);
const EarthIcon = () => (
  <svg className="w-10 h-10 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
  </svg>
);
const PhoneIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
  </svg>
);

export default function Login() {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState<string>("login");
  const [loginMode, setLoginMode] = useState<"email" | "phone">("email"); // 登录模式切换

  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [isConfirmPasswordVisible, setIsConfirmPasswordVisible] = useState(false);

  // 邮箱登录状态
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // 手机登录状态
  const [phoneNumber, setPhoneNumber] = useState("");
  const [verifyCode, setVerifyCode] = useState("");
  const [countdown, setCountdown] = useState(0); // 验证码倒计时

  // 注册表单状态
  const [registerName, setRegisterName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // RTK Query
  const [login, { isLoading: isLoginLoading }] = useLoginMutation();
  const [register, { isLoading: isRegisterLoading }] = useRegisterMutation();

  // 倒计时逻辑
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  // 模拟发送验证码
  const handleSendCode = () => {
    if (!phoneNumber) {
      addToast({ title: "请输入手机号", color: "warning" });
      return;
    }
    // 这里未来接入后端 API
    setCountdown(60);
    addToast({ title: "验证码已发送", description: "假装发了：123456", color: "success" });
  };

  const togglePasswordVisibility = () => setIsPasswordVisible(!isPasswordVisible);
  const toggleConfirmPasswordVisibility = () => setIsConfirmPasswordVisible(!isConfirmPasswordVisible);

  // 统一登录处理
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (loginMode === "email") {
        if (!loginEmail || !loginPassword) {
          addToast({ title: "请填写完整信息", color: "warning" });
          return;
        }
        const deviceId = getDeviceId();
        await login({ email: loginEmail, password: loginPassword, device_id: deviceId }).unwrap();
      } else {
        // 手机号登录逻辑（暂时 mock）
        if (!phoneNumber || !verifyCode) {
          addToast({ title: "请填写手机号和验证码", color: "warning" });
          return;
        }
        // TODO: 调用手机号登录 API
        addToast({ title: "演示模式", description: "手机号登录暂未接入后端", color: "primary" });
        return;
      }

      addToast({ title: "登录成功", description: "欢迎回来！", color: "success" });
      navigate("/");
    } catch (error) {
      const err = error as { data?: { message?: string } };
      addToast({ title: "登录失败", description: err.data?.message || "请检查输入信息", color: "danger" });
    }
  };

  // 注册处理 (保持不变)
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (registerPassword !== confirmPassword) {
      addToast({ title: "密码不匹配", color: "danger" });
      return;
    }
    try {
      await register({ name: registerName, email: registerEmail, password: registerPassword }).unwrap();
      addToast({ title: "注册成功", color: "success" });
      setSelectedTab("login");
      setLoginMode("email"); // 注册成功默认切回邮箱登录
      setLoginEmail(registerEmail);
    } catch (error) {
      const err = error as { data?: { message?: string } };
      addToast({ title: "注册失败", description: err.data?.message, color: "danger" });
    }
  };

  // 输入框通用样式
  const inputStyles = {
    input: "text-slate-200",
    label: "text-slate-400",
    inputWrapper: "border-slate-600 hover:border-emerald-500 data-[focused=true]:border-emerald-500 bg-slate-800/50",
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-emerald-950 to-slate-900 p-4">
      {/* 背景光效 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-600/5 rounded-full blur-3xl" />
      </div>

      <Card className="w-full max-w-md backdrop-blur-xl bg-slate-900/80 border border-slate-700/50 shadow-2xl">
        <CardHeader className="flex flex-col gap-3 pt-8 pb-0">
          <div className="flex items-center justify-center gap-3">
            <EarthIcon />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              Earth Diary
            </h1>
          </div>
          <p className="text-slate-400 text-sm text-center">记录地球上的每一天</p>
        </CardHeader>

        <CardBody className="px-6 py-6">
          <Tabs
            selectedKey={selectedTab}
            onSelectionChange={(key) => setSelectedTab(key as string)}
            variant="underlined"
            color="success"
            classNames={{
              tabList: "gap-6 w-full justify-center border-b border-slate-700/50",
              tab: "h-12 text-slate-400 data-[selected=true]:text-emerald-400",
              cursor: "bg-emerald-500",
              panel: "pt-6",
            }}
          >
            {/* --- 登录 Tab --- */}
            <Tab key="login" title="登录">
              <div className="flex flex-col gap-5">
                {/* 登录方式切换子 Tab */}
                <div className="flex p-1 bg-slate-800/50 rounded-lg self-center">
                  <button
                    onClick={() => setLoginMode("email")}
                    className={`px-4 py-1.5 text-sm rounded-md transition-all ${
                      loginMode === "email" ? "bg-emerald-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    账号密码
                  </button>
                  <button
                    onClick={() => setLoginMode("phone")}
                    className={`px-4 py-1.5 text-sm rounded-md transition-all ${
                      loginMode === "phone" ? "bg-emerald-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    手机验证码
                  </button>
                </div>

                <form onSubmit={handleLogin} className="flex flex-col gap-5">
                  {loginMode === "email" ? (
                    <>
                      <Input
                        label="邮箱"
                        type="email"
                        variant="bordered"
                        value={loginEmail}
                        onValueChange={setLoginEmail}
                        classNames={inputStyles}
                        autoComplete="email"
                      />
                      <Input
                        label="密码"
                        variant="bordered"
                        value={loginPassword}
                        onValueChange={setLoginPassword}
                        type={isPasswordVisible ? "text" : "password"}
                        classNames={inputStyles}
                        endContent={
                          <button type="button" onClick={togglePasswordVisibility} className="text-slate-400 hover:text-emerald-400">
                            {isPasswordVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                          </button>
                        }
                        autoComplete="current-password"
                      />
                    </>
                  ) : (
                    <>
                      <Input
                        label="手机号"
                        type="tel"
                        variant="bordered"
                        value={phoneNumber}
                        onValueChange={setPhoneNumber}
                        classNames={inputStyles}
                        startContent={<PhoneIcon className="w-5 h-5 text-slate-500" />}
                        placeholder="请输入手机号"
                      />
                      <div className="flex gap-3">
                        <Input
                          label="验证码"
                          variant="bordered"
                          value={verifyCode}
                          onValueChange={setVerifyCode}
                          classNames={inputStyles}
                          className="flex-1"
                        />
                        <Button
                          color="primary"
                          variant="flat"
                          className="h-14 bg-slate-800 text-emerald-400 border border-slate-600"
                          isDisabled={countdown > 0}
                          onPress={handleSendCode}
                        >
                          {countdown > 0 ? `${countdown}s` : "获取验证码"}
                        </Button>
                      </div>
                    </>
                  )}

                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500 cursor-pointer hover:text-emerald-400 transition-colors">
                      无法登录？
                    </span>
                    <Link href="#" size="sm" className="text-emerald-400 hover:text-emerald-300">
                      忘记密码？
                    </Link>
                  </div>

                  <Button
                    type="submit"
                    color="success"
                    variant="shadow"
                    size="lg"
                    isLoading={isLoginLoading}
                    className="mt-2 font-semibold bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                  >
                    {isLoginLoading ? "登录中..." : "登录"}
                  </Button>
                </form>
              </div>
            </Tab>

            {/* --- 注册 Tab (保持精简) --- */}
            <Tab key="register" title="注册">
              <form onSubmit={handleRegister} className="flex flex-col gap-4">
                <Input
                  label="用户名"
                  variant="bordered"
                  value={registerName}
                  onValueChange={setRegisterName}
                  classNames={inputStyles}
                />
                <Input
                  label="邮箱"
                  type="email"
                  variant="bordered"
                  value={registerEmail}
                  onValueChange={setRegisterEmail}
                  classNames={inputStyles}
                />
                <Input
                  label="密码"
                  variant="bordered"
                  value={registerPassword}
                  onValueChange={setRegisterPassword}
                  type={isPasswordVisible ? "text" : "password"}
                  classNames={inputStyles}
                  endContent={
                    <button type="button" onClick={togglePasswordVisibility} className="text-slate-400 hover:text-emerald-400">
                      {isPasswordVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                    </button>
                  }
                />
                <Input
                  label="确认密码"
                  variant="bordered"
                  value={confirmPassword}
                  onValueChange={setConfirmPassword}
                  type={isConfirmPasswordVisible ? "text" : "password"}
                  classNames={inputStyles}
                  endContent={
                    <button type="button" onClick={toggleConfirmPasswordVisibility} className="text-slate-400 hover:text-emerald-400">
                      {isConfirmPasswordVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                    </button>
                  }
                />
                <Button
                  type="submit"
                  color="success"
                  variant="shadow"
                  size="lg"
                  isLoading={isRegisterLoading}
                  className="mt-2 font-semibold bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                >
                  {isRegisterLoading ? "注册中..." : "创建账号"}
                </Button>
              </form>
            </Tab>
          </Tabs>
        </CardBody>
        <Divider className="bg-slate-700/50" />
        <CardFooter className="flex flex-col gap-4 py-6">
          <p className="text-slate-500 text-xs text-center">
            登录即代表同意 <Link href="#" className="text-emerald-400">服务条款</Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
