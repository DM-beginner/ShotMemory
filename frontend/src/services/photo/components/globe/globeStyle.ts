import type { Map as MaplibreMap, StyleSpecification } from "maplibre-gl";

export const globeStyle: StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
    },
  },
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#0d1b2a" },
    },
    {
      id: "carto-tiles",
      type: "raster",
      source: "carto",
      minzoom: 0,
      maxzoom: 20,
    },
  ],
};

export const applyGlobeAtmosphere = (map: MaplibreMap) => {
  map.setSky({
    "sky-color": "#061830",
    "horizon-color": "#1a3a5c",
    "fog-color": "#0a1628",
    "atmosphere-blend": 0.8,
    "sky-horizon-blend": 0.5,
    "fog-ground-blend": 0.7,
    "horizon-fog-blend": 0.5,
  });
};
