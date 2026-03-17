import type { Photo } from "@/services/photo/types/photoType";
import { getPhotoUrl } from "@/services/photo/utils/photoUrl";
import {
  Button,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  Spinner,
  useDisclosure,
} from "@heroui/react";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { useDeleteStoryMutation, useGetStoryQuery } from "../redux/api/storyApi";

export const StoryDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useGetStoryQuery(id!, { skip: !id });
  const [deleteStory, { isLoading: isDeleting }] = useDeleteStoryMutation();
  const { isOpen, onOpen, onOpenChange } = useDisclosure();

  const story = data?.data;

  const handleDelete = async () => {
    if (!id) return;
    try {
      await deleteStory(id).unwrap();
      navigate("/story", { replace: true });
    } catch {
      // error handled by RTK Query
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!story) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <p className="text-default-500">故事不存在</p>
        <Button variant="light" onPress={() => navigate("/story")} className="mt-4">
          返回列表
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between mb-6">
        <Button isIconOnly variant="light" onPress={() => navigate("/story")}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex gap-2">
          <Button
            isIconOnly
            variant="light"
            onPress={() => navigate(`/story/${id}/edit`)}
          >
            <Pencil className="w-5 h-5" />
          </Button>
          <Button isIconOnly variant="light" color="danger" onPress={onOpen}>
            <Trash2 className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* 照片横滚 */}
      {story.photos.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-4 mb-6">
          {story.photos.map((photo: Photo) => (
            <div
              key={photo.id}
              className="flex-shrink-0 h-[280px] rounded-xl overflow-hidden"
            >
              <img
                src={getPhotoUrl(photo)}
                alt=""
                className="h-full w-auto object-cover"
              />
            </div>
          ))}
        </div>
      )}

      {/* 标题 */}
      <h1 className="text-2xl font-bold mb-4">{story.title}</h1>

      {/* 时间 */}
      <p className="text-sm text-default-400 mb-6">
        {new Date(story.created_at).toLocaleDateString("zh-CN", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
      </p>

      {/* 正文 */}
      {story.content && (
        <div className="whitespace-pre-wrap text-default-700 leading-relaxed">
          {story.content}
        </div>
      )}

      {/* 删除确认弹窗 */}
      <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>确认删除</ModalHeader>
              <ModalBody>
                <p>确定要删除故事「{story.title}」吗？此操作不可撤销。</p>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  取消
                </Button>
                <Button color="danger" isLoading={isDeleting} onPress={handleDelete}>
                  删除
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
};
