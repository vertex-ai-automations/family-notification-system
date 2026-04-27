"""Tests for GET /api/members/tree."""


def _add(client, name, **kwargs):
    r = client.post("/api/members", json={"name": name, "birthday": "06-15", **kwargs})
    assert r.status_code == 201
    return r.json()["id"]


def test_tree_empty(client):
    # Remove the seeded John first
    john_id = client.get("/api/members").json()[0]["id"]
    client.delete(f"/api/members/{john_id}")
    r = client.get("/api/members/tree")
    assert r.status_code == 200
    data = r.json()
    assert data == {"nodes": [], "edges": []}


def test_tree_single_node_no_relations(client):
    r = client.get("/api/members/tree")
    assert r.status_code == 200
    data = r.json()
    assert len(data["nodes"]) == 1
    assert data["edges"] == []
    assert data["nodes"][0]["name"] == "John"


def test_tree_parent_child_edges(client):
    parent_id = client.get("/api/members").json()[0]["id"]  # John
    child_id = _add(client, "Jane", mother_id=parent_id)
    r = client.get("/api/members/tree")
    assert r.status_code == 200
    data = r.json()
    assert len(data["nodes"]) == 2
    parent_edges = [e for e in data["edges"] if e["relation"] == "parent"]
    assert len(parent_edges) == 1
    assert parent_edges[0] == {"source": parent_id, "target": child_id, "relation": "parent"}


def test_tree_spouse_edge_deduped(client):
    a_id = client.get("/api/members").json()[0]["id"]
    b_id = _add(client, "Alice")
    # Link A→B; sync_spouse will also set B→A
    client.patch(f"/api/members/{a_id}", json={"spouse_id": b_id})
    r = client.get("/api/members/tree")
    assert r.status_code == 200
    spouse_edges = [e for e in r.json()["edges"] if e["relation"] == "spouse"]
    # Bidirectional FK exists but tree must emit only ONE edge between the pair
    assert len(spouse_edges) == 1
    pair = {spouse_edges[0]["source"], spouse_edges[0]["target"]}
    assert pair == {a_id, b_id}


def test_tree_both_parents(client):
    father_id = client.get("/api/members").json()[0]["id"]
    mother_id = _add(client, "Mary")
    child_id = _add(client, "Sam", mother_id=mother_id, father_id=father_id)
    r = client.get("/api/members/tree")
    assert r.status_code == 200
    parent_edges = [e for e in r.json()["edges"] if e["relation"] == "parent"]
    sources = {e["source"] for e in parent_edges}
    assert sources == {mother_id, father_id}
    for e in parent_edges:
        assert e["target"] == child_id


def test_tree_node_fields(client):
    r = client.get("/api/members/tree")
    assert r.status_code == 200
    node = r.json()["nodes"][0]
    for field in ("id", "name", "mother_id", "father_id", "spouse_id"):
        assert field in node


def test_tree_no_self_reference_allowed(client):
    john_id = client.get("/api/members").json()[0]["id"]
    r = client.patch(f"/api/members/{john_id}", json={"mother_id": john_id})
    assert r.status_code == 400


def test_tree_bad_ref_rejected(client):
    john_id = client.get("/api/members").json()[0]["id"]
    r = client.patch(f"/api/members/{john_id}", json={"father_id": 99999})
    assert r.status_code == 400


# --- Cascade behavior --------------------------------------------------------

def test_delete_clears_child_parent_refs(client):
    parent_id = client.get("/api/members").json()[0]["id"]
    child_id = _add(client, "Kid", mother_id=parent_id)
    r = client.delete(f"/api/members/{parent_id}")
    assert r.status_code == 204
    child = client.get("/api/members").json()
    assert next(c for c in child if c["id"] == child_id)["mother_id"] is None


def test_delete_clears_partner_spouse_ref(client):
    a_id = client.get("/api/members").json()[0]["id"]
    b_id = _add(client, "Partner")
    client.patch(f"/api/members/{a_id}", json={"spouse_id": b_id})
    # Sanity: bidirectional after sync
    members = client.get("/api/members").json()
    assert next(m for m in members if m["id"] == b_id)["spouse_id"] == a_id
    # Delete A — B's spouse_id should be cleared
    r = client.delete(f"/api/members/{a_id}")
    assert r.status_code == 204
    members = client.get("/api/members").json()
    assert next(m for m in members if m["id"] == b_id)["spouse_id"] is None


# --- Spouse triangle (regression for orphaned third party) -------------------

def test_spouse_reassignment_clears_orphaned_third_party(client):
    a_id = client.get("/api/members").json()[0]["id"]
    b_id = _add(client, "Bee")
    c_id = _add(client, "Cee")
    # A↔B
    client.patch(f"/api/members/{a_id}", json={"spouse_id": b_id})
    members = {m["id"]: m for m in client.get("/api/members").json()}
    assert members[a_id]["spouse_id"] == b_id
    assert members[b_id]["spouse_id"] == a_id
    # Now link C↔B — A must be cleared, NOT left pointing at B
    client.patch(f"/api/members/{c_id}", json={"spouse_id": b_id})
    members = {m["id"]: m for m in client.get("/api/members").json()}
    assert members[c_id]["spouse_id"] == b_id
    assert members[b_id]["spouse_id"] == c_id
    assert members[a_id]["spouse_id"] is None, "A was orphaned — invariant broken"


# --- Cycle prevention --------------------------------------------------------

def test_parent_cycle_rejected(client):
    a_id = client.get("/api/members").json()[0]["id"]
    b_id = _add(client, "Bee", mother_id=a_id)
    # Now try to make A's mother B — would create a cycle A→B→A
    r = client.patch(f"/api/members/{a_id}", json={"mother_id": b_id})
    assert r.status_code == 400
