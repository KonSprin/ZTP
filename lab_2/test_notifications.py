# test_notifications.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from main import app

client = TestClient(app)

def test_create_notification():
    """Test tworzenia powiadomienia"""
    payload = {
        "recipient": "user@example.com",
        "channel": "email",
        "content": "Test message",
        "scheduled_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "priority": "high"
    }
    
    response = client.post("/notifications", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

def test_invalid_channel():
    """Test walidacji kanału"""
    payload = {
        "recipient": "user@example.com",
        "channel": "invalid",
        "content": "Test",
        "scheduled_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }
    
    response = client.post("/notifications", json=payload)
    assert response.status_code == 422

def test_past_scheduled_time():
    """Test walidacji czasu zaplanowania"""
    payload = {
        "recipient": "user@example.com",
        "channel": "email",
        "content": "Test",
        "scheduled_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    }
    
    response = client.post("/notifications", json=payload)
    assert response.status_code == 422

def test_cancel_notification(notification_id=1):
    """Test anulowania powiadomienia"""
    response = client.post(f"/notifications/{notification_id}/cancel")
    assert response.status_code == 200

def test_force_send_notification(notification_id=1):
    """Test natychmiastowej wysyłki"""
    response = client.post(f"/notifications/{notification_id}/force-send")
    assert response.status_code == 200
