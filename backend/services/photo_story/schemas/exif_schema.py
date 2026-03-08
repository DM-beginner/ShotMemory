from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FujiRecipeType(BaseModel):
    """富士胶片模拟配方 (简洁版)"""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    FilmMode: str | int | None = None  # 胶片模拟模式
    GrainEffectRoughness: str | int | None = None  # 颗粒粗糙度
    GrainEffectSize: str | int | None = None  # 颗粒大小
    ColorChromeEffect: str | int | None = None  # 彩色正片效果
    ColorChromeFxBlue: str | int | None = Field(
        None, alias="ColorChromeFXBlue"
    )  # 蓝色正片效果
    WhiteBalance: str | int | None = None  # 白平衡设定
    DynamicRange: str | int | None = None  # 动态范围 (DR100/200/400)
    HighlightTone: str | int | float | None = None  # 高光色调
    ShadowTone: str | int | float | None = None  # 阴影色调
    Saturation: str | int | None = None  # 饱和度
    NoiseReduction: str | int | None = None  # 高 ISO 降噪
    Clarity: str | int | None = None  # 清晰度
    ColorTemperature: str | int | None = None  # 手动色温值
    DevelopmentDynamicRange: str | int | None = None  # 显影动态范围
    DynamicRangeSetting: str | int | None = None  # 动态范围设置项


class SonyRecipeType(BaseModel):
    """索尼创意外观与图像设置"""

    model_config = ConfigDict(extra="ignore")

    CreativeStyle: str | int | None = None  # 创意风格
    PictureEffect: str | int | None = None  # 照片效果
    Hdr: str | int | None = None  # HDR 设定
    SoftSkinEffect: str | int | None = None  # 柔肤效果
    SonyCreativeStyle: str | int | None = None  # 索尼专属外观
    SonyToneCurve: str | int | None = None  # 色调曲线


