import json
from collections import defaultdict
from pathlib import Path
import pprint
from typing import Any

from exiftool import ExifToolHelper
from loguru import logger

# 排除的二进制大字段（base64 编码的缩略图/预览图，单个可达几十 KB）
_BINARY_KEYS: frozenset[str] = frozenset(
    {
        "ThumbnailImage",
        "PreviewImage",
        "JpgFromRaw",
        "OtherImage",
        "MPImage1",
        "MPImage2",
        "PreviewTIFF",
        "PreviewIPTC",
    }
)

# 命名空间优先级：索引越小优先级越高
# EXIF 优先（相机原始数据），Composite 提供已转换的 GPS 十进制值
# XMP/IPTC 可能含后期编辑值，优先级靠后（已进行倒序）
_NS_PRIORITY: tuple[str, ...] = (
    "ExifTool",
    "File",
    "IPTC",
    "XMP",
    "MakerNotes",
    "Composite",
    "EXIF",
)
_PRIORITY_SET: frozenset[str] = frozenset(_NS_PRIORITY)

def _flatten_by_priority(raw: dict[str, Any]) -> dict[str, Any]:
    """
    按命名空间优先级展平字典。
    采用"从低到高依次覆盖"的策略，利用原生的 dict.update() 实现极致性能。
    """
    ns_buckets: dict[str, dict[str, Any]] = defaultdict(dict)
    flat: dict[str, Any] = {}

    for full_key, value in raw.items():
        if ":" in full_key:
            ns, tag = full_key.split(":", 1)
            ns_buckets[ns][tag] = value
        else:
            # 1. 最底层的垫脚石：没有命名空间的标签（优先级最低）
            flat[full_key] = value

    # 2. 中层：未知命名空间（厂家自定义黑话），覆盖掉无命名的标签
    for ns, bucket in ns_buckets.items():
        if ns not in _PRIORITY_SET:
            # update 方法用于将一个字典的键值对“批量”加入到 flat 字典。如果有重复的 key，会覆盖掉原有的值。
            # 具体来说：flat.update(bucket) 会把 bucket（一个命名空间下所有键值对）全部合并到 flat。
            # 比如 flat 里已经有 "ImageWidth": 1000，bucket 里也有 "ImageWidth": 2000，调用 update 后 flat 的 "ImageWidth" 就会变成 2000。
            flat.update(bucket)

    # 3. 顶层：官方高优命名空间（精华所在）
    # 我们使用 reversed() 倒序遍历！
    # 比如列表是 [EXIF, Composite, XMP]
    # 倒序后变成 [XMP, Composite, EXIF]
    # XMP 先写入，Composite 覆盖 XMP，最后 EXIF 绝对王权，覆盖掉前面所有同名标签！
    for ns in _NS_PRIORITY:
        if ns in ns_buckets:
            flat.update(ns_buckets[ns])

    return flat


def print_raw_exif(image_path: str | Path) -> None:
    """
    使用 ExifTool 提取并打印图片的完整原始元数据。

    参数说明：
        -G1: 显示详细的命名空间（如 [IFD0], [ExifIFD]）
        -a: 允许显示重复的标签名
        -s: 显示实际的键名而非描述文字
    """
    path = Path(image_path)
    if not path.exists():
        logger.error(f"文件不存在: {path}")
        return

    logger.info(f"正在解析: {path.name}")

    try:
        # 使用 ExifToolHelper，这要求你系统已安装 exiftool 命令行工具
        with ExifToolHelper() as et:
            # 获取元数据。-G1 会返回类似 "IFD0:Model" 的带命名空间键值对
            metadata: list[dict[str, Any]] = et.get_metadata(
                str(path), params=["-G1", "-a", "-s"]
            )

        if not metadata:
            logger.warning("未检测到元数据")
            return

        # 打印完整字典（为了美观，使用缩进和排序）
        # 提示：你会在这里看到 ThumbnailImage 字段被标记为类似 "(Binary data ...)" 的字符串
        print(json.dumps(metadata[0], indent=4, ensure_ascii=False))

        # 统计字段数量，让你直观感受 EXIF 的臃肿
        logger.success(f"解析成功！共提取到 {len(metadata[0])} 个元数据字段。")

    except Exception as e:
        logger.exception(f"解析过程中发生错误: {e!s}")


