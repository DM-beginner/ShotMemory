from fastapi import UploadFile

from core.storage.interface import StorageStrategy, UploadResult


class AliyunOSSStrategy(StorageStrategy):
    """
    阿里云 OSS 存储策略（生产环境使用）

    TODO: 实现步骤
    1. 安装依赖: uv add oss2
    2. 实现 upload_file: 使用 oss2.Bucket.put_object() 上传文件
    3. 实现 delete_file: 使用 oss2.Bucket.delete_object() 删除文件
    4. 返回 CDN 域名拼接的 URL
    """

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        bucket_name: str,
        endpoint: str,
        cdn_domain: str,
    ) -> None:
        """
        Args:
            access_key_id: 阿里云 AccessKey ID
            access_key_secret: 阿里云 AccessKey Secret
            bucket_name: OSS Bucket 名称
            endpoint: OSS 节点地址（如 "https://oss-cn-hangzhou.aliyuncs.com"）
            cdn_domain: CDN 加速域名（如 "https://cdn.example.com"）
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.bucket_name = bucket_name
        self.endpoint = endpoint
        self.cdn_domain = cdn_domain.rstrip("/")

        # TODO: 初始化 oss2 客户端
        # import oss2
        # auth = oss2.Auth(access_key_id, access_key_secret)
        # self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

    async def upload_file(self, file: UploadFile) -> UploadResult:
        """
        上传文件到阿里云 OSS

        TODO: 实现逻辑
        1. 生成唯一的 object key（如 photos/uuid.jpg）
        2. 读取文件内容: content = await file.read()
        3. 上传到 OSS: self.bucket.put_object(object_key, content)
        4. 返回 UploadResult(url=f"{self.cdn_domain}/{object_key}", object_key=object_key)
        """
        raise NotImplementedError(
            "阿里云 OSS 存储尚未实现，请先安装 oss2 (uv add oss2) 并补充实现代码"
        )

    async def upload_bytes(
        self,
        data: bytes,
        suffix: str,
        subdir: str = "thumbnails",
        stem: str | None = None,
    ) -> UploadResult:
        """
        上传字节流到阿里云 OSS（用于程序生成的文件，如 WebP 缩略图、视频）

        TODO: 实现逻辑
        1. 生成唯一的 object key（如 thumbnails/uuid.webp 或 videos/uuid.mp4）
        2. 上传到 OSS: self.bucket.put_object(object_key, data)
        3. 返回 UploadResult(url=f"{self.cdn_domain}/{object_key}", object_key=object_key)
        """
        raise NotImplementedError(
            "阿里云 OSS 字节流上传尚未实现，请先安装 oss2 (uv add oss2) 并补充实现代码"
        )

    async def delete_file(self, object_key: str) -> bool:
        """
        从阿里云 OSS 删除文件

        TODO: 实现逻辑
        1. 删除对象: self.bucket.delete_object(object_key)
        2. 返回删除结果
        """
        raise NotImplementedError(
            "阿里云 OSS 删除尚未实现，请先安装 oss2 (uv add oss2) 并补充实现代码"
        )
