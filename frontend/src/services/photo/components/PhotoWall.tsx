import type { RootState } from "@/app/store";
import { Masonry } from "masonic";
import { useCallback, useEffect, useState } from "react";
import { useInView } from "react-intersection-observer";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { useGetMyPhotosQuery, useUploadPhotosMutation } from "../redux/api/photoApi";
import type { Photo } from "../types/photoType";
import { PhotoCard } from "./PhotoCard";

const PAGE_SIZE = 25;

export const PhotoWall = () => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  const navigate = useNavigate();

  const [offset, setOffset] = useState(0);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [hasMore, setHasMore] = useState(true);
  // masonic 的 positioner 按数组索引缓存位置，items 变短后索引越界会 crash。
  // 用 key 强制 Masonry 销毁重建，重置 positioner 缓存。
  const [masonryKey, setMasonryKey] = useState(0);

  // 共享上传状态：上传成功后重置分页，从 offset=0 重新加载
  const [, { isSuccess: uploadJustSucceeded, reset: resetUploadState }] =
    useUploadPhotosMutation({ fixedCacheKey: "photo-upload" });

  useEffect(() => {
    if (uploadJustSucceeded) {
      setPhotos([]);
      setOffset(0);
      setHasMore(true);
      setMasonryKey((k) => k + 1);
      resetUploadState();
    }
  }, [uploadJustSucceeded, resetUploadState]);

  // 优化点 1: 真正重置所有状态，防止旧请求数据覆盖新状态
  useEffect(() => {
    if (isAuthenticated === undefined) return;
    setPhotos([]);
    setOffset(0);
    setHasMore(true);
  }, [isAuthenticated]);

  const { data, isFetching, isError } = useGetMyPhotosQuery(
    { limit: PAGE_SIZE, offset },
    { skip: !isAuthenticated }
  );

  // 同步服务端数据到本地列表：首页替换，翻页追加
  useEffect(() => {
    const items = data?.data?.items;
    if (!items) return;

    setPhotos((prev) => {
      if (offset === 0) return items;

      // 使用 Map 进行高效去重
      const photoMap = new Map(prev.map((p) => [p.id, p]));
      for (const item of items) {
        photoMap.set(item.id, item);
      }
      return Array.from(photoMap.values());
    });

    if (items.length < PAGE_SIZE) {
      setHasMore(false);
    }
  }, [data, offset]);

  const { ref: sentinelRef, inView } = useInView({
    rootMargin: "0px 0px 1200px 0px", // 适度缩小预加载范围，减轻初始压力
  });

  useEffect(() => {
    // 只有当不在加载中、有更多数据、且当前没有正在进行的请求尝试时才触发
    if (inView && hasMore && !isFetching && photos.length > 0) {
      setOffset(photos.length);
    }
  }, [inView, hasMore, isFetching, photos.length]);

  const handlePhotoDeleted = useCallback((id: string) => {
    setPhotos((prev) => prev.filter((p) => p.id !== id));
    setMasonryKey((k) => k + 1);
  }, []);

  const handlePhotoUpdated = useCallback(
    (updated: Photo) =>
      setPhotos((prev) => prev.map((p) => (p.id === updated.id ? updated : p))),
    []
  );

  const handlePhotoClick = useCallback(
    (photo: Photo, index: number) => {
      navigate(`/photo/${photo.id}`, {
        state: { photos, currentIndex: index },
      });
    },
    [navigate, photos]
  );

  const renderCard = useCallback(
    ({ data, index }: { data: Photo; index: number }) => (
      <PhotoCard
        key={data.id}
        data={data}
        onClick={() => handlePhotoClick(data, index)}
        onDeleted={handlePhotoDeleted}
        onUpdated={handlePhotoUpdated}
      />
    ),
    [handlePhotoDeleted, handlePhotoUpdated, handlePhotoClick]
  );

  if (!isFetching && !isError && photos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4 text-default-400">
        <p className="text-lg">还没有照片</p>
        <p className="text-sm">点击右上角「上传」开始添加</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      {photos.length > 0 && (
        <Masonry
          key={masonryKey}
          items={photos}
          columnGutter={12}
          columnWidth={288}
          render={renderCard}
          overscanBy={5}
        />
      )}

      {/* Sentinel：距底部 2000px 时提前触发 */}
      <div ref={sentinelRef} className="h-px" />

      {/* 加载中指示 */}
      {isFetching && (
        <div className="flex justify-center py-8">
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-2 h-2 rounded-full bg-default-300 animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* 全部加载完毕 */}
      {!hasMore && photos.length > 0 && (
        <p className="text-center text-sm text-default-400 py-8">
          共 {photos.length} 张照片，已全部加载
        </p>
      )}

      {/* 错误状态 */}
      {isError && (
        <p className="text-center text-sm text-danger py-8">加载失败，请刷新页面重试</p>
      )}
    </div>
  );
};
