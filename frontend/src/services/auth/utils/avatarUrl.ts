const STORAGE_BASE = import.meta.env.VITE_STORAGE_BASE_URL ?? "";

export const getAvatarUrl = (avatarKey?: string): string | undefined =>
  avatarKey ? `${STORAGE_BASE}/${avatarKey}` : undefined;
