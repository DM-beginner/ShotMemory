import type { Photo } from "../types/photoType";

const STORAGE_BASE = import.meta.env.VITE_STORAGE_BASE_URL ?? "";

export const getPhotoUrl = (photo: Photo): string =>
  `${STORAGE_BASE}/${photo.thumbnail_key ?? photo.object_key}`;

export const getOriginalUrl = (photo: Photo): string =>
  `${STORAGE_BASE}/${photo.object_key}`;

export const getVideoUrl = (photo: Photo): string | null =>
  photo.video_key ? `${STORAGE_BASE}/${photo.video_key}` : null;
