import math
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    computed_field,
    model_validator,
)

from services.photo_story.schemas.exif_schema import (
    FujiRecipeType,
    PickedExif,
    SonyRecipeType,
)

# 预编译正则常量，大幅提升 CPU 执行效率
# 1. DECIMAL 模式
# group("value"): 匹配数值部分 (如 35.6762 或 -120)
# group("dir"): 匹配方向 (N, S, E, W)，可选
_DECIMAL_REGEX: Final[re.Pattern[str]] = re.compile(
    r"^(?P<value>[+-]?\d+(?:\.\d+)?)\s*"  # 数值部分
    r"(?P<dir>[NSEW])?$",  # 方向部分
    re.IGNORECASE,
)

# 2. DMS 模式
# 分别捕获度(deg)、分(min)、秒(sec)和方向(dir)
_DMS_REGEX: Final[re.Pattern[str]] = re.compile(
    r"^(?P<deg>[+-]?\d+(?:\.\d+)?)\s+deg\s+"  # 度部分
    r"(?P<min>\d+)\s*'\s*"  # 分部分
    r"(?P<sec>[\d.]+)\"\s*"  # 秒部分
    r"(?P<dir>[NSEW])?$",  # 方向部分
    re.IGNORECASE,
)


class ImageMetadata(BaseModel):
    """
    图片元数据模型。负责从展平的 EXIF 字典中安全地提取并清洗字段。
    """

    width: int = Field(default=0, description="图片宽度")
    height: int = Field(default=0, description="图片高度")
    latitude: float | None = Field(default=None, description="纬度（十进制）")
    longitude: float | None = Field(default=None, description="经度（十进制）")
    taken_at: datetime | None = Field(default=None, description="拍摄时间（带时区）")
    exif_data: dict[str, Any] = Field(
        default_factory=dict, description="业务裁剪后的 EXIF 字典"
    )

    @classmethod
    def _parse_datetime(cls, raw_time: Any, offset: str) -> datetime | None:
        """
        将 '2024:03:07 20:06:08' 转换为 Python datetime 对象，
        保留所有时间分量。
        """
        if not isinstance(raw_time, str) or not raw_time.strip():
            return None

        try:
            # 第一步：处理 EXIF 特有的冒号日期格式
            # 只替换前两个冒号（日期部分），保留后面的时分秒冒号
            # '2024:03:07 20:06:08' -> '2024-03-07 20:06:08'
            iso_date_part = raw_time.replace(":", "-", 2)

            # 第二步：处理时区偏移格式 (确保是 +HH:MM)
            # 某些相机可能只给 "+08"，需补全为 "+08:00"
            clean_offset = offset.strip()
            if len(clean_offset) == 3 and (
                clean_offset.startswith("+") or clean_offset.startswith("-")
            ):
                clean_offset += ":00"

            # 第三步：合成 ISO 8601 字符串
            # 结果示例: '2024-03-07T20:06:08+08:00'
            # 注意：T 是标准分隔符，空格也可以被 fromisoformat 识别
            full_iso_str = f"{iso_date_part.replace(' ', 'T')}{clean_offset}"

            return datetime.fromisoformat(full_iso_str)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _parse_gps(cls, value: Any, ref: Any = None) -> float | None:
        """解析复合 GPS 字符串为十进制浮点数。"""
        # --- 0. 辅助闭包：统一处理正负号 ---
        # 优先级：字符串内联方向 (如 "110 E") > 外部传入的 Ref (如 "East")
        clean_ref = str(ref).strip().upper()[0:1] if ref else None
        if clean_ref not in {"N", "S", "E", "W"}:
            clean_ref = None

        def solve_direction(val: float, direction: str | None = None) -> float:
            if direction in {"S", "W"}:
                return -abs(val)
            return abs(val) if direction in {"N", "E"} else val

        # --- 1. 前置过滤与预处理 ---
        if value in (None, ""):
            return None

        # 核心修复：即使 EXIF 直接给出了纯数字，也必须结合 Ref 处理方向！
        if isinstance(value, int | float):
            return (
                None
                if math.isnan(float(value)) or math.isinf(float(value))
                else solve_direction(float(value), clean_ref)
            )
        
        if not isinstance(value, str):
            return None

        # 清除两侧空格并统一转为大写，方便后续正则匹配（如 'n' -> 'N'）
        gps_str = value.strip().upper()

        # --- 2. 尝试匹配“纯十进制”格式 (例如: "110.6164 E") ---
        # 使用预定义的正则表达式检查是否是：数字 + 方向后缀
        # 1. 解析十进制格式
        if decimal_match := _DECIMAL_REGEX.match(gps_str):
            data = decimal_match.groupdict()
            return solve_direction(float(data["value"]), data.get("dir"))

        # 2. 解析度分秒 (DMS) 格式
        if dms_match := _DMS_REGEX.match(gps_str):
            data = dms_match.groupdict()
            degrees = float(data["deg"])
            minutes = float(data["min"])
            seconds = float(data["sec"])
            direction = data.get("dir")

            # 计算绝对值
            val = abs(degrees) + (minutes / 60.0) + (seconds / 3600.0)

            if degrees < 0 and not direction:
                direction = "S"  # 用 S 或 W 都可以，目的是触发 apply_sign 的变负逻辑

            return solve_direction(val, direction)
        return None

    @classmethod
    def _parse_exif_data(cls, data: Any) -> dict[str, Any]:
        """按业务需求提取和裁剪最终存入数据库的 EXIF 字典。"""

        def _safe_dump(
            model_cls: type[BaseModel], input_data: dict[str, Any]
        ) -> dict[str, Any]:
            try:
                # .model_validate() 校验成功后,调用 .model_dump() 将 Pydantic 对象转回普通字典
                return model_cls.model_validate(input_data).model_dump(
                    exclude_none=True
                )
            except ValidationError:
                return {}

        # 1. 提取兜底的基础 EXIF 数据字典
        base_exif_dict = _safe_dump(PickedExif, data)
        if not base_exif_dict:
            return {}

        # 2. 提取极其特殊的相机预设字典
        if data.get("FilmMode"):
            fuji_dict = _safe_dump(FujiRecipeType, data)
            if fuji_dict:
                base_exif_dict["FujiRecipe"] = fuji_dict

        elif data.get("CreativeStyle") is not None:
            sony_dict = _safe_dump(SonyRecipeType, data)
            if sony_dict:
                base_exif_dict["SonyRecipe"] = sony_dict

        return base_exif_dict

    @model_validator(mode="before")
    @classmethod
    def map_exif_keys(cls, data: Any) -> Any:
        """
        全局唯一入口：键映射、清洗与路由。
        """
        # mode="before" 意味着传入的 data 是最原始的数据（这里是字典）
        if not isinstance(data, dict):
            return data

        # 回退策略（Fallback）：按优先级依次尝试获取宽度、高度。
        width = (
            data.get("ExifImageWidth")
            or data.get("ImageWidth")
            or data.get("PixelXDimension")
            or 0
        )
        height = (
            data.get("ExifImageHeight")
            or data.get("ImageHeight")
            or data.get("PixelYDimension")
            or 0
        )

        lat_val = data.get("GPSLatitude")
        lat_ref = data.get("GPSLatitudeRef")

        lng_val = data.get("GPSLongitude")
        lng_ref = data.get("GPSLongitudeRef")

        raw_time = (
            data.get("DateTimeOriginal")
            or data.get("DateTimeDigitized")
            or data.get("CreateDate")
        )
        offset = data.get("OffsetTimeOriginal") or data.get("OffsetTime")

        # 最终组装
        return {
            "width": width,
            "height": height,
            "latitude": cls._parse_gps(lat_val, lat_ref),
            "longitude": cls._parse_gps(lng_val, lng_ref),
            "taken_at": cls._parse_datetime(raw_time, offset),
            "exif_data": cls._parse_exif_data(data),
        }


