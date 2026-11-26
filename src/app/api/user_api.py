from fastapi import APIRouter, Query, Depends, UploadFile, File, Form, Request, Response, HTTPException
from app.service.user_service import get_user_service, UserService
from app.service.s3_service import get_s3_service, S3Service
from app.enum.user_enum import UserProvider
from app.enum.s3_enum import S3Folder
from app.schema.user_schema import UserCreateDTO, UserClaimDTO, UserUpdateDTO, UserResponseDTO
from app.service.auth_service import AuthService, get_auth_service
from app.schema.common_schema import ApiResponseDTO
from app.schema.s3_schema import ImageUploadResponseDTO
from app.dependency.auth_dependency import get_current_user


router = APIRouter()


@router.get("/me", response_model=ApiResponseDTO[UserResponseDTO])
async def get_me(
    request: Request,
    response: Response,
    claims: UserClaimDTO = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    # ID를 프론트에서 받지 않고 검증한 access_token의 ID로만 조회합니다.
    if await auth_service.is_blacklisted_token(request.cookies.get("access_token")):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    try:
        user = await user_service.get_user_by_id(claims.id)
    except HTTPException as error:
        if error.status_code == 404:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.") from error
        raise
    if not user.user_status:
        raise HTTPException(status_code=403, detail="이용할 수 없는 회원입니다.")
    response.headers["Cache-Control"] = "no-store"
    return ApiResponseDTO(success=True, message="내 정보 조회 성공", data=user)

@router.post(
    "/check-user", 
    response_model=ApiResponseDTO
)
async def check_user(
    user_email: str, 
    user_provider: str, 
    user_service = Depends(get_user_service)
):
    await user_service.check_duplicate_user(user_email, user_provider)
    return ApiResponseDTO(
        success=True,
        message="중복되지 않은 사용자",
    )

