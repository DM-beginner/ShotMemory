from uuid import UUID

from fastapi import APIRouter

from core.base_schema import BaseResponse
from core.database import SessionDep
from core.exceptions import APIStatus, BaseError
from core.unify_response import UnifyResponse
from services.auth.routers.user_deps import CurrentUser
from services.photo_story.models.story_model import Story
from services.photo_story.models.story_photo_m2m import PhotoStoryM2M
from services.photo_story.repos.story_repo import StoryRepo
from services.photo_story.schemas.story_schema import (
    StoryCreateRequest,
    StoryDetailResponse,
    StoryListResponse,
    StoryResponse,
    StoryUpdateRequest,
)

router = APIRouter(tags=["story"], prefix="/story")


@router.post("", response_model=BaseResponse[StoryResponse])
async def create_story(
    request: StoryCreateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    创建故事

    - 需要登录认证
    - 可同时关联照片列表（最多 9 张）
    - 若 photo_ids 非空但未指定 cover_photo_id，自动设为 photo_ids[0]
    """
    # 批量验证照片归属
    valid_ids: set[UUID] = set()
    if request.photo_ids:
        valid_ids = await StoryRepo.batch_validate_photo_ownership(
            db, request.photo_ids, current_user.id
        )
        # 过滤出有效的 photo_ids（保持原始顺序）
        filtered_ids = [pid for pid in request.photo_ids if pid in valid_ids]

        if not filtered_ids and request.photo_ids:
            raise BaseError(
                code=APIStatus.BAD_REQUEST.code,
                message="提供的照片均不属于当前用户",
                status_code=400,
            )
    else:
        filtered_ids = []

    # 自动设置封面
    cover_photo_id = request.cover_photo_id
    if cover_photo_id and cover_photo_id not in valid_ids:
        cover_photo_id = None
    if not cover_photo_id and filtered_ids:
        cover_photo_id = filtered_ids[0]

    # 创建故事记录
    story = Story(
        user_id=current_user.id,
        title=request.title,
        content=request.content,
        cover_photo_id=cover_photo_id,
    )
    story = await StoryRepo.create(db, story)

    # 批量插入 M2M 关系（含 sort_order）
    if filtered_ids:
        await db.execute(
            PhotoStoryM2M.__table__.insert(),
            [
                {"story_id": story.id, "photo_id": pid, "sort_order": idx}
                for idx, pid in enumerate(filtered_ids)
            ],
        )
        await db.commit()

    await db.refresh(story, attribute_names=["cover_photo"])

    return UnifyResponse.success(
        data=StoryResponse.model_validate(story).model_dump(mode="json"),
        message="故事创建成功",
    )


@router.get("/{story_id}", response_model=BaseResponse[StoryDetailResponse])
async def get_story(
    story_id: UUID,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    获取故事详情

    - 需要登录认证
    - 只能查看自己的故事
    - 返回包含关联照片列表（按 sort_order 排序）
    """
    story = await StoryRepo.get_by_id(db, story_id, with_photos=True)

    if not story:
        raise BaseError(
            code=APIStatus.NOT_FOUND.code,
            message="故事不存在",
            status_code=404,
        )

    if story.user_id != current_user.id:
        raise BaseError(
            code=APIStatus.FORBIDDEN.code,
            message="无权访问此故事",
            status_code=403,
        )

    return UnifyResponse.success(
        data=StoryDetailResponse.model_validate(story).model_dump(mode="json"),
    )


@router.get("", response_model=BaseResponse[StoryListResponse])
async def get_my_stories(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = 20,
    offset: int = 0,
):
    """
    获取当前用户的故事列表

    - 需要登录认证
    - 支持分页
    - 按创建时间倒序排列
    - 包含封面缩略图推导
    """
    stories, total = await StoryRepo.get_list_with_cover(
        db, current_user.id, limit, offset
    )

    items = [StoryResponse.model_validate(story) for story in stories]

    return UnifyResponse.success(
        data=StoryListResponse(
            total=total,
            items=items,
        ).model_dump(mode="json"),
    )


@router.patch("/{story_id}", response_model=BaseResponse[StoryResponse])
async def update_story(
    story_id: UUID,
    request: StoryUpdateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    更新故事信息

    - 需要登录认证
    - 只能更新自己的故事
    - 支持更新标题、内容、封面照片、关联照片
    """
    story = await StoryRepo.get_by_id(db, story_id)

    if not story:
        raise BaseError(
            code=APIStatus.NOT_FOUND.code,
            message="故事不存在",
            status_code=404,
        )

    if story.user_id != current_user.id:
        raise BaseError(
            code=APIStatus.FORBIDDEN.code,
            message="无权修改此故事",
            status_code=403,
        )

    # 更新基本字段
    if request.title is not None:
        story.title = request.title
    if request.content is not None:
        story.content = request.content
    if request.cover_photo_id is not None:
        story.cover_photo_id = request.cover_photo_id

    # 更新关联照片
    if request.photo_ids is not None:
        if request.photo_ids:
            valid_ids = await StoryRepo.batch_validate_photo_ownership(
                db, request.photo_ids, current_user.id
            )
            filtered_ids = [pid for pid in request.photo_ids if pid in valid_ids]
        else:
            filtered_ids = []
        await StoryRepo.replace_photos(db, story_id, filtered_ids)

    story = await StoryRepo.update(db, story)

    return UnifyResponse.success(
        data=StoryResponse.model_validate(story).model_dump(mode="json"),
        message="故事更新成功",
    )


@router.delete("/{story_id}", response_model=BaseResponse[dict])
async def delete_story(
    story_id: UUID,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    删除故事

    - 需要登录认证
    - 只能删除自己的故事
    - 会级联删除 M2M 关系，但不会删除照片本身
    """
    story = await StoryRepo.get_by_id(db, story_id)

    if not story:
        raise BaseError(
            code=APIStatus.NOT_FOUND.code,
            message="故事不存在",
            status_code=404,
        )

    if story.user_id != current_user.id:
        raise BaseError(
            code=APIStatus.FORBIDDEN.code,
            message="无权删除此故事",
            status_code=403,
        )

    success = await StoryRepo.delete(db, story_id)

    if not success:
        raise BaseError(
            code=APIStatus.SYSTEM_ERROR.code,
            message="删除故事失败",
            status_code=500,
        )

    return UnifyResponse.success(
        data={"deleted": True},
        message="故事删除成功",
    )
