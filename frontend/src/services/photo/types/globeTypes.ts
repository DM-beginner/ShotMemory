export interface GlobePhoto {
  id: string;
  lng: number;
  lat: number;
  thumbnailUrl: string;
  isLive: boolean;
}

export interface PhotoGlobeProps {
  photos: GlobePhoto[];
  onPhotoClick: (photo: GlobePhoto) => void;
}
