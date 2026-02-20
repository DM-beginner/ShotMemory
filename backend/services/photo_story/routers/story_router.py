from uuid import UUID

from fastapi import APIRouter

from core.base_code import APIStatus
from core.base_schema import BaseResponse
from core.custom_exception import BusinessError
from core.database import SessionDep
from core.unify_response import UnifyResponse
from services.auth.routers.user_deps import CurrentUser
from services.photo_story.models.photo_story_m2m import StoryPhotoM2M
from services.photo_story.models.story_model import Story
from services.photo_story.repos.photo_repo import PhotoRepo
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
    - 可同时关联照片列表
    - 封面照片必须在关联照片列表中
    """
    # 创建故事记录
    story = Story(
        user_id=current_user.id,
        title=request.title,
        content=request.content,
        cover_photo_id=request.cover_photo_id,
    )

    story = await StoryRepo.create(db, story)

    # 关联照片（如果提供了 photo_ids）
    if request.photo_ids:
        # 批量插入 M2M 关系
        for photo_id in request.photo_ids:
            # 验证照片是否属于当前用户
            photo = await PhotoRepo.get_by_id(db, photo_id)
            if not photo or photo.user_id != current_user.id:
                continue  # 跳过不存在或不属于自己的照片

            # 插入 M2M 关系
            await db.execute(
                StoryPhotoM2M.__table__.insert().values(
                    story_id=story.id, photo_id=photo_id
                )
            )

        await db.commit()

    return UnifyResponse.success(
        data=StoryResponse.model_validate(story).model_dump(),
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
    - 返回包含关联照片列表
    """
    story = await StoryRepo.get_by_id(db, story_id, with_photos=True)

    if not story:
        raise BusinessError(
            code=APIStatus.NOT_FOUND.code,
            message="故事不存在",
            status_code=404,
        )

    # 权限校验
    if story.user_id != current_user.id:
        raise BusinessError(
            code=APIStatus.FORBIDDEN.code,
            message="无权访问此故事",
            status_code=403,
        )

    return UnifyResponse.success(
        data=StoryDetailResponse.model_validate(story).model_dump(),
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
    """
    stories = await StoryRepo.get_by_user_id(
        db, current_user.id, limit, offset, with_photos=False
    )

    # 统计总数
    total = await StoryRepo.count_by_user_id(db, current_user.id)

    # 转换为响应格式
    items = [StoryResponse.model_validate(story) for story in stories]

    return UnifyResponse.success(
        data=StoryListResponse(
            total=total,
            items=[item.model_dump() for item in items],
        ).model_dump(),
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
    - 支持更新标题、内容、封面照片
    """
    story = await StoryRepo.get_by_id(db, story_id)

    if not story:
        raise BusinessError(
            code=APIStatus.NOT_FOUND.code,
            message="故事不存在",
            status_code=404,
        )

    # 权限校验
    if story.user_id != current_user.id:
        raise BusinessError(
            code=APIStatus.FORBIDDEN.code,
            message="无权修改此故事",
            status_code=403,
        )

    # 更新字段
    if request.title is not None:
        story.title = request.title
    if request.content is not None:
        story.content = request.content
    if request.cover_photo_id is not None:
        story.cover_photo_id = request.cover_photo_id

    story = await StoryRepo.update(db, story)

    return UnifyResponse.success(
        data=StoryResponse.model_validate(story).model_dump(),
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
        raise BusinessError(
            code=APIStatus.NOT_FOUND.code,
            message="故事不存在",
            status_code=404,
        )

    # 权限校验
    if story.user_id != current_user.id:
        raise BusinessError(
            code=APIStatus.FORBIDDEN.code,
            message="无权删除此故事",
            status_code=403,
        )

    # 删除故事（M2M 关系会自动级联删除）
    success = await StoryRepo.delete(db, story_id)

    if not success:
        raise BusinessError(
            code=APIStatus.SYSTEM_ERROR.code,
            message="删除故事失败",
            status_code=500,
        )

    return UnifyResponse.success(
        data={"deleted": True},
        message="故事删除成功",
    )
