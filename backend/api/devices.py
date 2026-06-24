"""CRUD e listagem de dispositivos do inventario."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.auth import CurrentUser
from ..core.database import get_db
from ..core.models import Device
from ..core.schemas import DeviceListOut, DeviceOut

router = APIRouter()


@router.get("", response_model=DeviceListOut)
def listar(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    busca: str | None = Query(None, description="Busca em hostname, IP, MAC ou fabricante"),
    online: bool | None = Query(None, description="Filtra por online (true/false)"),
    so: str | None = Query(None, description="Filtra por sistema operacional"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    q = db.query(Device).filter(Device.tenant_id == user.tenant_id)
    if busca:
        like = f"%{busca}%"
        q = q.filter(or_(
            Device.hostname.like(like),
            Device.ip.like(like),
            Device.mac.like(like),
            Device.fabricante.like(like),
        ))
    if online is not None:
        q = q.filter(Device.online == online)
    if so:
        q = q.filter(Device.so == so)

    total = q.count()
    online_count = q.filter(Device.online.is_(True)).count()
    devices = q.order_by(Device.ultima_visao.desc()).offset(offset).limit(limit).all()

    return DeviceListOut(
        total=total,
        online=online_count,
        offline=total - online_count,
        devices=[DeviceOut.model_validate(d) for d in devices],
    )


@router.get("/{device_id}", response_model=DeviceOut)
def detalhe(device_id: int, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    d = db.query(Device).filter(Device.id == device_id, Device.tenant_id == user.tenant_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="device nao encontrado")
    return DeviceOut.model_validate(d)
