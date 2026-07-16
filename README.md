# Lakehouse

---

## Prerequisites

[V] Python 3.10, 3.11, or 3.12
[V] Docker installed & running
[]


---

## Setup

1. venv init & run
`python3 -m venv .venv` 
`source .venv/bin/activate`

2. Install all needed depedencies (requirements.txt)
`python3 -m pip install -r requirements.txt`


3. Run docker compose up (host minio & postgres services on local machine)
`docker compose up -d`

4. Run `lakehouse-setup.py` for building lakehouse architecture.
- Choose 9 for full initial setup.

5. SQLMesh Project Initiation
```text
- Run `sqlmesh init`
1. What type of project do you want to set up?
- [3]
2. Choose your SQL engine:
- [1]
3. Choose your SQLMesh CLI experience:
- [1]
```

6. 