if __name__ == "__main__":
    # 替换为你实际的本地路径
    # TARGET_IMAGE = "/home/hdmin/ShotMemory/backend/uploads/originals/a3c5fd65b2294739a6ca017f41eab534.jpg"
    # print_raw_exif(TARGET_IMAGE)
    raw = {
        "SourceFile": "/home/hdmin/ShotMemory/backend/uploads/originals/a3c5fd65b2294739a6ca017f41eab534.jpg",
        "ExifTool:ExifToolVersion": 12.4,
        "File:FileName": "a3c5fd65b2294739a6ca017f41eab534.jpg",
        "File:Directory": "/home/hdmin/ShotMemory/backend/uploads/originals",
        "File:FileSize": 12485834,
        "File:FileModifyDate": "2026:03:07 20:19:55+08:00",
        "File:FileAccessDate": "2026:03:08 21:00:44+08:00",
        "File:FileInodeChangeDate": "2026:03:07 20:19:55+08:00",
        "File:FilePermissions": 100644,
        "File:FileType": "JPEG",
        "File:FileTypeExtension": "JPG",
        "File:MIMEType": "image/jpeg",
        "File:ExifByteOrder": "MM",
        "File:ImageWidth": 3072,
        "File:ImageHeight": 4096,
        "File:EncodingProcess": 0,
        "File:BitsPerSample": 8,
        "File:ColorComponents": 3,
        "File:YCbCrSubSampling": "2 2",
        "EXIF:ImageWidth": 3072,
        "EXIF:ImageHeight": 4096,
        "EXIF:Make": "realme",
        "EXIF:Model": "realme GT 7 Pro",
        "EXIF:Orientation": 1,
        "EXIF:XResolution": 72,
        "EXIF:YResolution": 72,
        "EXIF:ResolutionUnit": 2,
        "EXIF:ModifyDate": "2026:03:07 20:18:45",
        "EXIF:YCbCrPositioning": 1,
        "EXIF:ExposureTime": 0.008849557522,
        "EXIF:FNumber": 1.8,
        "EXIF:ExposureProgram": 2,
        "EXIF:ISO": 800,
        "EXIF:ExifVersion": "0220",
        "EXIF:DateTimeOriginal": "2026:03:07 20:18:45",
        "EXIF:CreateDate": "2026:03:07 20:18:45",
        "EXIF:OffsetTimeOriginal": "+08:00",
        "EXIF:ComponentsConfiguration": "1 2 3 0",
        "EXIF:ShutterSpeedValue": "0.00882615011382909",
        "EXIF:ApertureValue": 1.79626474576787,
        "EXIF:BrightnessValue": 1.81,
        "EXIF:ExposureCompensation": 0,
        "EXIF:MaxApertureValue": 1.79626474576787,
        "EXIF:MeteringMode": 2,
        "EXIF:LightSource": 21,
        "EXIF:Flash": 16,
        "EXIF:FocalLength": 5.59,
        "EXIF:MakerNoteUnknownText": "(Binary data 319 bytes, use -b option to extract)",
        "EXIF:UserComment": "oplus_10485792",
        "EXIF:SubSecTime": 540,
        "EXIF:SubSecTimeOriginal": 540,
        "EXIF:SubSecTimeDigitized": 540,
        "EXIF:FlashpixVersion": "0100",
        "EXIF:ColorSpace": 1,
        "EXIF:ExifImageWidth": 3072,
        "EXIF:ExifImageHeight": 4096,
        "EXIF:InteropIndex": "R98",
        "EXIF:InteropVersion": "0100",
        "EXIF:SensingMethod": 1,
        "EXIF:SceneType": 1,
        "EXIF:ExposureMode": 0,
        "EXIF:WhiteBalance": 0,
        "EXIF:DigitalZoomRatio": 1.0222,
        "EXIF:FocalLengthIn35mmFormat": 24,
        "EXIF:SceneCaptureType": 0,
        "EXIF:LensModel": "realme GT 7 Pro back camera 23mm f/1.8",
        "EXIF:GPSLatitudeRef": "N",
        "EXIF:GPSLatitude": 21.4463833333333,
        "EXIF:GPSLongitudeRef": "E",
        "EXIF:GPSLongitude": 110.616486111111,
        "EXIF:GPSAltitudeRef": 0,
        "EXIF:GPSAltitude": 0,
        "EXIF:GPSTimeStamp": "12:18:39",
        "EXIF:GPSProcessingMethod": "CELLID",
        "EXIF:GPSDateStamp": "2026:03:07",
        "EXIF:Compression": 6,
        "EXIF:ThumbnailOffset": 1552,
        "EXIF:ThumbnailLength": 16390,
        "EXIF:ThumbnailImage": "(Binary data 16390 bytes, use -b option to extract)",
        "XMP:XMPToolkit": "Adobe XMP Core 5.1.0-jc003",
        "XMP:Version": 1.0,
        "XMP:MotionPhoto": 1,
        "XMP:MotionPhotoVersion": 1,
        "XMP:MotionPhotoPresentationTimestampUs": 1399734,
        "XMP:MotionPhotoPrimaryPresentationTimestampUs": 1399734,
        "XMP:MotionPhotoOwner": "oplus",
        "XMP:OLivePhotoVersion": 2,
        "XMP:VideoLength": 7411590,
        "XMP:DirectoryItemMime": "image/jpeg",
        "XMP:DirectoryItemSemantic": "Primary",
        "XMP:DirectoryItemLength": 0,
        "XMP:DirectoryItemPadding": 0,
        "MPF:MPFVersion": "0100",
        "MPF:NumberOfImages": 2,
        "MPF:MPImageFlags": 0,
        "MPF:MPImageFormat": 0,
        "MPF:MPImageType": 0,
        "MPF:MPImageLength": 495966,
        "MPF:MPImageStart": 3699646,
        "MPF:DependentImage1EntryNumber": 0,
        "MPF:DependentImage2EntryNumber": 0,
        "MPF:MPImage2": "(Binary data 495966 bytes, use -b option to extract)",
        "ICC_Profile:ProfileCMMType": "appl",
        "ICC_Profile:ProfileVersion": 1024,
        "ICC_Profile:ProfileClass": "mntr",
        "ICC_Profile:ColorSpaceData": "RGB ",
        "ICC_Profile:ProfileConnectionSpace": "XYZ ",
        "ICC_Profile:ProfileDateTime": "2018:06:24 13:22:32",
        "ICC_Profile:ProfileFileSignature": "acsp",
        "ICC_Profile:PrimaryPlatform": "APPL",
        "ICC_Profile:CMMFlags": 0,
        "ICC_Profile:DeviceManufacturer": "OPPO",
        "ICC_Profile:DeviceModel": "",
        "ICC_Profile:DeviceAttributes": "0 0",
        "ICC_Profile:RenderingIntent": 0,
        "ICC_Profile:ConnectionSpaceIlluminant": "0.9642 1 0.82491",
        "ICC_Profile:ProfileCreator": "appl",
        "ICC_Profile:ProfileID": "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
        "ICC_Profile:ProfileDescription": "Display P3",
        "ICC_Profile:ProfileCopyright": "Copyright Apple Inc., 2017",
        "ICC_Profile:MediaWhitePoint": "0.95045 1 1.08905",
        "ICC_Profile:RedMatrixColumn": "0.51512 0.2412 -0.00105",
        "ICC_Profile:GreenMatrixColumn": "0.29198 0.69225 0.04189",
        "ICC_Profile:BlueMatrixColumn": "0.1571 0.06657 0.78407",
        "ICC_Profile:RedTRC": "(Binary data 32 bytes, use -b option to extract)",
        "ICC_Profile:ChromaticAdaptation": "1.04788 0.02292 -0.0502 0.02959 0.99048 -0.01706 -0.00923 0.01508 0.75168",
        "ICC_Profile:BlueTRC": "(Binary data 32 bytes, use -b option to extract)",
        "ICC_Profile:GreenTRC": "(Binary data 32 bytes, use -b option to extract)",
        "Composite:Aperture": 1.8,
        "Composite:ImageSize": "3072 4096",
        "Composite:Megapixels": 12.582912,
        "Composite:ScaleFactor35efl": 4.29338103756708,
        "Composite:ShutterSpeed": 0.008849557522,
        "Composite:SubSecCreateDate": "2026:03:07 20:18:45.540",
        "Composite:SubSecDateTimeOriginal": "2026:03:07 20:18:45.540+08:00",
        "Composite:SubSecModifyDate": "2026:03:07 20:18:45.540",
        "Composite:GPSAltitude": 0,
        "Composite:GPSDateTime": "2026:03:07 12:18:39Z",
        "Composite:GPSLatitude": 21.4463833333333,
        "Composite:GPSLongitude": 110.616486111111,
        "Composite:CircleOfConfusion": "0.00699827487147351",
        "Composite:FOV": 73.7398575770812,
        "Composite:FocalLength35efl": 24,
        "Composite:GPSPosition": "21.4463833333333 110.616486111111",
        "Composite:HyperfocalDistance": 2.48061927751922,
        "Composite:LightValue": 5.51617277554529,
        "Composite:LensID": "realme GT 7 Pro back camera 23mm f/1.8",
    }
    
    pprint.pprint(_flatten_by_priority(raw))
