import { useLoginMutation, useRegisterMutation } from "@/services/auth";
import { getDeviceId } from "@/services/auth/utils/tokenHelper";
import {
  Button,
  Input,
  Modal,
  ModalBody,
  ModalContent,
  ModalHeader,
  Tab,
  Tabs,
} from "@heroui/react";
import { Eye, EyeOff, Lock, Mail, Smartphone, User } from "lucide-react";
import { useMemo, useState } from "react";
import type { Key, SyntheticEvent } from "react";

interface AuthModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

type AuthMode = "login" | "register";
type AccountType = "phone" | "email";

const validatePhone = (value: string) => /^1[3-9]\d{9}$/.test(value);
const validateEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const validateName = (value: string) => value.length >= 1 && value.length <= 20;

export const AuthModal = ({ isOpen, onOpenChange }: AuthModalProps) => {
  // 1. 顶层状态
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [accountType, setAccountType] = useState<AccountType>("phone");

  // 2. 表单字段状态
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  // const [agreedToTerms, setAgreedToTerms] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const [loginMutation, { isLoading: isLoginLoading }] = useLoginMutation();
  const [registerMutation, { isLoading: isRegisterLoading }] = useRegisterMutation();

  // === 优化 2：状态重置逻辑抽离，保持代码 DRY ===
  const resetFormState = () => {
    setError("");
    setPassword("");
    setConfirmPassword("");
  };

  const resetAllFields = () => {
    setPhone("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setName("");
    // setAgreedToTerms(false);
    setError("");
  };

  const handleAuthModeChange = (key: Key) => {
    setAuthMode(key as AuthMode);
    resetFormState();
  };

  const handleAccountTypeChange = (key: Key) => {
    setAccountType(key as AccountType);
    resetFormState();
  };

  const isPhoneInvalid = useMemo(() => {
    if (!phone) return false;
    return !validatePhone(phone);
  }, [phone]);

  const isEmailInvalid = useMemo(() => {
    if (!email) return false;
    return !validateEmail(email);
  }, [email]);

  const validateLogin = () => {
    if (accountType === "phone" && isPhoneInvalid) {
      setError("请输入正确的手机号码");
      return false;
    }

    if (accountType === "email" && isEmailInvalid) {
      setError("请输入正确的邮箱地址");
      return false;
    }

    if (!password || password.length < 6) {
      setError("密码长度不能少于6位");
      return false;
    }

    return true;
  };

  const validateRegister = () => {
    if (!name || !validateName(name)) {
      setError("用户名长度需在20字符以内");
      return false;
    }
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return false;
    }
    // if (!agreedToTerms) {
    //   setError("请先阅读并同意服务协议和隐私政策");
    //   return false;
    // }
    return true;
  };

  const getErrorMessage = (err: unknown, fallback: string) => {
    const errorResponse = err as { data?: { detail?: string; message?: string } };
    return errorResponse?.data?.detail || errorResponse?.data?.message || fallback;
  };

  const handleSubmit = async (e: SyntheticEvent) => {
    e.preventDefault();
    setError("");

    if (!validateLogin() || (authMode === "register" && !validateRegister())) return;

    try {
      if (authMode === "login") {
        const loginPayload =
          accountType === "phone"
            ? { phone, password, device_id: getDeviceId() }
            : { email, password, device_id: getDeviceId() };

        await loginMutation(loginPayload).unwrap();
        resetAllFields();
        onOpenChange(false);
        return;
      }

      const registerPayload =
        accountType === "phone" ? { name, phone, password } : { name, email, password };
      await registerMutation(registerPayload).unwrap();
      setAuthMode("login");
      setPassword("");
      setConfirmPassword("");
      setError("注册成功！请登录");
    } catch (err: unknown) {
      setError(
        getErrorMessage(
          err,
          `${authMode === "login" ? "登录" : "注册"}失败，请稍后再试`
        )
      );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      placement="center"
      backdrop="blur"
      className="max-w-md"
    >
      <ModalContent>
        {() => (
          <>
            <ModalHeader className="flex flex-col gap-1 pb-0 pt-8 px-8">
              <h2 className="font-display text-2xl font-bold tracking-tight">
                Welcome to ShotMemory
              </h2>
              <p className="text-sm text-default-500 font-sans font-normal mt-1">
                记录你的专属视界
              </p>
            </ModalHeader>

            <ModalBody className="p-8">
              <Tabs
                fullWidth
                size="md"
                variant="underlined"
                selectedKey={authMode}
                onSelectionChange={handleAuthModeChange}
                className="mb-2"
              >
                <Tab key="login" title="登录" />
                <Tab key="register" title="注册" />
              </Tabs>

              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                {/* === 优化 5：将渲染函数内联，保持 React 树结构的清晰直观 === */}
                <div className="flex flex-col gap-4">
                  <Tabs
                    fullWidth
                    size="sm"
                    selectedKey={accountType}
                    onSelectionChange={handleAccountTypeChange}
                  >
                    <Tab
                      key="phone"
                      title={authMode === "register" ? "手机号注册" : "手机号验证"}
                    />
                    <Tab
                      key="email"
                      title={authMode === "register" ? "邮箱注册" : "邮箱验证"}
                    />
                  </Tabs>
                  {authMode === "register" && (
                    <Input
                      isRequired
                      placeholder="请输入用户名"
                      variant="faded"
                      isInvalid={name.length > 20}
                      maxLength={20}
                      errorMessage="用户名长度需在20字符以内"
                      value={name}
                      onValueChange={setName}
                      startContent={<User className="w-4 h-4 text-default-400" />}
                    />
                  )}

                  {accountType === "phone" ? (
                    <Input
                      autoFocus
                      placeholder="请输入手机号"
                      variant="faded"
                      value={phone}
                      onValueChange={setPhone}
                      isInvalid={isPhoneInvalid}
                      errorMessage="请输入正确的手机号码"
                      startContent={<Smartphone className="w-4 h-4 text-default-400" />}
                    />
                  ) : (
                    <Input
                      autoFocus
                      placeholder="请输入邮箱"
                      variant="faded"
                      value={email}
                      onValueChange={setEmail}
                      isInvalid={isEmailInvalid}
                      errorMessage="请输入正确的邮箱地址"
                      startContent={<Mail className="w-4 h-4 text-default-400" />}
                    />
                  )}
                </div>

                <Input
                  placeholder="请输入密码"
                  variant="faded"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onValueChange={setPassword}
                  startContent={<Lock className="w-4 h-4 text-default-400" />}
                  endContent={
                    // === 优化 6：补充 aria-label，满足 Biome 的 a11y 规范 ===
                    // 同时使用函数式的 setState 避免闭包陷阱
                    <button
                      type="button"
                      aria-label={showPassword ? "隐藏密码" : "显示密码"}
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="focus:outline-solid outline-transparent cursor-pointer"
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4 text-default-400 pointer-events-none" />
                      ) : (
                        <Eye className="w-4 h-4 text-default-400 pointer-events-none" />
                      )}
                    </button>
                  }
                />

                {authMode === "register" && (
                  <Input
                    placeholder="请确认密码"
                    variant="faded"
                    type={showPassword ? "text" : "password"}
                    value={confirmPassword}
                    onValueChange={setConfirmPassword}
                    startContent={<Lock className="w-4 h-4 text-default-400" />}
                  />
                )}

                {error && <p className="text-danger text-sm">{error}</p>}

                {/* {authMode === "register" && (
                  <Checkbox size="sm" isSelected={agreedToTerms} onValueChange={setAgreedToTerms}>
                    我已阅读并同意
                    <Link href="#" size="sm" className="mx-1">
                      服务协议
                    </Link>
                    和
                    <Link href="#" size="sm" className="ml-1">
                      隐私政策
                    </Link>
                  </Checkbox>
                )} */}

                <Button
                  type="submit"
                  color="primary"
                  size="lg"
                  isLoading={authMode === "login" ? isLoginLoading : isRegisterLoading}
                >
                  {authMode === "login" ? "登录" : "立即注册"}
                </Button>
              </form>
            </ModalBody>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};
