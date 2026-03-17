import { useGetMyPhotosQuery } from "@/services/photo/redux/api/photoApi";
import type { Photo } from "@/services/photo/types/photoType";
import { getPhotoUrl } from "@/services/photo/utils/photoUrl";
import {
  Button,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
} from "@heroui/react";
import { Check } from "lucide-react";
import { useCallback, useState } from "react";

interface GalleryPickerModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedIds: string[];
  onConfirm: (ids: string[], photos: Photo[]) => void;
}

const MAX_PHOTOS = 9;

export const GalleryPickerModal = ({
  isOpen,
  onOpenChange,
  selectedIds,
  onConfirm,
}: GalleryPickerModalProps) => {
  const { data } = useGetMyPhotosQuery({ limit: 200, offset: 0 }, { skip: !isOpen });
  const photos = data?.data?.items ?? [];

  const [selected, setSelected] = useState<string[]>(selectedIds);

  // 每次打开时同步外部 selectedIds
  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (open) {
        setSelected(selectedIds);
      }
      onOpenChange(open);
    },
    [selectedIds, onOpenChange]
  );

  const togglePhoto = (photoId: string) => {
    setSelected((prev) => {
      if (prev.includes(photoId)) {
        return prev.filter((id) => id !== photoId);
      }
      if (prev.length >= MAX_PHOTOS) return prev;
      return [...prev, photoId];
    });
  };

  const getOrder = (photoId: string) => {
    const idx = selected.indexOf(photoId);
    return idx >= 0 ? idx + 1 : 0;
  };

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={handleOpenChange}
      size="4xl"
      scrollBehavior="inside"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader>选择照片</ModalHeader>
            <ModalBody>
              <div className="grid grid-cols-4 gap-2">
                {photos.map((photo: Photo) => {
                  const order = getOrder(photo.id);
                  const isSelected = order > 0;
                  return (
                    <button
                      type="button"
                      key={photo.id}
                      className="relative aspect-square overflow-hidden rounded-lg cursor-pointer group"
                      onClick={() => togglePhoto(photo.id)}
                    >
                      <img
                        src={getPhotoUrl(photo)}
                        alt=""
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                      {isSelected && (
                        <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                          <div className="absolute top-1 right-1 w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold">
                            {order}
                          </div>
                          <Check className="w-8 h-8 text-white drop-shadow-lg" />
                        </div>
                      )}
                      {!isSelected && selected.length < MAX_PHOTOS && (
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                      )}
                    </button>
                  );
                })}
              </div>
            </ModalBody>
            <ModalFooter>
              <span className="text-sm text-default-500 mr-auto">
                已选 {selected.length}/{MAX_PHOTOS}
              </span>
              <Button variant="light" onPress={onClose}>
                取消
              </Button>
              <Button
                color="primary"
                onPress={() => {
                  const photoMap = new Map(photos.map((p) => [p.id, p]));
                  onConfirm(
                    selected,
                    selected.map((id) => photoMap.get(id)).filter((p): p is Photo => p != null),
                  );
                  onClose();
                }}
              >
                确认
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};
