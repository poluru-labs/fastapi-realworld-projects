from fastapi.testclient import TestClient


def _auth_header(
    client: TestClient,
    email: str,
    password: str,
    *,
    full_name: str = "Test User",
) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_header(client: TestClient) -> dict:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_owner_creates_team_and_stranger_is_forbidden(client: TestClient) -> None:
    owner = _auth_header(client, "owner@example.com", "SecurePass1!")
    stranger = _auth_header(client, "stranger@example.com", "SecurePass1!")

    created = client.post(
        "/api/v1/teams",
        headers=owner,
        json={"name": "Design", "description": "Board work"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["team_role"] == "owner"
    assert body["member_count"] == 1
    team_id = body["id"]

    hidden = client.get(f"/api/v1/teams/{team_id}", headers=stranger)
    assert hidden.status_code == 403

    admin_view = client.get(f"/api/v1/teams/{team_id}", headers=_admin_header(client))
    assert admin_view.status_code == 200
    assert admin_view.json()["team_role"] is None

    listed = client.get("/api/v1/teams", headers=owner)
    assert listed.status_code == 200
    assert [team["name"] for team in listed.json()] == ["Design"]


def test_admin_owns_the_seed_team(client: TestClient) -> None:
    admin = _admin_header(client)
    teams = client.get("/api/v1/teams", headers=admin)
    assert teams.status_code == 200
    platform = next(team for team in teams.json() if team["name"] == "Platform")
    assert platform["id"] == 1
    assert platform["team_role"] == "owner"

    tasks = client.get("/api/v1/teams/1/tasks", headers=admin)
    assert tasks.status_code == 200
    assert tasks.json()[0]["title"] == "Write the API guide"
    assert tasks.json()[0]["status"] == "todo"


def test_member_workflow_and_status_rules(client: TestClient) -> None:
    owner = _auth_header(client, "lead@example.com", "SecurePass1!", full_name="Lead")
    member = _auth_header(client, "dev@example.com", "SecurePass1!", full_name="Dev")

    team_id = client.post(
        "/api/v1/teams",
        headers=owner,
        json={"name": "Build", "description": ""},
    ).json()["id"]

    added = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=owner,
        json={"email": "dev@example.com"},
    )
    assert added.status_code == 201
    assert added.json()["team_role"] == "member"
    member_id = added.json()["user_id"]

    denied = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=member,
        json={"email": "admin@example.com"},
    )
    assert denied.status_code == 403

    created = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=member,
        json={"title": "Ship the filter", "assignee_email": "dev@example.com"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["status"] == "todo"
    assert created.json()["assignee_id"] == member_id

    jump = client.patch(
        f"/api/v1/teams/{team_id}/tasks/{task_id}",
        headers=member,
        json={"status": "done"},
    )
    assert jump.status_code == 409

    started = client.patch(
        f"/api/v1/teams/{team_id}/tasks/{task_id}",
        headers=member,
        json={"status": "in_progress"},
    )
    assert started.status_code == 200

    finished = client.patch(
        f"/api/v1/teams/{team_id}/tasks/{task_id}",
        headers=owner,
        json={"status": "done"},
    )
    assert finished.status_code == 200
    assert finished.json()["status"] == "done"

    only_done = client.get(
        f"/api/v1/teams/{team_id}/tasks",
        headers=member,
        params={"status": "done"},
    )
    assert [task["id"] for task in only_done.json()] == [task_id]

    owned = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=owner,
        json={"title": "Owner note"},
    )
    assert owned.status_code == 201
    owned_id = owned.json()["id"]
    denied_delete = client.delete(
        f"/api/v1/teams/{team_id}/tasks/{owned_id}",
        headers=member,
    )
    assert denied_delete.status_code == 403
    removed = client.delete(f"/api/v1/teams/{team_id}/tasks/{owned_id}", headers=owner)
    assert removed.status_code == 204


def test_assignee_must_be_a_member_and_owner_cannot_be_removed(client: TestClient) -> None:
    owner = _auth_header(client, "boss@example.com", "SecurePass1!")
    _auth_header(client, "outsider@example.com", "SecurePass1!")
    team_id = client.post("/api/v1/teams", headers=owner, json={"name": "Ops"}).json()["id"]

    rejected = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=owner,
        json={"title": "Page someone", "assignee_email": "outsider@example.com"},
    )
    assert rejected.status_code == 409

    duplicate = client.post("/api/v1/teams", headers=owner, json={"name": "ops"})
    assert duplicate.status_code == 409

    owner_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
    remove_owner = client.delete(f"/api/v1/teams/{team_id}/members/{owner_id}", headers=owner)
    assert remove_owner.status_code == 409


def test_removing_a_member_clears_their_assignments(client: TestClient) -> None:
    owner = _auth_header(client, "pm@example.com", "SecurePass1!")
    member_headers = _auth_header(client, "ic@example.com", "SecurePass1!")
    team_id = client.post("/api/v1/teams", headers=owner, json={"name": "Crew"}).json()["id"]
    member_id = client.get("/api/v1/auth/me", headers=member_headers).json()["id"]
    client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=owner,
        json={"email": "ic@example.com"},
    )
    task_id = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=owner,
        json={"title": "Write notes", "assignee_email": "ic@example.com"},
    ).json()["id"]

    removed = client.delete(f"/api/v1/teams/{team_id}/members/{member_id}", headers=owner)
    assert removed.status_code == 204
    task = client.get(f"/api/v1/teams/{team_id}/tasks/{task_id}", headers=owner)
    assert task.json()["assignee_id"] is None

    gone = client.delete(f"/api/v1/teams/{team_id}", headers=owner)
    assert gone.status_code == 204
    missing = client.get(f"/api/v1/teams/{team_id}/tasks/{task_id}", headers=owner)
    assert missing.status_code == 404


def test_tasks_require_a_token(client: TestClient) -> None:
    response = client.get("/api/v1/teams")
    assert response.status_code == 401
