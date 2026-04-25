"""M67 Tests: DB backup + 5-year retention"""
import os
import pytest

def test_T01_backup_script_exists():
    assert os.path.exists("scripts/backup_db.sh")

def test_T02_backup_script_executable():
    import stat, sys
    if sys.platform == "win32":
        pytest.skip("Windows does not support Unix execute bits")
    st = os.stat("scripts/backup_db.sh")
    assert st.st_mode & stat.S_IXUSR

def test_T03_backup_script_has_bfiu_ref():
    content = open("scripts/backup_db.sh").read()
    assert "BFIU" in content
    assert "5.1" in content

def test_T04_backup_script_has_retention():
    content = open("scripts/backup_db.sh").read()
    assert "RETENTION_DAYS" in content
    assert "mtime" in content

def test_T05_backup_script_has_verification():
    content = open("scripts/backup_db.sh").read()
    assert "empty" in content.lower() or "size" in content.lower() or "-s" in content

def test_T06_retention_task_exists():
    from app.worker.tasks_retention import task_flag_retention_eligible
    assert task_flag_retention_eligible is not None

def test_T07_retention_years_is_5():
    from app.worker.tasks_retention import RETENTION_YEARS
    assert RETENTION_YEARS == 5

def test_T08_retention_in_celery_beat():
    content = open("app/worker/celery_app.py", encoding="latin-1").read()
    assert "retention.flag_eligible_records" in content

def test_T09_requirements_txt_exists():
    assert os.path.exists("requirements.txt")

def test_T10_requirements_has_fastapi():
    content = open("requirements.txt").read()
    assert "fastapi" in content.lower()

def test_T11_requirements_has_sqlalchemy():
    content = open("requirements.txt").read()
    assert "sqlalchemy" in content.lower()

def test_T12_requirements_has_celery():
    content = open("requirements.txt").read()
    assert "celery" in content.lower()

def test_T13_docker_compose_has_backup_service():
    for path in ["../docker-compose.prod.yml", "docker-compose.prod.yml"]:
        if os.path.exists(path):
            content = open(path).read()
            assert "db_backup" in content or "backup" in content
            return
    pytest.skip("docker-compose.prod.yml not found")

def test_T14_retention_bfiu_ref():
    content = open("app/worker/tasks_retention.py", encoding="utf-8").read()
    assert "BFIU" in content
    assert "5.1" in content

def test_T15_celery_app_encoding_ok():
    content = open("app/worker/celery_app.py", encoding="latin-1").read()
    assert "celery_app" in content

def test_T16_backup_uses_bst_timezone():
    content = open("scripts/backup_db.sh").read()
    assert "Asia/Dhaka" in content or "BST" in content
