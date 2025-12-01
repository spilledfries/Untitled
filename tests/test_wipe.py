import os
import tempfile
from datetime import datetime
import pytest
from pkg.reusekit import Device, Storage, Wipe
from pkg.reusekit.errors import ReuseKitError


class DummySession:
    def __init__(self, device):
        self.device = device
        self.workdir = tempfile.mkdtemp()
        def _noop(*args, **kwargs):
            pass
        self.log = _noop

def make_file_device(size_bytes: int) -> Storage:
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, "wb") as f:
        f.truncate(size_bytes)
    return Storage(name="testdisk", path=path, size_bytes=size_bytes, transport="file")

def test_wipe_nist_clear_success():
    st = make_file_device(8 * 1024 * 1024)
    dev = Device(id="dev1", vendor="v", model="m", serial=None, storage=[st], created_at=datetime.utcnow())
    sess = DummySession(dev)
    task = Wipe(method="nist_clear", verify=True, samples=6, seed=1)
    art = task.run(sess)
    assert art.kind == "wipe_report"
    with open(st.path, "rb") as f:
        chunk = f.read(1024 * 1024)
        assert set(chunk) == {0}

def test_wipe_verify_mismatch():
    st = make_file_device(4 * 1024 * 1024)
    dev = Device(id="dev2", vendor="v", model="m", serial=None, storage=[st], created_at=datetime.utcnow())
    sess = DummySession(dev)
    task = Wipe(method="nist_clear", verify=True, samples=8, seed=42)
    art = task.run(sess)
    with open(st.path, "r+b") as f:
        f.seek(12345)
        f.write(b"\x01")
        f.flush()
        os.fsync(f.fileno())
    with pytest.raises(ReuseKitError) as ei:
        task._verify_zero_samples(st)
    assert ei.value.code == "VERIFY_MISMATCH"

def test_safety_blocks_dev_without_env():
    st = Storage(name="realdev", path="/dev/sdz", size_bytes=1024, transport="sata")
    dev = Device(id="dev3", vendor="v", model="m", serial=None, storage=[st], created_at=datetime.utcnow())
    sess = DummySession(dev)
    task = Wipe()
    with pytest.raises(ReuseKitError) as ei:
        task.run(sess)
    assert ei.value.code == "WRITE_BLOCKED"
