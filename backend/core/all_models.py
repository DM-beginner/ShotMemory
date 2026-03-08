# backend/core/models.py
"""
统一的模型注册中心 (Model Registry Aggregator)

此文件的唯一目的：在系统（主服务、Worker、Alembic 迁移脚本）启动时，
通过引入此文件，强制 SQLAlchemy 加载并注册分散在各个业务域（Domain）的所有表结构，
从而完美解决字符串外键 (ForeignKey) 找不到目标表的 RuntimeError。
"""

# 严格按模块导入所有领域模型，即使IDE提示 "unused import" 也绝不能删！
from services.auth.models.refresh_token_model import RefreshToken
from services.auth.models.user_model import User
from services.photo_story.models.photo_model import Photo
from services.photo_story.models.story_model import Story
from services.photo_story.models.story_photo_m2m import PhotoStoryM2M

# 未来如果增加了新的服务模块，比如评论系统，也要加在这里
# from services.comments.models.comment import Comment

__all__ = ["Photo", "PhotoStoryM2M", "RefreshToken", "Story", "User"]