class PhotoUpdateRequest(BaseModel):
    """更新照片记录的请求"""

    exif_data: dict | None = Field(default=None, description="EXIF元数据")


class PhotoWorkerUpdate(BaseModel):
    """
    Worker 处理完成后回写数据库的专用载体。
    """

    width: int = Field(description="图片宽度(px)")
    height: int = Field(description="图片高度(px)")
    taken_at: datetime | None = Field(
        default=None, description="拍摄时间（从EXIF提取，无则为上传时间）"
    )
    exif_data: dict | None = Field(
        default=None, description="完整EXIF元数据，无则为 None"
    )
    thumbnail_key: str | None = Field(
        default=None, description="WebP 缩略图访问路径"
    )
    location_wkt: str | None = Field(
        default=None, description="PostGIS WKT 格式坐标，无 GPS 则为 None"
    )


class PhotoProcessStatus(StrEnum):
    """前端契约枚举：严格收束可能出现的状态"""

    PROCESSING = "processing"  # 正在处理中
    COMPLETED = "completed"  # 处理完毕，有数据
    NO_EXIF = "no_exif"  # 处理完毕，无 EXIF 数据


class PhotoResponse(BaseModel):
    """照片信息响应"""

    id: UUID = Field(description="照片ID")
    user_id: UUID = Field(description="所属用户ID")
    object_key: str = Field(description="OSS相对路径")
    thumbnail_key: str | None = Field(default=None, description="WebP 缩略图访问 URL")
    width: int = Field(description="图片宽度")
    height: int = Field(description="图片高度")
    location_wkt: dict | None = Field(default=None, description="地理位置 {lat, lng}")
    exif_data: dict | None = Field(default=None, description="EXIF元数据")
    taken_at: datetime = Field(description="拍摄时间")
    created_at: datetime = Field(description="上传时间")

    model_config = {"from_attributes": True}

    @computed_field(description="基于 exif_data 动态推导的隐式状态，绝不落盘")
    @property
    def status(self) -> PhotoProcessStatus:
        """
        状态机推导逻辑：
        一旦被调用，瞬间根据 exif_data 的特征返回强类型状态。
        """
        if self.exif_data is None:
            # 数据库里是 null，说明 Worker 还没更新
            return PhotoProcessStatus.PROCESSING

        if not self.exif_data:
            # 数据库里是 {} (空字典)，说明 Worker 找了一圈发现没 EXIF
            return PhotoProcessStatus.NO_EXIF

        # 剩下的情况绝对是有实际数据的字典
        return PhotoProcessStatus.COMPLETED


class PhotoListResponse(BaseModel):
    """照片列表响应"""

    total: int = Field(description="总数量")
    items: list[PhotoResponse] = Field(description="照片列表")