"""
{
    "SourceFile": "/home/hdmin/ShotMemory/backend/uploads/originals/a3c5fd65b2294739a6ca017f41eab534.jpg",
    "ExifTool:ExifToolVersion": 12.4,
    "File:FileName": "a3c5fd65b2294739a6ca017f41eab534.jpg",
    "File:Directory": "/home/hdmin/ShotMemory/backend/uploads/originals",
    "File:FileSize": 12485834,
    "File:FileModifyDate": "2026:03:07 20:19:55+08:00",
    "File:FileAccessDate": "2026:03:08 21:00:44+08:00",
    "File:FileInodeChangeDate": "2026:03:07 20:19:55+08:00",
    "File:FilePermissions": 100644,
    "File:FileType": "JPEG",
    "File:FileTypeExtension": "JPG",
    "File:MIMEType": "image/jpeg",
    "File:ExifByteOrder": "MM",
    "File:ImageWidth": 3072,
    "File:ImageHeight": 4096,
    "File:EncodingProcess": 0,
    "File:BitsPerSample": 8,
    "File:ColorComponents": 3,
    "File:YCbCrSubSampling": "2 2",
    "EXIF:ImageWidth": 3072,
    "EXIF:ImageHeight": 4096,
    "EXIF:Make": "realme",
    "EXIF:Model": "realme GT 7 Pro",
    "EXIF:Orientation": 1,
    "EXIF:XResolution": 72,
    "EXIF:YResolution": 72,
    "EXIF:ResolutionUnit": 2,
    "EXIF:ModifyDate": "2026:03:07 20:18:45",
    "EXIF:YCbCrPositioning": 1,
    "EXIF:ExposureTime": 0.008849557522,
    "EXIF:FNumber": 1.8,
    "EXIF:ExposureProgram": 2,
    "EXIF:ISO": 800,
    "EXIF:ExifVersion": "0220",
    "EXIF:DateTimeOriginal": "2026:03:07 20:18:45",
    "EXIF:CreateDate": "2026:03:07 20:18:45",
    "EXIF:OffsetTimeOriginal": "+08:00",
    "EXIF:ComponentsConfiguration": "1 2 3 0",
    "EXIF:ShutterSpeedValue": "0.00882615011382909",
    "EXIF:ApertureValue": 1.79626474576787,
    "EXIF:BrightnessValue": 1.81,
    "EXIF:ExposureCompensation": 0,
    "EXIF:MaxApertureValue": 1.79626474576787,
    "EXIF:MeteringMode": 2,
    "EXIF:LightSource": 21,
    "EXIF:Flash": 16,
    "EXIF:FocalLength": 5.59,
    "EXIF:MakerNoteUnknownText": "(Binary data 319 bytes, use -b option to extract)",
    "EXIF:UserComment": "oplus_10485792",
    "EXIF:SubSecTime": 540,
    "EXIF:SubSecTimeOriginal": 540,
    "EXIF:SubSecTimeDigitized": 540,
    "EXIF:FlashpixVersion": "0100",
    "EXIF:ColorSpace": 1,
    "EXIF:ExifImageWidth": 3072,
    "EXIF:ExifImageHeight": 4096,
    "EXIF:InteropIndex": "R98",
    "EXIF:InteropVersion": "0100",
    "EXIF:SensingMethod": 1,
    "EXIF:SceneType": 1,
    "EXIF:ExposureMode": 0,
    "EXIF:WhiteBalance": 0,
    "EXIF:DigitalZoomRatio": 1.0222,
    "EXIF:FocalLengthIn35mmFormat": 24,
    "EXIF:SceneCaptureType": 0,
    "EXIF:LensModel": "realme GT 7 Pro back camera 23mm f/1.8",
    "EXIF:GPSLatitudeRef": "N",
    "EXIF:GPSLatitude": 21.4463833333333,
    "EXIF:GPSLongitudeRef": "E",
    "EXIF:GPSLongitude": 110.616486111111,
    "EXIF:GPSAltitudeRef": 0,
    "EXIF:GPSAltitude": 0,
    "EXIF:GPSTimeStamp": "12:18:39",
    "EXIF:GPSProcessingMethod": "CELLID",
    "EXIF:GPSDateStamp": "2026:03:07",
    "EXIF:Compression": 6,
    "EXIF:ThumbnailOffset": 1552,
    "EXIF:ThumbnailLength": 16390,
    "EXIF:ThumbnailImage": "(Binary data 16390 bytes, use -b option to extract)",
    "XMP:XMPToolkit": "Adobe XMP Core 5.1.0-jc003",
    "XMP:Version": 1.0,
    "XMP:MotionPhoto": 1,
    "XMP:MotionPhotoVersion": 1,
    "XMP:MotionPhotoPresentationTimestampUs": 1399734,
    "XMP:MotionPhotoPrimaryPresentationTimestampUs": 1399734,
    "XMP:MotionPhotoOwner": "oplus",
    "XMP:OLivePhotoVersion": 2,
    "XMP:VideoLength": 7411590,
    "XMP:DirectoryItemMime": "image/jpeg",
    "XMP:DirectoryItemSemantic": "Primary",
    "XMP:DirectoryItemLength": 0,
    "XMP:DirectoryItemPadding": 0,
    "MPF:MPFVersion": "0100",
    "MPF:NumberOfImages": 2,
    "MPF:MPImageFlags": 0,
    "MPF:MPImageFormat": 0,
    "MPF:MPImageType": 0,
    "MPF:MPImageLength": 495966,
    "MPF:MPImageStart": 3699646,
    "MPF:DependentImage1EntryNumber": 0,
    "MPF:DependentImage2EntryNumber": 0,
    "MPF:MPImage2": "(Binary data 495966 bytes, use -b option to extract)",
    "ICC_Profile:ProfileCMMType": "appl",
    "ICC_Profile:ProfileVersion": 1024,
    "ICC_Profile:ProfileClass": "mntr",
    "ICC_Profile:ColorSpaceData": "RGB ",
    "ICC_Profile:ProfileConnectionSpace": "XYZ ",
    "ICC_Profile:ProfileDateTime": "2018:06:24 13:22:32",
    "ICC_Profile:ProfileFileSignature": "acsp",
    "ICC_Profile:PrimaryPlatform": "APPL",
    "ICC_Profile:CMMFlags": 0,
    "ICC_Profile:DeviceManufacturer": "OPPO",
    "ICC_Profile:DeviceModel": "",
    "ICC_Profile:DeviceAttributes": "0 0",
    "ICC_Profile:RenderingIntent": 0,
    "ICC_Profile:ConnectionSpaceIlluminant": "0.9642 1 0.82491",
    "ICC_Profile:ProfileCreator": "appl",
    "ICC_Profile:ProfileID": "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
    "ICC_Profile:ProfileDescription": "Display P3",
    "ICC_Profile:ProfileCopyright": "Copyright Apple Inc., 2017",
    "ICC_Profile:MediaWhitePoint": "0.95045 1 1.08905",
    "ICC_Profile:RedMatrixColumn": "0.51512 0.2412 -0.00105",
    "ICC_Profile:GreenMatrixColumn": "0.29198 0.69225 0.04189",
    "ICC_Profile:BlueMatrixColumn": "0.1571 0.06657 0.78407",
    "ICC_Profile:RedTRC": "(Binary data 32 bytes, use -b option to extract)",
    "ICC_Profile:ChromaticAdaptation": "1.04788 0.02292 -0.0502 0.02959 0.99048 -0.01706 -0.00923 0.01508 0.75168",
    "ICC_Profile:BlueTRC": "(Binary data 32 bytes, use -b option to extract)",
    "ICC_Profile:GreenTRC": "(Binary data 32 bytes, use -b option to extract)",
    "Composite:Aperture": 1.8,
    "Composite:ImageSize": "3072 4096",
    "Composite:Megapixels": 12.582912,
    "Composite:ScaleFactor35efl": 4.29338103756708,
    "Composite:ShutterSpeed": 0.008849557522,
    "Composite:SubSecCreateDate": "2026:03:07 20:18:45.540",
    "Composite:SubSecDateTimeOriginal": "2026:03:07 20:18:45.540+08:00",
    "Composite:SubSecModifyDate": "2026:03:07 20:18:45.540",
    "Composite:GPSAltitude": 0,
    "Composite:GPSDateTime": "2026:03:07 12:18:39Z",
    "Composite:GPSLatitude": 21.4463833333333,
    "Composite:GPSLongitude": 110.616486111111,
    "Composite:CircleOfConfusion": "0.00699827487147351",
    "Composite:FOV": 73.7398575770812,
    "Composite:FocalLength35efl": 24,
    "Composite:GPSPosition": "21.4463833333333 110.616486111111",
    "Composite:HyperfocalDistance": 2.48061927751922,
    "Composite:LightValue": 5.51617277554529,
    "Composite:LensID": "realme GT 7 Pro back camera 23mm f/1.8"
}
2026-03-08 22:00:34.195 | SUCCESS  | __main__:print_raw_exif:42 - 解析成功！共提取到 147 个元数据字段。
"""
