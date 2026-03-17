import type { BBox } from "geojson";
import { useCallback, useRef, useState } from "react";
import { Map as MapGL } from "react-map-gl/maplibre";
import type { MapRef, ViewStateChangeEvent } from "react-map-gl/maplibre";
import type { GlobePhoto, PhotoGlobeProps } from "../../types/globeTypes";
import { ClusterMarker } from "./ClusterMarker";
import { SingleMarker } from "./SingleMarker";
import { applyGlobeAtmosphere, globeStyle } from "./globeStyle";
import {
  type ClusterProperties,
  type PointProperties,
  useMapClusters,
} from "./useMapClusters";

const INITIAL_VIEW = {
  longitude: 116.4,
  latitude: 30,
  zoom: 2,
  pitch: 0,
  bearing: 0,
};

export const PhotoGlobe = ({ photos, onPhotoClick }: PhotoGlobeProps) => {
  const mapRef = useRef<MapRef>(null);
  const [bounds, setBounds] = useState<BBox | undefined>();
  const [zoom, setZoom] = useState(INITIAL_VIEW.zoom);

  const { clusters, supercluster } = useMapClusters({
    photos,
    bounds,
    zoom,
  });

  const updateViewport = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const b = map.getBounds();
    setBounds([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);
    setZoom(map.getZoom());
  }, []);

  const handleMoveEnd = useCallback(
    (_e: ViewStateChangeEvent) => updateViewport(),
    [updateViewport]
  );

  const handleClusterClick = useCallback(
    (clusterId: number, lng: number, lat: number) => {
      if (!supercluster) return;
      const expansionZoom = Math.min(
        supercluster.getClusterExpansionZoom(clusterId),
        18
      );
      mapRef.current?.flyTo({
        center: [lng, lat],
        zoom: expansionZoom,
        pitch: 45,
        duration: 1500,
      });
    },
    [supercluster]
  );

  const handleSingleClick = useCallback(
    (photo: GlobePhoto) => onPhotoClick(photo),
    [onPhotoClick]
  );

  return (
    <MapGL
      ref={mapRef}
      initialViewState={INITIAL_VIEW}
      mapStyle={globeStyle}
      projection={{ type: zoom > 5 ? "mercator" : "globe" }}
      style={{ width: "100%", height: "100%" }}
      onLoad={(e) => {
        applyGlobeAtmosphere(e.target);
        updateViewport();
      }}
      onMoveEnd={handleMoveEnd}
    >
      {clusters.map((feature) => {
        const [lng, lat] = feature.geometry.coordinates;
        const props = feature.properties;

        if (props.cluster) {
          return (
            <ClusterMarker
              key={`cluster-${feature.id}`}
              lng={lng}
              lat={lat}
              properties={props as ClusterProperties}
              onClick={() => handleClusterClick(feature.id as number, lng, lat)}
            />
          );
        }

        const { photo } = props as PointProperties;
        return (
          <SingleMarker
            key={`point-${photo.id}`}
            photo={photo}
            onClick={() => handleSingleClick(photo)}
          />
        );
      })}
    </MapGL>
  );
};
