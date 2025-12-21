# routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from .. import schemas, database
from ..services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])

def get_service():
    return NotificationService()

@router.get("", response_model=List[schemas.NotificationResponse])
def get_notifications(
    db=Depends(database.get_db),
    service=Depends(get_service)
):
    return service.get_notifications(db)

@router.get("/{id}", response_model=schemas.NotificationResponse)
def get_notification(
    id: int,
    db=Depends(database.get_db),
    service=Depends(get_service)
):
    notification = service.get_notification(db, id)
    if not notification:
        raise HTTPException(404, "Powiadomienie nie znalezione")
    return notification

@router.post("", response_model=schemas.NotificationResponse)
def create_notification(
    notification: schemas.NotificationCreate,
    db=Depends(database.get_db),
    service=Depends(get_service)
):
    try:
        created = service.create_notification(db, notification)
        return created
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

@router.post("/{id}/force-send")
def force_send_notification(
    id: int,
    db=Depends(database.get_db),
    service=Depends(get_service)
):
    notif = service.force_send_now(db, id)
    if not notif:
        raise HTTPException(404, "Powiadomienie nie znalezione lub nie można go wysłać")
    
    return {"message": "Powiadomienie zaplanowane do natychmiastowej wysyłki"}

@router.post("/{id}/cancel")
def cancel_notification(
    id: int,
    db=Depends(database.get_db),
    service=Depends(get_service)
):
    success = service.cancel_notification(db, id)
    if not success:
        raise HTTPException(404, "Powiadomienie nie znalezione lub nie można go anulować")
    return {"message": "Powiadomienie anulowane"}

@router.put("/{id}/reschedule")
def reschedule_notification(
    id: int,
    # new_time: datetime = Query(...),
    new_time: datetime,
    db=Depends(database.get_db),
    service=Depends(get_service)
):
    notif = service.reschedule_notification(db, id, new_time)
    if not notif:
        raise HTTPException(404, "Powiadomienie nie znalezione")
    
    # Anuluj poprzednią planowaną wysyłkę i zaplanuj nową
    return notif
