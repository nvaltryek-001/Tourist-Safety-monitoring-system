"""Legacy POST /tourists/{code}/sos contract."""


def test_sos_records_alert_without_claiming_delivery(client, tourist_headers, db_session):
    from app.models.models import SOSAlert, Tourist

    response = client.post("/tourists/T-TEST-01/sos", headers=tourist_headers, json={"message": "Automated test only"})
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "SOS alert recorded"
    assert body["tourist_code"] == "T-TEST-01"
    assert all(r["status"] != "DELIVERED" for r in body["notification_results"])

    alert = db_session.query(SOSAlert).filter_by(tourist_code="T-TEST-01").first()
    tourist = db_session.query(Tourist).filter_by(tourist_code="T-TEST-01").first()
    assert alert.message == "Automated test only"
    assert tourist.safety_status == "SOS"


def test_sos_unknown_tourist_returns_404(client, admin_headers):
    response = client.post("/tourists/DOES-NOT-EXIST/sos", headers=admin_headers, json={"message": "x"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Tourist not found"
