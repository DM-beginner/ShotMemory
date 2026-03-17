import { baseApi } from "@/app/baseApi";
import type {
  StoryCreateRequest,
  StoryDetailResponse,
  StoryListResponse,
  StoryMutationResponse,
  StoryUpdateRequest,
} from "../../types/storyType";

export const storyApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getMyStories: builder.query<StoryListResponse, { limit?: number; offset?: number }>(
      {
        query: ({ limit = 20, offset = 0 } = {}) => ({
          url: "/story",
          method: "GET",
          params: { limit, offset },
        }),
        providesTags: ["Story"],
      }
    ),

    getStory: builder.query<StoryDetailResponse, string>({
      query: (storyId) => ({
        url: `/story/${storyId}`,
        method: "GET",
      }),
      providesTags: (_result, _error, id) => [{ type: "Story", id }],
    }),

    createStory: builder.mutation<StoryMutationResponse, StoryCreateRequest>({
      query: (body) => ({
        url: "/story",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Story"],
    }),

    updateStory: builder.mutation<
      StoryMutationResponse,
      { id: string } & StoryUpdateRequest
    >({
      query: ({ id, ...body }) => ({
        url: `/story/${id}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["Story"],
    }),

    deleteStory: builder.mutation<StoryMutationResponse, string>({
      query: (storyId) => ({
        url: `/story/${storyId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Story"],
    }),
  }),
});

export const {
  useGetMyStoriesQuery,
  useGetStoryQuery,
  useCreateStoryMutation,
  useUpdateStoryMutation,
  useDeleteStoryMutation,
} = storyApi;
