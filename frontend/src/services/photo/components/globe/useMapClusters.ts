import type { BBox } from "geojson";
import { useMemo } from "react";
import type { PointFeature } from "supercluster";
import useSupercluster from "use-supercluster";
import type { GlobePhoto } from "../../types/globeTypes";

export type ClusterProperties = {
  cluster: true;
  point_count: number;
  thumbnailUrl: string;
};

export type PointProperties = {
  cluster: false;
  photo: GlobePhoto;
};

export type MarkerFeature = PointFeature<ClusterProperties | PointProperties>;

interface UseMapClustersOptions {
  photos: GlobePhoto[];
  bounds: BBox | undefined;
  zoom: number;
}

export const useMapClusters = ({ photos, bounds, zoom }: UseMapClustersOptions) => {
  const points = useMemo<PointFeature<PointProperties>[]>(
    () =>
      photos.map((p) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
        properties: { cluster: false as const, photo: p },
      })),
    [photos]
  );

  const { clusters, supercluster } = useSupercluster<
    ClusterProperties | PointProperties
  >({
    points,
    bounds,
    zoom,
    options: {
      radius: 75,
      maxZoom: 18,
      map: (props) => ({
        thumbnailUrl: (props as PointProperties).photo?.thumbnailUrl ?? "",
      }),
      reduce: (acc, props) => {
        if (!acc.thumbnailUrl) acc.thumbnailUrl = props.thumbnailUrl;
      },
    },
  });

  return { clusters: clusters as MarkerFeature[], supercluster };
};
