import clsx from "clsx";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useGetPhotoQuery } from "../redux/api/photoApi";
import type { Photo } from "../types/photoType";
import { formatCameraSummary } from "../utils/exifFormat";
import { getOriginalUrl, getPhotoUrl } from "../utils/photoUrl";
import { ExifPanel } from "./ExifPanel";
import { ThumbnailStrip } from "./ThumbnailStrip";

interface LocationState {
  photos: Photo[];
  currentIndex: number;
}

export const PhotoDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;

  // Whether we have full album context from PhotoWall
  const hasAlbumContext = !!state?.photos?.length;
  const [currentIndex, setCurrentIndex] = useState(state?.currentIndex ?? 0);
  const photos = state?.photos ?? [];

  // Fallback: direct URL access — fetch single photo
  const { data: singlePhotoData } = useGetPhotoQuery(id ?? "", {
    skip: hasAlbumContext || !id,
  });

  const currentPhoto: Photo | undefined = hasAlbumContext
    ? photos[currentIndex]
    : singlePhotoData?.data;

  // Progressive loading state
  const [thumbLoaded, setThumbLoaded] = useState(false);
  const [hdLoaded, setHdLoaded] = useState(false);
  const [exifOpen, setExifOpen] = useState(true);

  // biome-ignore lint/correctness/useExhaustiveDependencies: currentPhoto?.id is an intentional trigger
  useEffect(() => {
    setThumbLoaded(false);
    setHdLoaded(false);
  }, [currentPhoto?.id]);

  // Navigation
  const canGoPrev = hasAlbumContext && currentIndex > 0;
  const canGoNext = hasAlbumContext && currentIndex < photos.length - 1;

  const goPrev = useCallback(() => {
    if (canGoPrev) setCurrentIndex((i) => i - 1);
  }, [canGoPrev]);

  const goNext = useCallback(() => {
    if (canGoNext) setCurrentIndex((i) => i + 1);
  }, [canGoNext]);

  const goBack = useCallback(() => {
    navigate(-1);
  }, [navigate]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") goPrev();
      else if (e.key === "ArrowRight") goNext();
      else if (e.key === "Escape") goBack();
      else if (e.key === "i" || e.key === "I") setExifOpen((o) => !o);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goPrev, goNext, goBack]);

  // Camera summary text
  const cameraSummary = useMemo(
    () => (currentPhoto ? formatCameraSummary(currentPhoto.exif_data) : null),
    [currentPhoto]
  );

  if (!currentPhoto) {
    return (
      <div className="flex h-screen items-center justify-center bg-black text-white/60">
        加载中…
      </div>
    );
  }

  const thumbnailUrl = getPhotoUrl(currentPhoto);
  const originalUrl = getOriginalUrl(currentPhoto);

  return (
    <div className="relative h-screen w-screen overflow-hidden select-none">
      {/* Layer 1: Blurred background */}
      <div
        className="absolute inset-0 scale-110 bg-cover bg-center"
        style={{
          backgroundImage: `url(${thumbnailUrl})`,
          filter: "blur(40px) saturate(1.2) brightness(0.6)",
        }}
      />

      {/* Layer 2: Dark overlay */}
      <div className="absolute inset-0 bg-black/30" />

      {/* Layer 3: Main photo */}
      <div
        className={clsx(
          "absolute inset-0 z-10 flex items-center justify-center",
          hasAlbumContext ? "pb-20" : "pb-0",
          exifOpen ? "pr-80" : "pr-0"
        )}
        style={{ transition: "padding 300ms ease-in-out" }}
      >
        <div className="relative h-full w-full">
          {/* Thumbnail (blur-up base) */}
          <img
            src={thumbnailUrl}
            alt=""
            onLoad={() => setThumbLoaded(true)}
            className={clsx(
              "h-full w-full object-contain transition-all duration-500",
              thumbLoaded ? "blur-0" : "blur-lg"
            )}
          />

          {/* HD overlay */}
          {thumbLoaded && (
            <img
              src={originalUrl}
              alt={currentPhoto.taken_at || "Photo"}
              onLoad={() => setHdLoaded(true)}
              className={clsx(
                "absolute inset-0 h-full w-full object-contain transition-opacity duration-700",
                hdLoaded ? "opacity-100" : "opacity-0"
              )}
            />
          )}

          {/* Camera summary */}
          {cameraSummary && (
            <div
              className={clsx(
                "absolute inset-x-0 flex justify-center pointer-events-none",
                hasAlbumContext ? "bottom-2" : "bottom-4"
              )}
            >
              <span className="rounded-full bg-black/50 backdrop-blur-sm px-4 py-1.5 text-xs text-white/80">
                {cameraSummary}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Back button */}
      <button
        type="button"
        onClick={goBack}
        className="absolute top-4 left-4 z-30 flex items-center gap-1.5 rounded-full bg-black/50 px-4 py-2 text-sm text-white/80 backdrop-blur-sm transition-colors hover:bg-black/70 hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        返回
      </button>

      {/* Left / Right navigation arrows */}
      {canGoPrev && (
        <button
          type="button"
          onClick={goPrev}
          className="absolute left-4 top-1/2 z-20 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/60 backdrop-blur-sm opacity-0 transition-opacity hover:bg-black/60 hover:text-white hover:opacity-100 group-hover:opacity-100 md:opacity-40"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}
      {canGoNext && (
        <button
          type="button"
          onClick={goNext}
          className="absolute right-4 top-1/2 z-20 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/60 backdrop-blur-sm opacity-0 transition-opacity hover:bg-black/60 hover:text-white hover:opacity-100 group-hover:opacity-100 md:opacity-40"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}

      {/* EXIF Panel */}
      <ExifPanel
        exifData={currentPhoto.exif_data}
        isOpen={exifOpen}
        onToggle={() => setExifOpen((o) => !o)}
      />

      {/* Thumbnail strip */}
      {hasAlbumContext && (
        <ThumbnailStrip
          photos={photos}
          currentIndex={currentIndex}
          onSelect={setCurrentIndex}
        />
      )}
    </div>
  );
};
