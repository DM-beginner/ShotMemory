import type { GlobePhoto } from "../types/globeTypes";
import type { Photo } from "../types/photoType";
import { getPhotoUrl } from "./photoUrl";

export const toGlobePhotos = (photos: Photo[]): GlobePhoto[] =>
  photos
    .filter(
      (p): p is Photo & { location_wkt: NonNullable<Photo["location_wkt"]> } =>
        p.status === "completed" && p.location_wkt !== null
    )
    .map((p) => ({
      id: p.id,
      lng: p.location_wkt.coordinates[0],
      lat: p.location_wkt.coordinates[1],
      thumbnailUrl: getPhotoUrl(p),
      isLive: p.video_key !== null,
    }));
