import { Marker } from "react-map-gl/maplibre";
import type { ClusterProperties } from "./useMapClusters";

interface ClusterMarkerProps {
  lng: number;
  lat: number;
  properties: ClusterProperties;
  onClick: () => void;
}

export const ClusterMarker = ({
  lng,
  lat,
  properties,
  onClick,
}: ClusterMarkerProps) => {
  const count = properties.point_count;

  return (
    <Marker longitude={lng} latitude={lat}>
      <button
        type="button"
        className="group relative h-14 w-14 cursor-pointer overflow-hidden rounded-lg border-2 border-white shadow-lg transition-transform hover:scale-110"
        onClick={onClick}
      >
        <img
          src={properties.thumbnailUrl}
          alt={`${count} photos`}
          className="h-full w-full object-cover"
          loading="lazy"
        />
        <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
          {count > 99 ? "99+" : count}
        </span>
      </button>
    </Marker>
  );
};
