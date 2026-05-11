# 故事模块

## 1. 概述

故事 = 用户创建的图文笔记，关联最多 9 张自己的照片，含一张封面。`backend/services/photo_story/routers/story_router.py` 负责故事 CRUD；与照片共用同一 schema (`photo_story`)。

---

## 2. 数据模型

字段定义以 `services/photo_story/models/{story_model,story_photo_m2m}.py` 为准。下表只列**非显然**字段：

### 2.1 `photo_story.story`

| 字段 | 类型 | 说明 |
|------|------|------|
| content | TEXT NULL | 正文（Markdown / 富文本） |
| cover_photo_id | UUID FK → photo.id (ondelete=SET NULL) NULL | 封面照片；删除照片时 SET NULL 而非 CASCADE，故事保留 |

索引：`(user_id)`、`(created_at)`、`(title)`。

### 2.2 `photo_story.photo_story_m2m`

复合主键 `(story_id, photo_id)`。`sort_order INT DEFAULT 0` 由后端按数组下标写入，提供故事内照片稳定顺序。

### 2.3 关系定义

```
Story.cover_photo : Photo | None       (selectinload, post_update=True 解决循环外键)
Story.photos      : list[Photo]        (M2M, order_by=PhotoStoryM2M.sort_order, lazy="select")
Photo.stories     : list[Story]        (M2M 反向, lazy="selectin")
```

`cover_photo_id` 是单独的外键关系（非 M2M）；删除照片时 `ondelete=SET NULL` 清空指向但保留故事。`post_update=True` 是为了解决 `story.cover_photo_id` 与 `photo` 之间的循环依赖。

---

## 3. API 接口

所有接口前缀 `/v1/story`，需 `CurrentUser`。完整请求/响应字段见 `/v1/docs`，以下只列**非显然**语义。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/story` | POST | 创建。请求体 `photo_ids[]` ≤ 9（Pydantic `max_length=9`）；`cover_photo_id` 可选；`StoryRepo.batch_validate_photo_ownership` 会过滤出归属当前用户的子集，全不归属时返回 `40000` |
| `/story` | GET | 列表，`?limit=&offset=`，按 `created_at DESC`；预加载 `cover_photo` 推导 `cover_thumbnail_key`；`total` 是真正的全表 count（故事条数小，COUNT 不痛） |
| `/story/{id}` | GET | 详情，归属当前用户；返回 `photos[]` 按 `sort_order` 排序 |
| `/story/{id}` | PATCH | 所有字段可选；`photo_ids` 传 `null` = **不更新关联**，传 `[]` = **清空所有关联**，传 `[...]` = replace（DELETE 旧 → batch INSERT 新含新 sort_order） |
| `/story/{id}` | DELETE | 故事记录物理删除；M2M 通过外键 `ondelete=CASCADE` 自动清理；**不删除照片本身** |

错误码段位见 `docs/architecture.md` § 11。常用：`40000 BAD_REQUEST`、`40004 STORY_NOT_FOUND`、`40003` 越权。

---

## 4. 业务规则

1. **最多 9 张照片**：`StoryCreateRequest.photo_ids` / `StoryUpdateRequest.photo_ids` 都加了 `max_length=9` Pydantic 校验。
2. **批量归属校验**：`StoryRepo.batch_validate_photo_ownership` 一条 `WHERE id IN (...) AND user_id = ?` 取交集，过滤出当前用户的照片。
3. **封面自动选择**：未指定 `cover_photo_id` 但 `photo_ids` 非空 → 取过滤后的第一张作封面；指定的封面若不在归属集合 → 置空。
4. **`cover_thumbnail_key` 仅在缩略图就绪时返回**（`StoryResponse.derive_cover_thumbnail`）：要求 `cover_photo.exif_data is not None`，避免链接到一个未生成的缩略图。
5. **更新照片走 replace 而非 diff**：实现简单且 `sort_order` 完全可控；适合 9 张以内的小集合，不会有性能问题。
6. **PATCH 字段语义统一**：`null` = 不动，`[]` = 清空（仅 `photo_ids`）。其他字段为 `null` 也表示不动。
7. **删除故事不级联删照片**：通过 `Story.id` 路径上的 ON DELETE CASCADE 只清掉 M2M 行，照片表保持不变。

---

## 5. 依赖关系

| 依赖于 | 用途 |
|--------|------|
| `services.auth` | `CurrentUser` 注入 |
| `services.photo_story.models.photo` | `cover_photo` 关系 + 归属校验 |
| `services.photo_story.schemas.photo_schema` | `PhotoResponse` 嵌入故事详情、`derive_thumbnail_key` 推导封面 |

| 被依赖 | 用途 |
|--------|------|
| 前端 `StoryList` / `StoryDetail` / `StoryEditor` | CRUD |

---

## 6. 关键源码索引

代码位置：`backend/services/photo_story/`。子目录 `routers/story_router`、`models/{story_model,story_photo_m2m}`、`schemas/story_schema`、`repos/story_repo`。`sort_order` 字段由迁移 `2026_03_17_0100_add_sort_order_to_m2m` 引入。
