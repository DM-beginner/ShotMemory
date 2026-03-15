type ExifData = Record<string, unknown>;

interface ExifField {
  label: string;
  value: string;
}

export interface ExifSection {
  title: string;
  fields: ExifField[];
}

// ── helpers ──

const str = (v: unknown): string | null => {
  if (v == null || v === "") return null;
  return String(v);
};

const fmt = (v: unknown, suffix = ""): string | null => {
  const s = str(v);
  return s ? `${s}${suffix}` : null;
};

// ── camera summary (shown below main photo) ──

export const formatCameraSummary = (exif: ExifData | null): string | null => {
  if (!exif) return null;

  const parts: string[] = [];

  const model = str(exif.Model);
  if (model) parts.push(model);

  const fl = str(exif.FocalLengthIn35mmFormat) ?? str(exif.FocalLength);
  if (fl) parts.push(`${fl}mm`);

  const fn = str(exif.FNumber);
  if (fn) parts.push(`f/${fn}`);

  const et = str(exif.ExposureTime);
  if (et) parts.push(`${et}s`);

  const iso = str(exif.ISO);
  if (iso) parts.push(`ISO ${iso}`);

  return parts.length > 0 ? parts.join(", ") : null;
};

// ── EXIF sections for side panel ──

const buildSection = (
  title: string,
  entries: [string, unknown][]
): ExifSection | null => {
  const fields = entries
    .filter(([, v]) => v != null && v !== "" && v !== false)
    .map(([label, value]) => ({ label, value: String(value) }));
  return fields.length > 0 ? { title, fields } : null;
};

export const getExifSections = (exif: ExifData | null): ExifSection[] => {
  if (!exif) return [];

  const sections: (ExifSection | null)[] = [
    buildSection("相机与镜头", [
      ["品牌", exif.Make],
      ["机型", exif.Model],
      ["制造商", exif.DeviceManufacturer],
      ["镜头品牌", exif.LensMake],
      ["镜头型号", exif.LensModel],
    ]),

    buildSection("曝光与光学", [
      ["焦距", fmt(exif.FocalLength, " mm")],
      ["等效焦距", fmt(exif.FocalLengthIn35mmFormat, " mm")],
      ["光圈", exif.FNumber != null ? `f/${exif.FNumber}` : null],
      ["快门速度", fmt(exif.ExposureTime, "s")],
      ["感光度", exif.ISO != null ? `ISO ${exif.ISO}` : null],
      ["曝光补偿", fmt(exif.ExposureCompensation, " EV")],
      ["视野角度", fmt(exif.FOV, "°")],
    ]),

    buildSection("拍摄模式", [
      ["曝光程序", exif.ExposureProgram],
      ["曝光模式", exif.ExposureMode],
      ["测光模式", exif.MeteringMode],
      ["白平衡", exif.WhiteBalance],
      ["光源", exif.LightSource],
      ["闪光灯", exif.Flash],
      ["场景类型", exif.SceneCaptureType],
    ]),

    buildSection("图像信息", [
      ["文件格式", exif.FileType],
      [
        "分辨率",
        exif.ImageWidth && exif.ImageHeight
          ? `${exif.ImageWidth} × ${exif.ImageHeight}`
          : null,
      ],
      ["像素", fmt(exif.Megapixels, " MP")],
      ["色彩空间", exif.ColorSpace],
      ["位深", fmt(exif.BitsPerSample, " bit")],
      ["色彩配置", exif.ProfileDescription],
      ["处理软件", exif.Software],
    ]),

    buildSection("时间", [
      ["拍摄时间", exif.DateTimeOriginal],
      ["时区", exif.OffsetTimeOriginal],
    ]),

    buildSection("位置", [
      ["纬度", exif.GPSLatitude],
      ["经度", exif.GPSLongitude],
      ["海拔", fmt(exif.GPSAltitude, " m")],
    ]),

    buildFujiRecipeSection(exif.FujiRecipe as ExifData | null),
    buildSonyRecipeSection(exif.SonyRecipe as ExifData | null),
  ];

  return sections.filter((s): s is ExifSection => s !== null);
};

// ── special recipe sections ──

const buildFujiRecipeSection = (recipe: ExifData | null): ExifSection | null => {
  if (!recipe) return null;
  return buildSection("富士配方", [
    ["胶片模拟", recipe.FilmMode],
    ["颗粒粗糙度", recipe.GrainEffectRoughness],
    ["颗粒大小", recipe.GrainEffectSize],
    ["彩色正片效果", recipe.ColorChromeEffect],
    ["蓝色正片效果", recipe.ColorChromeFxBlue ?? recipe.ColorChromeFXBlue],
    ["白平衡", recipe.WhiteBalance],
    ["动态范围", recipe.DynamicRange],
    ["高光色调", recipe.HighlightTone],
    ["阴影色调", recipe.ShadowTone],
    ["饱和度", recipe.Saturation],
    ["降噪", recipe.NoiseReduction],
    ["清晰度", recipe.Clarity],
  ]);
};

const buildSonyRecipeSection = (recipe: ExifData | null): ExifSection | null => {
  if (!recipe) return null;
  return buildSection("索尼外观", [
    ["创意风格", recipe.CreativeStyle],
    ["照片效果", recipe.PictureEffect],
    ["HDR", recipe.Hdr],
    ["柔肤效果", recipe.SoftSkinEffect],
  ]);
};
