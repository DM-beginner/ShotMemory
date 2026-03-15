import { Button } from "@heroui/react";
import clsx from "clsx";
import { Disc3, Trash2 } from "lucide-react";
import { memo, useEffect, useRef, useState } from "react";
import { useDeletePhotoMutation, useGetPhotoQuery } from "../redux/api/photoApi";
import type { Photo } from "../types/photoType";
import { getOriginalUrl, getPhotoUrl, getVideoUrl } from "../utils/photoUrl";

interface PhotoCardProps {
  data: Photo;
  width?: number; // masonic 会自动注入此属性，声明出来避免 TS 报错
  onDeleted?: (id: string) => void;
  onUpdated?: (photo: Photo) => void;
}

export const PhotoCard = memo(
  ({ data: photo, onDeleted, onUpdated }: PhotoCardProps) => {
    const [imgLoaded, setImgLoaded] = useState(false);
    const [hdLoaded, setHdLoaded] = useState(false);
    const [showVideo, setShowVideo] = useState(false);
    const [deletePhoto, { isLoading: isDeleting }] = useDeletePhotoMutation();
    const [pollCount, setPollCount] = useState(0);
    const videoRef = useRef<HTMLVideoElement>(null);

    const isProcessing = photo.status === "processing";
    const isLivePhoto = !!photo.video_key;
    const shouldPoll = isProcessing && pollCount < 20;
    const aspectRatio = photo.width && photo.height ? photo.width / photo.height : 1;

    // Processing 轮询：每 3s 查询一次，直到 status 不再是 processing 或达到上限
    const { data: polledData } = useGetPhotoQuery(photo.id, {
      pollingInterval: 3000,
      skip: !shouldPoll,
    });

    useEffect(() => {
      if (!shouldPoll) return;
      const updated = polledData?.data;
      if (updated && updated.status !== "processing") {
        onUpdated?.(updated);
      } else if (updated) {
        setPollCount((c) => c + 1);
      }
    }, [polledData, onUpdated, shouldPoll]);

    const handleDelete = async () => {
      try {
        await deletePhoto(photo.id).unwrap();
        onDeleted?.(photo.id);
      } catch {
        // 错误已由 RTK Query 全局/组件内拦截处理
      }
    };

    return (
      <div
        className="group relative w-full cursor-pointer overflow-hidden rounded-xl bg-default-100"
        style={{
          aspectRatio: `${aspectRatio}`,
        }}
        onMouseEnter={() => {
          if (isLivePhoto && videoRef.current) {
            setShowVideo(true);
            videoRef.current.currentTime = 0;
            videoRef.current.play();
          }
        }}
        onMouseLeave={() => {
          setShowVideo(false);
          if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.currentTime = 0;
          }
        }}
      >
        {/* 实况照片图标（点击可重播） */}
        {isLivePhoto && (
          <div className="absolute top-2 left-2 z-10">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (videoRef.current) {
                  setShowVideo(true);
                  videoRef.current.currentTime = 0;
                  videoRef.current.play();
                }
              }}
              className="flex cursor-pointer items-center gap-1 rounded-full bg-black/40 px-1.5 py-0.5 text-[10px] text-white backdrop-blur-sm transition-colors hover:bg-black/60"
            >
              <Disc3 className="h-3 w-3" />
              实况
            </button>
          </div>
        )}

        {/* Processing 标签 */}
        {isProcessing && (
          <div className="absolute inset-x-0 top-0 z-10 flex justify-center pt-2 pointer-events-none">
            <span className="rounded-full bg-white/80 px-2 py-1 text-xs text-default-500 backdrop-blur-sm">
              处理中…
            </span>
          </div>
        )}

        {/* 照片主体：模糊渐进加载 */}
        <div className="absolute inset-0 transition-transform duration-700 group-hover:scale-105">
          {/* 底层：缩略图（快速展示，带 blur-up） */}
          <img
            src={getPhotoUrl(photo)}
            alt={photo.taken_at || "Photo"}
            loading="lazy"
            onLoad={() => setImgLoaded(true)}
            className={clsx(
              "absolute inset-0 h-full w-full object-cover transition-all duration-700",
              imgLoaded ? "blur-0 scale-100" : "blur-xl scale-105"
            )}
          />

          {/* 顶层：原图（缩略图加载完成后才开始加载，淡入覆盖） */}
          {imgLoaded && !isProcessing && (
            <img
              src={getOriginalUrl(photo)}
              alt={photo.taken_at || "Photo"}
              onLoad={() => setHdLoaded(true)}
              className={clsx(
                "absolute inset-0 h-full w-full object-cover transition-opacity duration-700",
                hdLoaded ? "opacity-100" : "opacity-0"
              )}
            />
          )}

          {/* 实况照片视频层：播放一次后淡出 */}
          {isLivePhoto && (
            <video
              ref={videoRef}
              src={getVideoUrl(photo)!}
              muted
              playsInline
              preload="none"
              onEnded={() => setShowVideo(false)}
              className={clsx(
                "absolute inset-0 h-full w-full object-cover transition-opacity duration-300",
                showVideo ? "opacity-100" : "opacity-0"
              )}
            />
          )}
        </div>

        {/* 悬浮遮罩 + 删除按钮 */}
        <div
          className={clsx(
            "absolute inset-0 flex items-end justify-end p-2",
            "bg-gradient-to-t from-black/40 via-transparent to-transparent",
            "opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          )}
        >
          <Button
            isIconOnly
            size="sm"
            color="danger"
            variant="flat"
            isLoading={isDeleting}
            onPress={handleDelete}
            className="translate-y-2 transition-transform duration-300 group-hover:translate-y-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }
);

PhotoCard.displayName = "PhotoCard"; // 规范：memo 组件显式声明名称
