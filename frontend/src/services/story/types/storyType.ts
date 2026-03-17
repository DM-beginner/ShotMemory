import type { ApiResponse } from "@/services/auth/types/authType";
import type { Photo } from "@/services/photo/types/photoType";

export interface Story {
  id: string;
  user_id: string;
  title: string;
  content: string | null;
  cover_photo_id: string | null;
  cover_thumbnail_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface StoryDetail extends Story {
  photos: Photo[];
}

export interface StoryListData {
  total: number;
  items: Story[];
}

export interface StoryCreateRequest {
  title: string;
  content?: string;
  photo_ids: string[];
  cover_photo_id?: string;
}

export interface StoryUpdateRequest {
  title?: string;
  content?: string;
  photo_ids?: string[];
  cover_photo_id?: string;
}

export type StoryListResponse = ApiResponse<StoryListData>;
export type StoryDetailResponse = ApiResponse<StoryDetail>;
export type StoryMutationResponse = ApiResponse<Story>;
