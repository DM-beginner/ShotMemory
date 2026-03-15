import type { RootState } from "@/app/store";
import { authApi, useLogoutMutation, useUploadAvatarMutation } from "@/services/auth";
import { AuthModal } from "@/services/auth/components/AuthModal";
import { getAvatarUrl } from "@/services/auth/utils/avatarUrl";
import { UploadModal } from "@/services/photo/components/UploadModal";
import {
  Avatar,
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
} from "@heroui/react";
import { Camera, LogOut, Moon, Sun, Upload } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";
import { useSelector } from "react-redux";

export const Header = () => {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [logoutMutation] = useLogoutMutation();
  const [uploadAvatar] = useUploadAvatarMutation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: meData } = authApi.useGetMeQuery(undefined, { skip: !isAuthenticated });
  const avatarUrl = getAvatarUrl(meData?.data?.avatar_key);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    await uploadAvatar(formData);
    e.target.value = "";
  };

  return (
    <>
      <Navbar maxWidth="full" shouldHideOnScroll className="px-4">
        <NavbarBrand className="gap-2">
          ShotMemory
          <NavbarItem>
            {!mounted ? (
              <Button isIconOnly variant="light" aria-label="加载中" className="p-2" />
            ) : (
              <Button
                isIconOnly
                variant="light"
                aria-label="切换主题"
                className="p-2"
                onPress={() => setTheme(theme === "dark" ? "light" : "dark")}
              >
                {theme === "dark" ? (
                  <Sun className="w-5 h-5" />
                ) : (
                  <Moon className="w-5 h-5" />
                )}
              </Button>
            )}
          </NavbarItem>
        </NavbarBrand>
        <NavbarContent justify="end" className="gap-4">
          {isAuthenticated && (
            <NavbarItem>
              <Button
                color="primary"
                startContent={<Upload className="w-4 h-4" />}
                onPress={() => setIsUploadModalOpen(true)}
              >
                上传
              </Button>
            </NavbarItem>
          )}
          <NavbarItem>
            {isAuthenticated ? (
              <Dropdown placement="bottom-end">
                <DropdownTrigger>
                  <Avatar
                    isBordered
                    as="button"
                    radius="md"
                    className="transition-transform cursor-pointer"
                    src={avatarUrl}
                  />
                </DropdownTrigger>
                <DropdownMenu aria-label="用户菜单">
                  <DropdownItem
                    key="avatar"
                    startContent={<Camera className="w-4 h-4" />}
                    onPress={() => fileInputRef.current?.click()}
                  >
                    修改头像
                  </DropdownItem>
                  <DropdownItem
                    key="logout"
                    color="danger"
                    startContent={<LogOut className="w-4 h-4" />}
                    onPress={() => logoutMutation()}
                  >
                    退出登录
                  </DropdownItem>
                </DropdownMenu>
              </Dropdown>
            ) : (
              <Button color="primary" onPress={() => setIsAuthModalOpen(true)}>
                登录
              </Button>
            )}
          </NavbarItem>
        </NavbarContent>
      </Navbar>
      <AuthModal isOpen={isAuthModalOpen} onOpenChange={setIsAuthModalOpen} />
      <UploadModal isOpen={isUploadModalOpen} onOpenChange={setIsUploadModalOpen} />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleAvatarChange}
      />
    </>
  );
};
