def test_create_project_returns_201(client):
    response = client.post("/projects", json={"name": "Alpha", "description": "First"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alpha"
    assert body["description"] == "First"


def test_create_project_validates_name(client):
    assert client.post("/projects", json={"name": ""}).status_code == 422


def test_list_projects_is_paginated(client):
    for i in range(3):
        client.post("/projects", json={"name": f"P{i}"})

    body = client.get("/projects", params={"page": 2, "size": 2}).json()

    assert body["total"] == 3
    assert body["pages"] == 2
    assert [p["name"] for p in body["items"]] == ["P2"]


def test_get_project_details_and_404(client, project_id):
    assert client.get(f"/projects/{project_id}").json()["id"] == project_id
    response = client.get("/projects/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project 9999 not found"}
