import { baseApi } from "@/app/baseApi";
import type {
  GetPhotosParams,
  Photo,
  PhotoDeleteResponse,
  PhotoListResponse,
  PhotoResponse,
  PhotoUploadResponse,
} from "../../types/photoType";

export const photoApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getMyPhotos: builder.query<PhotoListResponse, GetPhotosParams>({
      query: ({ limit = 25, offset = 0 } = {}) => ({
        url: "/photo",
        method: "GET",
        params: { limit, offset },
      }),
      providesTags: ["Photo"],
    }),

    getPhoto: builder.query<PhotoResponse, string>({
      query: (photoId) => ({
        url: `/photo/${photoId}`,
        method: "GET",
      }),
      providesTags: (_result, _error, id) => [{ type: "Photo", id }],
    }),

    uploadPhotos: builder.mutation<PhotoUploadResponse, File[]>({
      query: (files) => {
        const formData = new FormData();
        for (const file of files) {
          formData.append("files", file);
        }
        return {
          url: "/photo/uploads",
          method: "POST",
          body: formData,
        };
      },
      invalidatesTags: ["Photo"],
    }),

    updatePhoto: builder.mutation<
      PhotoResponse,
      { photoId: string; exif_data?: Record<string, unknown> }
    >({
      query: ({ photoId, ...body }) => ({
        url: `/photo/${photoId}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: (_result, _error, { photoId }) => [
        { type: "Photo", id: photoId },
      ],
    }),

    deletePhoto: builder.mutation<PhotoDeleteResponse, string>({
      query: (photoId) => ({
        url: `/photo/${photoId}`,
        method: "DELETE",
      }),
      // 不 invalidate — PhotoWall 通过 onDeleted 回调直接更新本地 photos 状态，
      // 避免 refetch 与本地状态竞争导致 Masonry 布局崩溃
    }),

    batchDeletePhotos: builder.mutation<PhotoDeleteResponse, string[]>({
      query: (photoIds) => ({
        url: "/photo/batch-delete",
        method: "POST",
        body: photoIds,
      }),
      // 同上：由调用方通过本地状态移除已删除项
    }),
  }),
});

export const {
  useGetMyPhotosQuery,
  useGetPhotoQuery,
  useUploadPhotosMutation,
  useUpdatePhotoMutation,
  useDeletePhotoMutation,
  useBatchDeletePhotosMutation,
} = photoApi;

export type PhotoItem = Photo;
