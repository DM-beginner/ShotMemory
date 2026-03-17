import type { Photo } from "@/services/photo/types/photoType";
import { getPhotoUrl } from "@/services/photo/utils/photoUrl";
import { Button, Input, Textarea } from "@heroui/react";
import { ArrowLeft, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  useCreateStoryMutation,
  useGetStoryQuery,
  useUpdateStoryMutation,
} from "../redux/api/storyApi";
import { GalleryPickerModal } from "./GalleryPickerModal";

export const StoryEditor = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const { data: storyData } = useGetStoryQuery(id!, { skip: !isEdit });
  const story = storyData?.data;

  const [createStory, { isLoading: isCreating }] = useCreateStoryMutation();
  const [updateStory, { isLoading: isUpdating }] = useUpdateStoryMutation();

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [photoIds, setPhotoIds] = useState<string[]>([]);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  // 编辑模式：加载已有数据
  useEffect(() => {
    if (story) {
      setTitle(story.title);
      setContent(story.content ?? "");
      setPhotoIds(story.photos.map((p) => p.id));
      setPhotos(story.photos);
    }
  }, [story]);

  const handlePickerConfirm = (ids: string[], selectedPhotos: Photo[]) => {
    setPhotoIds(ids);
    setPhotos(selectedPhotos);
  };

  const removePhoto = (photoId: string) => {
    setPhotoIds((prev) => prev.filter((id) => id !== photoId));
    setPhotos((prev) => prev.filter((p) => p.id !== photoId));
  };

  const handleSubmit = async () => {
    if (!title.trim()) return;
    try {
      if (isEdit && id) {
        await updateStory({
          id,
          title,
          content: content || undefined,
          photo_ids: photoIds,
        }).unwrap();
        navigate(`/story/${id}`);
      } else {
        const result = await createStory({
          title,
          content: content || undefined,
          photo_ids: photoIds,
        }).unwrap();
        navigate(`/story/${result.data.id}`);
      }
    } catch {
      // error handled by RTK Query
    }
  };

  const isLoading = isCreating || isUpdating;

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <Button isIconOnly variant="light" onPress={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <h1 className="text-xl font-bold">{isEdit ? "编辑故事" : "新建故事"}</h1>
      </div>

      {/* 照片选择区 */}
      <div className="mb-6">
        <div className="flex gap-3 overflow-x-auto pb-2" style={{ minHeight: 200 }}>
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="relative flex-shrink-0 h-[200px] aspect-[3/4] rounded-lg overflow-hidden"
            >
              <img
                src={getPhotoUrl(photo)}
                alt=""
                className="w-full h-full object-cover"
              />
              <button
                type="button"
                className="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"
                onClick={() => removePhoto(photo.id)}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          <button
            type="button"
            className="flex-shrink-0 h-[200px] w-[150px] rounded-lg border-2 border-dashed border-default-300 flex items-center justify-center hover:border-primary transition-colors cursor-pointer"
            onClick={() => setIsPickerOpen(true)}
          >
            <Plus className="w-8 h-8 text-default-400" />
          </button>
        </div>
      </div>

      {/* 标题 */}
      <Input
        label="标题"
        placeholder="给故事起个名字"
        value={title}
        onValueChange={setTitle}
        className="mb-4"
        maxLength={255}
      />

      {/* 正文 */}
      <Textarea
        label="正文"
        placeholder="记录你的故事..."
        value={content}
        onValueChange={setContent}
        minRows={4}
        className="mb-6"
      />

      {/* 发布按钮 */}
      <Button
        color="primary"
        className="w-full"
        isLoading={isLoading}
        isDisabled={!title.trim()}
        onPress={handleSubmit}
      >
        {isEdit ? "保存" : "发布"}
      </Button>

      <GalleryPickerModal
        isOpen={isPickerOpen}
        onOpenChange={setIsPickerOpen}
        selectedIds={photoIds}
        onConfirm={handlePickerConfirm}
      />
    </div>
  );
};
