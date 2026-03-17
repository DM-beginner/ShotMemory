import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useGetMyPhotosQuery } from "../../redux/api/photoApi";
import type { GlobePhoto } from "../../types/globeTypes";
import { toGlobePhotos } from "../../utils/globeAdapter";
import { PhotoGlobe } from "./PhotoGlobe";

export const PhotoGlobePage = () => {
  const { data } = useGetMyPhotosQuery({ limit: 1000 });
  const navigate = useNavigate();

  const photos = data?.data ? toGlobePhotos(data.data.items) : [];

  const handlePhotoClick = useCallback(
    (photo: GlobePhoto) => navigate(`/photo/${photo.id}`),
    [navigate]
  );

  return (
    <div className="h-dvh w-dvw">
      <PhotoGlobe photos={photos} onPhotoClick={handlePhotoClick} />
    </div>
  );
};
