from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class UploadResponseData(BaseModel):
    """文件上传成功后的响应数据"""

    url: str = Field(description="文件访问 URL")
    filename: str = Field(description="原始文件名")


class PhotoCreateRequest(BaseModel):
    """创建照片记录的请求"""

    object_key: str = Field(description="OSS中的相对路径")
    width: int = Field(description="图片宽度(px)", gt=0)
    height: int = Field(description="图片高度(px)", gt=0)
    latitude: float | None = Field(default=None, description="纬度", ge=-90, le=90)
    longitude: float | None = Field(default=None, description="经度", ge=-180, le=180)
    exif_data: dict | None = Field(default=None, description="EXIF元数据")
    taken_at: datetime | None = Field(default=None, description="拍摄时间")


class PhotoUpdateRequest(BaseModel):
    """更新照片记录的请求"""

    exif_data: dict | None = Field(default=None, description="EXIF元数据")


class PhotoResponse(BaseModel):
    """照片信息响应"""

    id: UUID = Field(description="照片ID")
    user_id: UUID = Field(description="所属用户ID")
    object_key: str = Field(description="OSS相对路径")
    width: int = Field(description="图片宽度")
    height: int = Field(description="图片高度")
    location: dict | None = Field(default=None, description="地理位置 {lat, lng}")
    exif_data: dict | None = Field(default=None, description="EXIF元数据")
    taken_at: datetime = Field(description="拍摄时间")
    created_at: datetime = Field(description="上传时间")

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_location(cls, data: Any) -> Any:
        """将 PostGIS WKBElement 转换为 dict"""
        if isinstance(data, dict) and "location" in data:
            location = data["location"]
            # 如果是 WKBElement 对象（GeoAlchemy2 返回的类型）
            if location is not None and hasattr(location, "desc"):
                try:
                    # 解析 WKT 格式：POINT(longitude latitude)
                    from geoalchemy2.shape import to_shape

                    point = to_shape(location)
                    data["location"] = {"lng": point.x, "lat": point.y}
                except Exception:
                    # 解析失败则设为 None
                    data["location"] = None
        return data


class PhotoListResponse(BaseModel):
    """照片列表响应"""

    total: int = Field(description="总数量")
    items: list[PhotoResponse] = Field(description="照片列表")
