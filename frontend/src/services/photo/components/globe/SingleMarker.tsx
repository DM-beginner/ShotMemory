import { Marker } from "react-map-gl/maplibre";
import type { GlobePhoto } from "../../types/globeTypes";

interface SingleMarkerProps {
  photo: GlobePhoto;
  onClick: () => void;
}

export const SingleMarker = ({ photo, onClick }: SingleMarkerProps) => (
  <Marker longitude={photo.lng} latitude={photo.lat}>
    <button
      type="button"
      className="group relative h-11 w-11 cursor-pointer overflow-hidden rounded-lg border-2 border-white shadow-md transition-transform hover:scale-110"
      onClick={onClick}
    >
      <img
        src={photo.thumbnailUrl}
        alt="marker"
        className="h-full w-full object-cover"
        loading="lazy"
      />
      {photo.isLive && (
        <span className="absolute left-0.5 top-0.5 flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
        </span>
      )}
    </button>
  </Marker>
);