class PickedExif(BaseModel):
    """清洗后的 EXIF 数据模型 (适配前端展示)"""

    model_config = ConfigDict(extra="ignore")

    # ==========================================
    # 模块 1: 图像基础
    # ==========================================
    FileType: str | None = None  # 文件格式 (JPEG/HEIC)
    ImageWidth: int | None = None  # 图像宽度 (px)
    ImageHeight: int | None = None  # 图像高度 (px)
    Megapixels: float | None = None  # 像素总量 (MP)
    BitsPerSample: int | None = None  # 色彩位深 (Bit)
    ColorSpace: str | int | None = None  # 色彩空间 (sRGB/AdobeRGB)
    ProfileDescription: str | None = None  # 色彩配置文件 (Display P3)
    Software: str | None = None  # 后期处理软件

    # ==========================================
    # 模块 2: 时间与精度
    # ==========================================
    DateTimeOriginal: str | None = None  # 拍摄时间
    DateTimeDigitized: str | None = None  # 数字化时间
    OffsetTimeOriginal: str | None = None  # 拍摄时区 (如 +08:00)
    SubSecTimeOriginal: str | int | None = None  # 拍摄毫秒级时间戳

    # ==========================================
    # 模块 3: 硬件信息
    # ==========================================
    Make: str | None = None  # 品牌 (Apple/OPPO)
    Model: str | None = None  # 机型
    DeviceManufacturer: str | None = None  # 制造商
    LensMake: str | None = None  # 镜头品牌
    LensModel: str | None = None  # 镜头型号

    # ==========================================
    # 模块 4: 曝光与光学
    # ==========================================
    FocalLength: float | str | None = None  # 物理焦距 (mm)
    FocalLengthIn35mmFormat: int | str | float | None = None  # 等效焦距 (mm)
    FNumber: float | str | None = None  # 光圈系数 (f/N)
    ExposureTime: float | str | None = None  # 曝光时间 (秒)
    ISO: int | str | None = None  # 感光度
    ExposureCompensation: float | str | int | None = None  # 曝光补偿 (EV)
    ApertureValue: float | str | None = None  # APEX 光圈值
    ShutterSpeedValue: float | str | None = None  # APEX 快门值
    DigitalZoomRatio: float | None = None  # 数码变焦倍率
    FOV: str | None = None  # 视野角度 (Field of View)

    # ==========================================
    # 模块 5: 拍摄模式与光影
    # ==========================================
    ExposureProgram: str | int | None = None  # 曝光程序 (P/A/S/M)
    ExposureMode: str | int | None = None  # 曝光模式 (Auto/Manual)
    MeteringMode: str | int | None = None  # 测光模式 (Center/Spot)
    WhiteBalance: str | int | None = None  # 白平衡 (Auto/Manual)
    LightSource: str | int | None = None  # 光源类型 (D65/Daylight)
    Flash: str | int | None = None  # 闪光灯状态
    BrightnessValue: float | None = None  # APEX 亮度值 测光表读取的环境亮度值。用于计算曝光补偿。
    LightValue: float | None = None  # 环境光亮度 (LV)
    SceneCaptureType: str | int | None = None  # 场景类型 (Landscape/Night)

    # ==========================================
    # 模块 6: 空间与技术参数
    # ==========================================
    SensingMethod: str | int | None = None  # 传感器成像方法
    HyperfocalDistance: str | None = None  # 超焦距距离 (m)
    CircleOfConfusion: str | None = None  # 弥散圆直径 (mm)

    # ==========================================
    # 模块 7: 动态照片与计算摄影
    # ==========================================
    MotionPhoto: int | str | None = None  # 动态照片标记 (Samsung/OPPO)
    MotionPhotoVersion: str | int | None = None  # 动态照片协议版本
    MotionPhotoPresentationTimestampUs: int | str | None = None  # 视频时间戳
    MicroVideo: int | str | None = None  # 微视频标记 (Google)
    GainMap: bool | None = False  # HDR 增益图标识 (Ultra HDR)
    MPImageType: str | int | None = None  # 多图封装类型
    NumberOfImages: int | None = None  # 容器内图像数量
    

    # ==========================================
    # 模块 8: 位置信息 (GPS)
    # ==========================================
    GPSLatitude: float | str | None = None  # 纬度
    GPSLatitudeRef: str | None = None  # 纬度参考 (N/S)
    GPSLongitude: float | str | None = None  # 经度
    GPSLongitudeRef: str | None = None  # 经度参考 (E/W)
    GPSAltitude: float | str | None = None  # 海拔高度 (m)

    # ==========================================
    # 嵌套结构
    # ==========================================
    FujiRecipe: FujiRecipeType | None = None  # 富士专属配方
    SonyRecipe: SonyRecipeType | None = None  # 索尼专属外观

    # ==========================================
    # 自动转换校验器 (Validators)
    # ==========================================

    @field_validator("ColorSpace", mode="before")
    @classmethod
    def translate_color_space(cls, v: Any) -> str | None:
        """翻译色彩空间数值"""
        if v is None:
            return None
        mapping = {1: "sRGB", 2: "Adobe RGB", 65535: "Uncalibrated"}
        return mapping.get(v, str(v)) if isinstance(v, int) else str(v)

    @field_validator("ExposureProgram", mode="before")
    @classmethod
    def translate_exposure_program(cls, v: Any) -> str | None:
        """翻译曝光程序数值"""
        if v is None:
            return None
        mapping = {
            1: "Manual (M)",
            2: "Program AE (P)",
            3: "Aperture-priority (A)",
            4: "Shutter-priority (S)",
            8: "Landscape",
            9: "Portrait",
        }
        return mapping.get(v, str(v)) if isinstance(v, int) else str(v)

    @field_validator("MeteringMode", mode="before")
    @classmethod
    def translate_metering_mode(cls, v: Any) -> str | None:
        """翻译测光模式数值"""
        if v is None:
            return None
        mapping = {1: "Average", 2: "Center-weighted", 3: "Spot", 5: "Multi-segment"}
        return mapping.get(v, str(v)) if isinstance(v, int) else str(v)

    @field_validator("LightSource", mode="before")
    @classmethod
    def translate_light_source(cls, v: Any) -> str | None:
        """翻译光源类型数值"""
        if v is None:
            return None
        mapping = {1: "Daylight", 3: "Tungsten", 21: "D65"}
        return mapping.get(v, str(v)) if isinstance(v, int) else str(v)

    @field_validator("Flash", mode="before")
    @classmethod
    def translate_flash(cls, v: Any) -> str | None:
        """翻译闪光灯标记 (如 16 -> Off)"""
        if v is None:
            return None
        if v == 16 or str(v) == "16":
            return "Off"
        return str(v)

    @field_validator("GainMap", mode="before")
    @classmethod
    def check_gain_map(cls, v: Any) -> bool:
        """识别是否具备 HDR 增益图"""
        if v is None:
            return False
        return True if "GainMap" in str(v) else bool(v)

    @field_validator("ExposureTime", mode="before")
    @classmethod
    def format_exposure_time(cls, v: Any) -> str | None:
        """转换曝光时间为分数形式 (如 0.02 -> 1/50)"""
        if v is None:
            return None
        if isinstance(v, float) and 0 < v < 1:
            return f"1/{round(1 / v)}"
        return str(v)


