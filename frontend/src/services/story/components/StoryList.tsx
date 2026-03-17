import { Button, Card, CardBody, Spinner } from "@heroui/react";
import { BookOpen, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useInView } from "react-intersection-observer";
import { useNavigate } from "react-router-dom";
import { useGetMyStoriesQuery } from "../redux/api/storyApi";
import type { Story } from "../types/storyType";

const STORAGE_BASE = import.meta.env.VITE_STORAGE_BASE_URL ?? "";
const PAGE_SIZE = 20;

export const StoryList = () => {
  const navigate = useNavigate();
  const [stories, setStories] = useState<Story[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const { data, isFetching } = useGetMyStoriesQuery({ limit: PAGE_SIZE, offset });

  useEffect(() => {
    if (data?.data) {
      const newItems = data.data.items;
      setStories((prev) => (offset === 0 ? newItems : [...prev, ...newItems]));
      setHasMore(offset + newItems.length < data.data.total);
    }
  }, [data, offset]);

  const loadMore = useCallback(() => {
    if (!isFetching && hasMore) {
      setOffset((prev) => prev + PAGE_SIZE);
    }
  }, [isFetching, hasMore]);

  const { ref: sentinelRef } = useInView({
    threshold: 0,
    onChange: (inView) => {
      if (inView) loadMore();
    },
  });

  const getCoverUrl = (story: Story) => {
    if (story.cover_thumbnail_key) {
      return `${STORAGE_BASE}/${story.cover_thumbnail_key}`;
    }
    return null;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 relative min-h-[50vh]">
      {stories.length === 0 && !isFetching && (
        <div className="flex flex-col items-center justify-center py-20 text-default-400">
          <BookOpen className="w-16 h-16 mb-4" />
          <p className="text-lg mb-2">还没有故事</p>
          <p className="text-sm">点击右下角按钮创建你的第一个故事</p>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {stories.map((story) => {
          const coverUrl = getCoverUrl(story);
          return (
            <Card
              key={story.id}
              isPressable
              onPress={() => navigate(`/story/${story.id}`)}
              className="overflow-hidden"
            >
              <CardBody className="flex flex-row gap-4 p-4">
                {coverUrl && (
                  <img
                    src={coverUrl}
                    alt=""
                    className="w-24 h-24 rounded-lg object-cover flex-shrink-0"
                  />
                )}
                <div className="flex flex-col min-w-0 flex-1">
                  <h3 className="text-lg font-semibold truncate">{story.title}</h3>
                  {story.content && (
                    <p className="text-sm text-default-500 line-clamp-2 mt-1">
                      {story.content}
                    </p>
                  )}
                  <span className="text-xs text-default-400 mt-auto">
                    {formatDate(story.created_at)}
                  </span>
                </div>
              </CardBody>
            </Card>
          );
        })}
      </div>

      {isFetching && (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      )}

      {hasMore && <div ref={sentinelRef} className="h-4" />}

      {/* FAB */}
      <Button
        isIconOnly
        color="primary"
        size="lg"
        className="fixed bottom-6 right-6 rounded-full shadow-lg z-50"
        onPress={() => navigate("/story/new")}
      >
        <Plus className="w-6 h-6" />
      </Button>
    </div>
  );
};
