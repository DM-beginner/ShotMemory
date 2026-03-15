import type { ApiResponse } from "@/services/auth/types/authType";

export type PhotoProcessStatus = "processing" | "completed" | "no_exif";

/** GeoJSON Point — Maplibre-GL-JS 原生格式 */
export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number]; // [longitude, latitude]
}

export interface Photo {
  id: string;
  user_id: string;
  object_key: string;
  thumbnail_key: string | null;
  video_key: string | null;
  width: number;
  height: number;
  location_wkt: GeoJSONPoint | null;
  exif_data: Record<string, unknown> | null;
  taken_at: string;
  created_at: string;
  status: PhotoProcessStatus;
}

export interface PhotoListData {
  total: number;
  items: Photo[];
}

export interface GetPhotosParams {
  limit?: number;
  offset?: number;
}

export type PhotoListResponse = ApiResponse<PhotoListData>;
export type PhotoResponse = ApiResponse<Photo>;
export type PhotoUploadResponse = ApiResponse<Photo[]>;
export type PhotoDeleteResponse = ApiResponse<Record<string, never>>;
