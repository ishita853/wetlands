from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/climate", tags=["climate"])

_NOT_IMPLEMENTED = "This climate indicator endpoint is not implemented yet."


@router.get("/drought")
def get_drought() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)


@router.get("/precipitation")
def get_precipitation() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)


@router.get("/heat-waves")
def get_heat_waves() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)


@router.get("/cold-waves")
def get_cold_waves() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)
