import clsx from "clsx";
import { memo, useEffect, useRef } from "react";
import type { Photo } from "../types/photoType";
import { getPhotoUrl } from "../utils/photoUrl";

interface ThumbnailStripProps {
  photos: Photo[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export const ThumbnailStrip = memo(
  ({ photos, currentIndex, onSelect }: ThumbnailStripProps) => {
    const activeRef = useRef<HTMLButtonElement>(null);

    // biome-ignore lint/correctness/useExhaustiveDependencies: currentIndex is an intentional trigger
    useEffect(() => {
      activeRef.current?.scrollIntoView({
        behavior: "smooth",
        inline: "center",
        block: "nearest",
      });
    }, [currentIndex]);

    return (
      <div className="absolute inset-x-0 bottom-0 z-20 bg-black/50 backdrop-blur-sm px-4 py-2">
        <div className="flex gap-2 overflow-x-auto scrollbar-hide justify-center">
          {photos.map((photo, i) => (
            <button
              key={photo.id}
              ref={i === currentIndex ? activeRef : null}
              type="button"
              onClick={() => onSelect(i)}
              className={clsx(
                "shrink-0 w-16 h-16 rounded-md overflow-hidden transition-all duration-200",
                i === currentIndex
                  ? "ring-2 ring-primary scale-105"
                  : "opacity-60 hover:opacity-90"
              )}
            >
              <img
                src={getPhotoUrl(photo)}
                alt=""
                className="h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      </div>
    );
  }
);

ThumbnailStrip.displayName = "ThumbnailStrip";
