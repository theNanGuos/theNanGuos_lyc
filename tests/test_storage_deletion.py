from pathlib import Path

import pytest

from the_nanguos.services.storage import ArtifactStore


def test_delete_request_rejects_root_traversal_and_symlink(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outside = tmp_path / "outside"
    outputs.mkdir(); outside.mkdir()
    store = ArtifactStore(outputs)

    for request_id in ("..", "../outside", "", "a/b"):
        with pytest.raises(ValueError):
            store.delete_request(request_id)

    link = outputs / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows environment")
    with pytest.raises(ValueError, match="symbolic link"):
        store.delete_request("linked")
    assert outside.exists()
