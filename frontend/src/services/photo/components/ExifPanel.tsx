import clsx from "clsx";
import { Info, PanelRightClose } from "lucide-react";
import { memo, useEffect, useRef } from "react";
import { type ExifSection, getExifSections } from "../utils/exifFormat";

interface ExifPanelProps {
  exifData: Record<string, unknown> | null;
  isOpen: boolean;
  onToggle: () => void;
}

export const ExifPanel = memo(({ exifData, isOpen, onToggle }: ExifPanelProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const sections = getExifSections(exifData);

  // biome-ignore lint/correctness/useExhaustiveDependencies: exifData is an intentional trigger
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [exifData]);

  return (
    <>
      {/* Toggle button — always visible */}
      <button
        type="button"
        onClick={onToggle}
        className={clsx(
          "absolute top-4 z-30 flex items-center justify-center",
          "h-10 w-10 rounded-full bg-black/50 text-white/80 backdrop-blur-sm",
          "transition-all duration-300 hover:bg-black/70 hover:text-white",
          isOpen ? "right-[21rem]" : "right-4"
        )}
        title={isOpen ? "收起信息" : "照片信息 (i)"}
      >
        {isOpen ? (
          <PanelRightClose className="h-5 w-5" />
        ) : (
          <Info className="h-5 w-5" />
        )}
      </button>

      {/* Panel */}
      <div
        className={clsx(
          "absolute top-0 right-0 z-20 h-full w-80",
          "bg-black/70 backdrop-blur-md text-white/90",
          "transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div
          ref={scrollRef}
          className="h-full overflow-y-auto px-5 pt-16 pb-24 scrollbar-hide"
        >
          {sections.length === 0 ? (
            <p className="text-sm text-white/40 mt-8 text-center">暂无 EXIF 数据</p>
          ) : (
            sections.map((section) => (
              <SectionBlock key={section.title} section={section} />
            ))
          )}
        </div>
      </div>
    </>
  );
});

ExifPanel.displayName = "ExifPanel";

const SectionBlock = ({ section }: { section: ExifSection }) => (
  <div className="mb-5">
    <h3 className="text-xs font-semibold uppercase tracking-wider text-white/50 mb-2">
      {section.title}
    </h3>
    <div className="space-y-1.5">
      {section.fields.map((field) => (
        <div key={field.label} className="flex justify-between text-sm gap-4">
          <span className="text-white/50 shrink-0">{field.label}</span>
          <span className="text-white/90 text-right truncate">{field.value}</span>
        </div>
      ))}
    </div>
  </div>
);
