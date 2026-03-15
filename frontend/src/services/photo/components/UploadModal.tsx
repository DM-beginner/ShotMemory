import {
  Button,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  Progress,
} from "@heroui/react";
import { ImagePlus, Upload, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import type { DragEvent } from "react";
import { useUploadPhotosMutation } from "../redux/api/photoApi";

const ALLOWED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "image/avif",
  "video/quicktime",
]);

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

interface FilePreview {
  file: File;
  previewUrl: string | null;
}

interface UploadModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

export const UploadModal = ({ isOpen, onOpenChange }: UploadModalProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [previews, setPreviews] = useState<FilePreview[]>([]);
  const [error, setError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploadMutation, { isLoading: isUploading }] = useUploadPhotosMutation({
    fixedCacheKey: "photo-upload",
  });

  const addFiles = useCallback((incoming: File[]) => {
    setError("");
    const valid: FilePreview[] = [];
    for (const file of incoming) {
      if (!ALLOWED_TYPES.has(file.type)) {
        setError(
          `不支持的文件类型：${file.name}（仅支持 JPEG/PNG/WebP/HEIC/HEIF/AVIF/MOV）`
        );
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setError(`文件过大：${file.name}（最大 50MB）`);
        return;
      }
      const previewUrl = file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : null;
      valid.push({ file, previewUrl });
    }
    setPreviews((prev) => {
      const existingNames = new Set(prev.map((p) => p.file.name));
      return [...prev, ...valid.filter((v) => !existingNames.has(v.file.name))];
    });
  }, []);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  };

  const handleInputChange = () => {
    const files = Array.from(inputRef.current?.files ?? []);
    addFiles(files);
    if (inputRef.current) inputRef.current.value = "";
  };

  const removeFile = (index: number) => {
    setPreviews((prev) => {
      const next = [...prev];
      const removed = next.splice(index, 1)[0];
      if (removed.previewUrl) URL.revokeObjectURL(removed.previewUrl);
      return next;
    });
  };

  const handleClose = (open: boolean) => {
    if (!isUploading) {
      for (const p of previews) {
        if (p.previewUrl) URL.revokeObjectURL(p.previewUrl);
      }
      setPreviews([]);
      setError("");
      setUploadProgress(0);
      onOpenChange(open);
    }
  };

  const handleSubmit = async () => {
    if (!previews.length) return;
    setError("");

    // 模拟进度（RTK Query 不原生支持 upload progress）
    const progressInterval = setInterval(() => {
      setUploadProgress((p) => (p < 85 ? p + 5 : p));
    }, 200);

    try {
      await uploadMutation(previews.map((p) => p.file)).unwrap();
      clearInterval(progressInterval);
      setUploadProgress(100);
      setTimeout(() => handleClose(false), 500);
    } catch {
      clearInterval(progressInterval);
      setUploadProgress(0);
      setError("上传失败，请重试");
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={handleClose}
      size="2xl"
      placement="center"
      backdrop="blur"
      isDismissable={!isUploading}
      hideCloseButton={isUploading}
    >
      <ModalContent>
        {() => (
          <>
            <ModalHeader className="flex flex-col gap-1">
              <span className="font-display text-lg">上传照片</span>
              <span className="text-sm font-normal text-default-500">
                支持 JPEG / PNG / WebP / HEIC / HEIF / AVIF / MOV（实况照片），单张最大
                50MB，单次最多 50 张
              </span>
            </ModalHeader>

            <ModalBody className="gap-4">
              {/* 拖拽区域 */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                // 💡 3. 补充键盘事件：按下回车或空格时，等同于点击
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault(); // 阻止空格键默认向下滚动网页的行为
                    inputRef.current?.click();
                  }
                }}
                className={[
                  "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed",
                  // 💡 顺手加上 focus-visible 样式，让键盘聚焦时有一圈漂亮的高亮轮廓
                  "cursor-pointer py-10 transition-colors duration-200 select-none focus-visible:outline-2 focus-visible:outline-primary",
                  isDragging
                    ? "border-primary bg-primary/5 scale-[1.01]"
                    : "border-default-300 hover:border-primary/60 hover:bg-default-50",
                ].join(" ")}
              >
                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  accept={[...ALLOWED_TYPES].join(",")}
                  className="hidden"
                  // 注意：用 onChange 处理文件选择没问题，记得保留你的 handleInputChange
                  onChange={handleInputChange}
                />
                {isDragging ? (
                  <ImagePlus className="w-10 h-10 text-primary animate-bounce" />
                ) : (
                  <Upload className="w-10 h-10 text-default-400" />
                )}
                <p className="text-sm text-default-500">
                  {isDragging ? "松开以添加文件" : "拖拽照片到此处，或点击选择文件"}
                </p>
              </div>

              {/* 错误提示 */}
              {error && <p className="text-sm text-danger px-1">{error}</p>}

              {/* 文件预览列表 */}
              {previews.length > 0 && (
                <div className="flex flex-col gap-2 max-h-60 overflow-y-auto pr-1">
                  <p className="text-xs text-default-400 px-1">
                    已选择 {previews.length} 张
                  </p>
                  {previews.map((item, idx) => (
                    <div
                      key={`${item.file.name}-${item.file.size}`}
                      className="flex items-center gap-3 rounded-lg bg-default-50 px-3 py-2"
                    >
                      {item.previewUrl ? (
                        <img
                          src={item.previewUrl}
                          alt={item.file.name}
                          className="w-10 h-10 rounded-md object-cover shrink-0"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-md bg-default-200 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{item.file.name}</p>
                        <p className="text-xs text-default-400">
                          {formatBytes(item.file.size)}
                        </p>
                      </div>
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        isDisabled={isUploading}
                        onPress={() => removeFile(idx)}
                        aria-label="移除"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* 上传进度 */}
              {isUploading && (
                <Progress
                  value={uploadProgress}
                  size="sm"
                  color="primary"
                  label="上传中..."
                  showValueLabel
                  className="animate-fade-in"
                />
              )}
            </ModalBody>

            <ModalFooter>
              <Button
                variant="flat"
                onPress={() => handleClose(false)}
                isDisabled={isUploading}
              >
                取消
              </Button>
              <Button
                color="primary"
                onPress={handleSubmit}
                isLoading={isUploading}
                isDisabled={!previews.length || isUploading}
                startContent={!isUploading && <Upload className="w-4 h-4" />}
              >
                {isUploading ? "上传中" : `上传 ${previews.length || ""} 张`}
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};
