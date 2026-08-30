import copy
import fcntl
import json
import os
import re
import secrets
import stat
from contextlib import suppress
from pathlib import Path

MOD_ID_LIST_RE = re.compile(r"^[A-Z\d,=.]+$")
MOD_ID_RE = re.compile(r"^[0-9A-F]{16}$")
MOD_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MOUNT_ESCAPE_RE = re.compile(r"\\([0-7]{3})")
MAX_SERVER_DATA_SIZE = 1024 * 1024
MAX_PRUNE_MANIFEST_SIZE = 16 * 1024 * 1024
MOUNTINFO_PATH = "/proc/self/mountinfo"
PRUNE_MANIFEST_FILE = ".mod-prune.json"
PRUNE_QUARANTINE_PREFIX = ".mod-prune-"
PRUNE_QUARANTINE_RE = re.compile(r"^\.mod-prune-[0-9a-f]{16}$")
SERVER_DATA_FILE = "ServerData.json"
DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
ENTRY_OPEN_FLAGS = os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC
WORKSHOP_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC


def env_defined(env, key):
    return key in env and len(env[key]) > 0


def bool_str(text):
    return text.strip().lower() == "true"


def split_csv(text):
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_int(env, key):
    try:
        return int(env[key])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError(f"Invalid {key}: {env.get(key)!r}") from err


def env_str(env, key):
    return env[key]


def env_bool(env, key):
    return bool_str(env[key])


def env_csv(env, key):
    return split_csv(env[key])


def env_navmesh_streaming(env, key):
    if env[key].lower() == "all":
        return []
    return split_csv(env[key])


def load_json_file(path):
    try:
        with open(path, encoding="utf-8-sig") as json_file:
            return json.load(json_file)
    except (OSError, ValueError) as err:
        raise ValueError(f"Failed to load {path}: {err}") from err


def validate_mod_id(mod_id, source):
    if not isinstance(mod_id, str) or not MOD_ID_RE.fullmatch(mod_id):
        raise ValueError(f"Invalid mod ID in {source}: {mod_id!r}")
    return mod_id


def configured_mod_ids(config_path):
    config = load_json_file(config_path)
    game = config.get("game") if isinstance(config, dict) else None
    if not isinstance(game, dict):
        raise ValueError(f"{config_path} does not contain game")
    mods = game.get("mods", [])
    if not isinstance(mods, list):
        raise ValueError(f"game.mods in {config_path} must be an array")

    mod_ids = set()
    for mod in mods:
        mod_id = mod.get("modId") if isinstance(mod, dict) else None
        mod_ids.add(validate_mod_id(mod_id, config_path))
    return mod_ids


def dependency_ids(server_data_path, dependencies):
    if not isinstance(dependencies, list):
        raise ValueError(f"dependencies in {server_data_path} must be an array")

    mod_ids = set()
    for dependency in dependencies:
        if isinstance(dependency, str):
            mod_id = dependency
        elif isinstance(dependency, dict):
            mod_id = dependency.get("id") or dependency.get("modId")
        else:
            mod_id = None
        try:
            mod_ids.add(validate_mod_id(mod_id, server_data_path))
        except ValueError as err:
            raise ValueError(
                f"Invalid dependency in {server_data_path}: {dependency!r}"
            ) from err
    return mod_ids


def load_server_data(mod_fd, server_data_path):
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
    server_data_fd = None
    try:
        server_data_fd = os.open(SERVER_DATA_FILE, flags, dir_fd=mod_fd)
        server_data_stat = os.fstat(server_data_fd)
        if not stat.S_ISREG(server_data_stat.st_mode):
            raise ValueError(f"{server_data_path} is not a regular file")
        if server_data_stat.st_size > MAX_SERVER_DATA_SIZE:
            raise ValueError(f"{server_data_path} exceeds the metadata size limit")
        with os.fdopen(server_data_fd, "rb") as server_data_file:
            server_data_fd = None
            content = server_data_file.read(MAX_SERVER_DATA_SIZE + 1)
        if len(content) > MAX_SERVER_DATA_SIZE:
            raise ValueError(f"{server_data_path} exceeds the metadata size limit")
        return json.loads(content.decode("utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as err:
        raise ValueError(f"Failed to load {server_data_path}: {err}") from err
    finally:
        if server_data_fd is not None:
            os.close(server_data_fd)


def load_installed_mod(mod_id, mod_fd, mod_path):
    server_data_path = mod_path / SERVER_DATA_FILE
    server_data = load_server_data(mod_fd, server_data_path)
    if not isinstance(server_data, dict):
        raise ValueError(f"{server_data_path} must contain an object")

    metadata_mod_id = server_data.get("id")
    name = server_data.get("name")
    revision = server_data.get("revision")
    if (
        not isinstance(metadata_mod_id, str)
        or metadata_mod_id != mod_id
        or not MOD_ID_RE.fullmatch(metadata_mod_id)
    ):
        raise ValueError(f"id in {server_data_path} does not match its directory")
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid name in {server_data_path}")
    if not isinstance(revision, dict):
        raise ValueError(f"Invalid revision in {server_data_path}")
    if not isinstance(revision.get("version"), str) or not revision["version"]:
        raise ValueError(f"Invalid revision.version in {server_data_path}")
    downloaded = revision.get("downloaded")
    if not isinstance(downloaded, bool) or not downloaded:
        raise ValueError(f"Mod in {server_data_path} is not fully downloaded")

    mod_stat = os.fstat(mod_fd)
    return {
        "id": metadata_mod_id,
        "name": name,
        "dependencies": dependency_ids(server_data_path, revision.get("dependencies")),
        "path": mod_path,
        "stat": mod_stat,
    }


def decode_mount_path(path):
    return MOUNT_ESCAPE_RE.sub(lambda match: chr(int(match.group(1), 8)), path)


def mounted_paths():
    try:
        with open(
            MOUNTINFO_PATH, encoding="utf-8", errors="surrogateescape"
        ) as mountinfo_file:
            paths = set()
            for line in mountinfo_file:
                fields = line.split()
                if len(fields) < 5:
                    raise ValueError(f"Invalid entry in {MOUNTINFO_PATH}: {line!r}")
                paths.add(Path(decode_mount_path(fields[4])))
            return paths
    except OSError as err:
        raise OSError(f"Failed to read {MOUNTINFO_PATH}: {err}") from err


def contains_mount(path, mount_paths):
    return any(
        mount_path == path or path in mount_path.parents for mount_path in mount_paths
    )


def fd_mount_id(file_descriptor):
    fdinfo_path = f"/proc/self/fdinfo/{file_descriptor}"
    try:
        with open(fdinfo_path, encoding="utf-8") as fdinfo_file:
            for line in fdinfo_file:
                if line.startswith("mnt_id:"):
                    return int(line.split(":", 1)[1])
    except (OSError, ValueError) as err:
        raise OSError(
            f"Failed to read mount ID for file descriptor {file_descriptor}: {err}"
        ) from err
    raise OSError(f"Mount ID is missing from {fdinfo_path}")


def validate_open_entry(file_descriptor, expected_stat, expected_mount_id, path):
    actual_stat = os.fstat(file_descriptor)
    if (
        actual_stat.st_dev != expected_stat.st_dev
        or actual_stat.st_ino != expected_stat.st_ino
    ):
        raise ValueError(f"Filesystem entry changed before pruning: {path}")
    if fd_mount_id(file_descriptor) != expected_mount_id:
        raise ValueError(f"Refusing to prune mounted content: {path}")


def same_entry(actual_stat, expected_stat):
    return (
        actual_stat.st_dev == expected_stat.st_dev
        and actual_stat.st_ino == expected_stat.st_ino
    )


def fd_path(file_descriptor):
    try:
        return Path(os.readlink(f"/proc/self/fd/{file_descriptor}"))
    except OSError as err:
        raise OSError(
            f"Failed to resolve file descriptor {file_descriptor}: {err}"
        ) from err


def open_directory_node(root_fd, node, expected_mount_id):
    chain = []
    current = node
    while current is not None:
        chain.append(current)
        current = current["parent"]

    directory_fd = os.dup(root_fd)
    try:
        for item in reversed(chain):
            next_fd = os.open(item["name"], DIRECTORY_OPEN_FLAGS, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
            validate_open_entry(
                directory_fd, item["stat"], expected_mount_id, item["path"]
            )
        return directory_fd
    except BaseException:
        os.close(directory_fd)
        raise


def remove_empty_directory(root_fd, node, expected_mount_id):
    parent_fd = (
        os.dup(root_fd)
        if node["parent"] is None
        else open_directory_node(root_fd, node["parent"], expected_mount_id)
    )
    try:
        current_stat = os.stat(
            node["name"],
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if not same_entry(current_stat, node["stat"]):
            raise ValueError(f"Filesystem entry changed before pruning: {node['path']}")
        os.rmdir(node["name"], dir_fd=parent_fd)
    except OSError as err:
        raise OSError(f"Failed to remove directory {node['path']}: {err}") from err
    finally:
        os.close(parent_fd)


def remove_file_entry(directory_fd, name, expected_stat, expected_mount_id, path):
    child_fd = os.open(name, ENTRY_OPEN_FLAGS, dir_fd=directory_fd)
    try:
        validate_open_entry(child_fd, expected_stat, expected_mount_id, path)
        os.unlink(name, dir_fd=directory_fd)
    except OSError as err:
        raise OSError(f"Failed to remove file {path}: {err}") from err
    finally:
        os.close(child_fd)


def remove_directory_tree(root_fd, name, expected_stat, expected_mount_id, path):
    current = {
        "name": name,
        "parent": None,
        "path": path,
        "stat": expected_stat,
    }
    while current is not None:
        directory_fd = open_directory_node(root_fd, current, expected_mount_id)
        child_node = None
        removed_current = False
        try:
            with os.scandir(directory_fd) as entries:
                entry = next(entries, None)
            if entry is None:
                remove_empty_directory(root_fd, current, expected_mount_id)
                removed_current = True
            else:
                child_stat = entry.stat(follow_symlinks=False)
                child_path = current["path"] / entry.name
                if stat.S_ISDIR(child_stat.st_mode):
                    child_node = {
                        "name": entry.name,
                        "parent": current,
                        "path": child_path,
                        "stat": child_stat,
                    }
                else:
                    remove_file_entry(
                        directory_fd,
                        entry.name,
                        child_stat,
                        expected_mount_id,
                        child_path,
                    )
        finally:
            os.close(directory_fd)

        if child_node is not None:
            current = child_node
        elif removed_current:
            current = current["parent"]


def create_quarantine(workshop_fd, expected_mount_id):
    for _ in range(10):
        name = f"{PRUNE_QUARANTINE_PREFIX}{secrets.token_hex(8)}"
        try:
            os.mkdir(name, mode=0o700, dir_fd=workshop_fd)
        except FileExistsError:
            continue
        quarantine_fd = None
        try:
            sync_directory(workshop_fd)
            quarantine_stat = os.stat(name, dir_fd=workshop_fd, follow_symlinks=False)
            quarantine_fd = os.open(name, DIRECTORY_OPEN_FLAGS, dir_fd=workshop_fd)
            validate_open_entry(
                quarantine_fd,
                quarantine_stat,
                expected_mount_id,
                fd_path(quarantine_fd),
            )
            return name, quarantine_fd
        except BaseException as err:
            if quarantine_fd is not None:
                os.close(quarantine_fd)
            try:
                os.rmdir(name, dir_fd=workshop_fd)
                sync_directory(workshop_fd)
            except OSError as cleanup_err:
                raise cleanup_err from err
            raise
    raise OSError("Failed to create a unique mod pruning quarantine")


def write_json_at(directory_fd, name, content, size_limit):
    encoded = json.dumps(content).encode("utf-8")
    if len(encoded) > size_limit:
        raise ValueError(f"{name} exceeds the metadata size limit")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    file_fd = None
    try:
        file_fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(file_fd, "wb") as output_file:
            file_fd = None
            output_file.write(encoded)
            output_file.flush()
            os.fsync(output_file.fileno())
    except OSError as err:
        raise OSError(f"Failed to write {name}: {err}") from err
    finally:
        if file_fd is not None:
            os.close(file_fd)


def read_json_at(directory_fd, name, size_limit):
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
    file_fd = None
    try:
        file_fd = os.open(name, flags, dir_fd=directory_fd)
        file_stat = os.fstat(file_fd)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"{name} is not a regular file")
        if file_stat.st_size > size_limit:
            raise ValueError(f"{name} exceeds the metadata size limit")
        with os.fdopen(file_fd, "rb") as input_file:
            file_fd = None
            content = input_file.read(size_limit + 1)
        if len(content) > size_limit:
            raise ValueError(f"{name} exceeds the metadata size limit")
        return json.loads(content.decode("utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, ValueError) as err:
        raise ValueError(f"Failed to load {name}: {err}") from err
    finally:
        if file_fd is not None:
            os.close(file_fd)


def sync_directory(directory_fd):
    try:
        os.fsync(directory_fd)
    except OSError as err:
        raise OSError(f"Failed to sync directory: {err}") from err


def prune_manifest(candidates):
    return {
        "mods": {
            installed_mod["id"]: {
                "device": installed_mod["stat"].st_dev,
                "inode": installed_mod["stat"].st_ino,
            }
            for installed_mod in candidates
        }
    }


def load_prune_manifest(quarantine_fd):
    manifest = read_json_at(quarantine_fd, PRUNE_MANIFEST_FILE, MAX_PRUNE_MANIFEST_SIZE)
    mods = manifest.get("mods") if isinstance(manifest, dict) else None
    if not isinstance(mods, dict):
        raise ValueError(f"Invalid {PRUNE_MANIFEST_FILE}")
    for mod_id, identity in mods.items():
        validate_mod_id(mod_id, PRUNE_MANIFEST_FILE)
        if (
            not isinstance(identity, dict)
            or not isinstance(identity.get("device"), int)
            or not isinstance(identity.get("inode"), int)
        ):
            raise ValueError(f"Invalid mod identity in {PRUNE_MANIFEST_FILE}")
    return manifest


def delete_quarantined_mods(
    quarantine_fd,
    manifest,
    expected_mount_id,
    quarantine_path,
):
    for mod_id, identity in manifest["mods"].items():
        try:
            mod_stat = os.stat(mod_id, dir_fd=quarantine_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if (
            not stat.S_ISDIR(mod_stat.st_mode)
            or mod_stat.st_dev != identity["device"]
            or mod_stat.st_ino != identity["inode"]
        ):
            raise ValueError(f"Invalid quarantined mod entry: {mod_id}")
        remove_directory_tree(
            quarantine_fd,
            mod_id,
            mod_stat,
            expected_mount_id,
            quarantine_path / mod_id,
        )
    sync_directory(quarantine_fd)
    try:
        os.unlink(PRUNE_MANIFEST_FILE, dir_fd=quarantine_fd)
    except OSError as err:
        raise OSError(f"Failed to remove {PRUNE_MANIFEST_FILE}: {err}") from err
    sync_directory(quarantine_fd)


def recover_prune_quarantines(workshop_fd, expected_mount_id, workshop_root):
    with os.scandir(workshop_fd) as entries:
        quarantine_names = [
            entry.name for entry in entries if PRUNE_QUARANTINE_RE.fullmatch(entry.name)
        ]

    for quarantine_name in quarantine_names:
        quarantine_path = workshop_root / quarantine_name
        try:
            quarantine_stat = os.stat(
                quarantine_name, dir_fd=workshop_fd, follow_symlinks=False
            )
        except OSError as err:
            raise OSError(f"Failed to inspect {quarantine_path}: {err}") from err
        if not stat.S_ISDIR(quarantine_stat.st_mode):
            raise ValueError(f"Invalid mod pruning quarantine: {quarantine_path}")
        quarantine_fd = os.open(
            quarantine_name, DIRECTORY_OPEN_FLAGS, dir_fd=workshop_fd
        )
        try:
            validate_open_entry(
                quarantine_fd,
                quarantine_stat,
                expected_mount_id,
                quarantine_path,
            )
            try:
                manifest = load_prune_manifest(quarantine_fd)
            except FileNotFoundError as err:
                with os.scandir(quarantine_fd) as entries:
                    if next(entries, None) is not None:
                        raise ValueError(
                            f"Incomplete mod pruning quarantine: {quarantine_path}"
                        ) from err
            else:
                delete_quarantined_mods(
                    quarantine_fd,
                    manifest,
                    expected_mount_id,
                    quarantine_path,
                )
        finally:
            os.close(quarantine_fd)
        try:
            os.rmdir(quarantine_name, dir_fd=workshop_fd)
        except OSError as err:
            raise OSError(f"Failed to remove {quarantine_path}: {err}") from err
        sync_directory(workshop_fd)
        print(f"Recovered interrupted mod pruning quarantine {quarantine_path}")


def rollback_staged_mods(workshop_fd, quarantine_fd, staged_mods):
    failures = []
    for installed_mod in reversed(staged_mods):
        mod_id = installed_mod["id"]
        try:
            quarantined_stat = os.stat(
                mod_id, dir_fd=quarantine_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            try:
                workshop_stat = os.stat(
                    mod_id, dir_fd=workshop_fd, follow_symlinks=False
                )
            except OSError as err:
                failures.append(f"{mod_id}: {err}")
            else:
                if not same_entry(workshop_stat, installed_mod["stat"]):
                    failures.append(f"{mod_id}: workshop entry changed")
            continue
        if not same_entry(quarantined_stat, installed_mod["stat"]):
            failures.append(f"{mod_id}: quarantined entry changed")
            continue
        try:
            os.rename(
                mod_id,
                mod_id,
                src_dir_fd=quarantine_fd,
                dst_dir_fd=workshop_fd,
            )
        except OSError as err:
            failures.append(f"{mod_id}: {err}")
    sync_directory(quarantine_fd)
    sync_directory(workshop_fd)
    if failures:
        raise OSError(f"Failed to roll back staged mods: {', '.join(failures)}")


def stage_prune_candidates(workshop_fd, expected_mount_id, candidates):
    quarantine_name, quarantine_fd = create_quarantine(workshop_fd, expected_mount_id)
    staged_mods = []
    try:
        write_json_at(
            quarantine_fd,
            PRUNE_MANIFEST_FILE,
            prune_manifest(candidates),
            MAX_PRUNE_MANIFEST_SIZE,
        )
        sync_directory(quarantine_fd)
        for installed_mod in candidates:
            mod_id = installed_mod["id"]
            staged_mods.append(installed_mod)
            os.rename(
                mod_id,
                mod_id,
                src_dir_fd=workshop_fd,
                dst_dir_fd=quarantine_fd,
            )
            staged_stat = os.stat(mod_id, dir_fd=quarantine_fd, follow_symlinks=False)
            if not same_entry(staged_stat, installed_mod["stat"]):
                raise ValueError(
                    f"Mod directory changed before pruning: {installed_mod['path']}"
                )
            staged_fd = os.open(mod_id, DIRECTORY_OPEN_FLAGS, dir_fd=quarantine_fd)
            try:
                validate_open_entry(
                    staged_fd,
                    installed_mod["stat"],
                    expected_mount_id,
                    installed_mod["path"],
                )
            finally:
                os.close(staged_fd)
        sync_directory(quarantine_fd)
        sync_directory(workshop_fd)
        return quarantine_name, quarantine_fd
    except BaseException as err:
        try:
            rollback_staged_mods(workshop_fd, quarantine_fd, staged_mods)
            with suppress(FileNotFoundError):
                os.unlink(PRUNE_MANIFEST_FILE, dir_fd=quarantine_fd)
            sync_directory(quarantine_fd)
            os.rmdir(quarantine_name, dir_fd=workshop_fd)
            sync_directory(workshop_fd)
        except OSError as rollback_err:
            raise rollback_err from err
        finally:
            os.close(quarantine_fd)
        raise


def scan_installed_mods(workshop_fd, workshop_root):
    installed_mods = {}
    invalid_mods = {}
    with os.scandir(workshop_fd) as entries:
        for entry in entries:
            mod_id = entry.name
            if not MOD_ID_RE.fullmatch(mod_id):
                continue
            mod_path = workshop_root / mod_id
            if not entry.is_dir(follow_symlinks=False):
                err = ValueError(f"{mod_path} is not a regular directory")
                invalid_mods[mod_id] = err
                print(f"Skipping invalid mod directory {mod_path}: {err}")
                continue
            try:
                mod_fd = os.open(mod_id, DIRECTORY_OPEN_FLAGS, dir_fd=workshop_fd)
                try:
                    installed_mods[mod_id] = load_installed_mod(
                        mod_id, mod_fd, mod_path
                    )
                finally:
                    os.close(mod_fd)
            except (OSError, ValueError) as err:
                invalid_mods[mod_id] = err
                print(f"Skipping invalid mod directory {mod_path}: {err}")
    return installed_mods, invalid_mods


def retained_mod_ids(configured_ids, installed_mods, invalid_mods):
    retained_ids = set()
    pending_ids = list(configured_ids)
    while pending_ids:
        mod_id = pending_ids.pop()
        if mod_id in retained_ids:
            continue
        retained_ids.add(mod_id)
        if mod_id in invalid_mods:
            raise ValueError(
                f"Cannot safely prune because required mod {mod_id} is invalid: "
                f"{invalid_mods[mod_id]}"
            )
        installed_mod = installed_mods.get(mod_id)
        if installed_mod is not None:
            pending_ids.extend(installed_mod["dependencies"])
    return retained_ids


def validate_prune_candidates(workshop_fd, candidates):
    mount_paths = mounted_paths()
    for installed_mod in candidates:
        mod_id = installed_mod["id"]
        mod_path = installed_mod["path"]
        try:
            current_stat = os.stat(mod_id, dir_fd=workshop_fd, follow_symlinks=False)
        except OSError as err:
            raise ValueError(
                f"Mod directory changed before pruning: {mod_path}"
            ) from err
        if not stat.S_ISDIR(current_stat.st_mode) or not same_entry(
            current_stat, installed_mod["stat"]
        ):
            raise ValueError(f"Mod directory changed before pruning: {mod_path}")
        if contains_mount(mod_path, mount_paths):
            raise ValueError(f"Refusing to prune mounted content: {mod_path}")


def delete_prune_candidates(workshop_fd, expected_mount_id, candidates):
    quarantine_name, quarantine_fd = stage_prune_candidates(
        workshop_fd, expected_mount_id, candidates
    )
    pruned_paths = []
    try:
        for installed_mod in candidates:
            remove_directory_tree(
                quarantine_fd,
                installed_mod["id"],
                installed_mod["stat"],
                expected_mount_id,
                installed_mod["path"],
            )
            print(
                f"Pruned mod {installed_mod['name']} "
                f"({installed_mod['id']}) from {installed_mod['path']}"
            )
            pruned_paths.append(installed_mod["path"])
        sync_directory(quarantine_fd)
        try:
            os.unlink(PRUNE_MANIFEST_FILE, dir_fd=quarantine_fd)
        except OSError as err:
            raise OSError(f"Failed to remove {PRUNE_MANIFEST_FILE}: {err}") from err
        sync_directory(quarantine_fd)
    finally:
        os.close(quarantine_fd)

    try:
        os.rmdir(quarantine_name, dir_fd=workshop_fd)
    except OSError as err:
        raise OSError(f"Failed to remove mod pruning quarantine: {err}") from err
    sync_directory(workshop_fd)
    return pruned_paths


def prune_mods(config_path, workshop_dir):
    configured_ids = configured_mod_ids(config_path)
    try:
        workshop_fd = os.open(workshop_dir, WORKSHOP_OPEN_FLAGS)
    except FileNotFoundError:
        return []
    try:
        fcntl.flock(workshop_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(workshop_fd)
        raise

    try:
        workshop_root = fd_path(workshop_fd)
        workshop_mount_id = fd_mount_id(workshop_fd)
        recover_prune_quarantines(workshop_fd, workshop_mount_id, workshop_root)

        installed_mods, invalid_mods = scan_installed_mods(workshop_fd, workshop_root)
        retained_ids = retained_mod_ids(configured_ids, installed_mods, invalid_mods)
        candidates = [
            installed_mod
            for mod_id, installed_mod in sorted(installed_mods.items())
            if mod_id not in retained_ids
        ]
        if not candidates:
            return []

        validate_prune_candidates(workshop_fd, candidates)
        return delete_prune_candidates(workshop_fd, workshop_mount_id, candidates)
    finally:
        os.close(workshop_fd)


SERVER_ENV_MAP = (
    ("SERVER_BIND_ADDRESS", "bindAddress", env_str),
    ("SERVER_BIND_PORT", "bindPort", parse_int),
    ("SERVER_PUBLIC_ADDRESS", "publicAddress", env_str),
    ("SERVER_PUBLIC_PORT", "publicPort", parse_int),
)
GAME_ENV_MAP = (
    ("GAME_NAME", "name", env_str),
    ("GAME_PASSWORD", "password", env_str),
    ("GAME_PASSWORD_ADMIN", "passwordAdmin", env_str),
    ("GAME_ADMINS", "admins", env_csv),
    ("GAME_SCENARIO_ID", "scenarioId", env_str),
    ("GAME_MAX_PLAYERS", "maxPlayers", parse_int),
    ("GAME_VISIBLE", "visible", env_bool),
    ("GAME_SUPPORTED_PLATFORMS", "supportedPlatforms", env_csv),
    ("GAME_CROSS_PLATFORM", "crossPlatform", env_bool),
    ("GAME_MODS_REQUIRED_BY_DEFAULT", "modsRequiredByDefault", env_bool),
)
GAME_PROPS_ENV_MAP = (
    ("GAME_PROPS_BATTLEYE", "battlEye", env_bool),
    ("GAME_PROPS_DISABLE_THIRD_PERSON", "disableThirdPerson", env_bool),
    ("GAME_PROPS_FAST_VALIDATION", "fastValidation", env_bool),
    ("GAME_PROPS_SERVER_MAX_VIEW_DISTANCE", "serverMaxViewDistance", parse_int),
    ("GAME_PROPS_SERVER_MIN_GRASS_DISTANCE", "serverMinGrassDistance", parse_int),
    ("GAME_PROPS_NETWORK_VIEW_DISTANCE", "networkViewDistance", parse_int),
    ("GAME_PROPS_VON_DISABLE_UI", "VONDisableUI", env_bool),
    ("GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI", "VONDisableDirectSpeechUI", env_bool),
    (
        "GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION",
        "VONCanTransmitCrossFaction",
        env_bool,
    ),
)
PERSISTENCE_ENV_MAP = (
    ("PERSISTENCE_AUTO_SAVE_INTERVAL", "autoSaveInterval", parse_int),
    ("PERSISTENCE_SAVE_RETENTION", "saveRetention", parse_int),
    ("PERSISTENCE_LOAD_SESSION_SAVE", "loadSessionSave", env_bool),
    ("PERSISTENCE_KEEP_SESSION_SAVE", "keepSessionSave", env_bool),
    ("PERSISTENCE_HIVE_ID", "hiveId", parse_int),
)
PERSISTENCE_ENV_KEYS = tuple(key for key, _, _ in PERSISTENCE_ENV_MAP) + (
    "PERSISTENCE_JSON_FILE_PATH",
)
OPERATING_ENV_MAP = (
    ("OPERATING_LOBBY_PLAYER_SYNCHRONISE", "lobbyPlayerSynchronise", env_bool),
    ("OPERATING_DISABLE_CRASH_REPORTER", "disableCrashReporter", env_bool),
    (
        "OPERATING_DISABLE_NAVMESH_STREAMING",
        "disableNavmeshStreaming",
        env_navmesh_streaming,
    ),
    ("OPERATING_DISABLE_SERVER_SHUTDOWN", "disableServerShutdown", env_bool),
    ("OPERATING_DISABLE_AI", "disableAI", env_bool),
    ("OPERATING_PLAYER_SAVE_TIME", "playerSaveTime", parse_int),
    ("OPERATING_AI_LIMIT", "aiLimit", parse_int),
    ("OPERATING_SLOT_RESERVATION_TIMEOUT", "slotReservationTimeout", parse_int),
)


def apply_env_overrides(target, env, env_map):
    for key, name, convert in env_map:
        if env_defined(env, key):
            target[name] = convert(env, key)


def apply_server_config(config, env):
    apply_env_overrides(config, env, SERVER_ENV_MAP)
    if env_defined(env, "SERVER_A2S_ADDRESS") and env_defined(env, "SERVER_A2S_PORT"):
        config["a2s"] = {
            "address": env["SERVER_A2S_ADDRESS"],
            "port": parse_int(env, "SERVER_A2S_PORT"),
        }
    else:
        config.pop("a2s", None)


def apply_rcon_config(config, env):
    required_keys = ("RCON_PASSWORD", "RCON_ADDRESS", "RCON_PORT")
    if not all(env_defined(env, key) for key in required_keys):
        config.pop("rcon", None)
        return
    if env_defined(env, "RCON_BLACKLIST") and env_defined(env, "RCON_WHITELIST"):
        raise ValueError("RCON_BLACKLIST and RCON_WHITELIST cannot both be set")

    rcon = {
        "address": env["RCON_ADDRESS"],
        "port": parse_int(env, "RCON_PORT"),
        "password": env["RCON_PASSWORD"],
        "permission": env.get("RCON_PERMISSION")
        or config.get("rcon", {}).get("permission")
        or "admin",
    }
    if env_defined(env, "RCON_MAX_CLIENTS"):
        rcon["maxClients"] = parse_int(env, "RCON_MAX_CLIENTS")
    if env_defined(env, "RCON_BLACKLIST"):
        rcon["blacklist"] = split_csv(env["RCON_BLACKLIST"])
    if env_defined(env, "RCON_WHITELIST"):
        rcon["whitelist"] = split_csv(env["RCON_WHITELIST"])
    config["rcon"] = rcon


def apply_game_properties(config, env):
    game_properties = config["game"]["gameProperties"]
    apply_env_overrides(game_properties, env, GAME_PROPS_ENV_MAP)
    if env_defined(env, "GAME_MISSION_HEADER_JSON_FILE_PATH"):
        game_properties["missionHeader"] = load_json_file(
            env["GAME_MISSION_HEADER_JSON_FILE_PATH"]
        )
    else:
        game_properties["missionHeader"] = {}


def default_mod_required(env):
    if env_defined(env, "GAME_MODS_REQUIRED_BY_DEFAULT"):
        return bool_str(env["GAME_MODS_REQUIRED_BY_DEFAULT"])
    return None


def parse_mods_ids_list(env, required_default, seen_ids):
    if not MOD_ID_LIST_RE.match(env["GAME_MODS_IDS_LIST"]):
        raise ValueError("Illegal characters in GAME_MODS_IDS_LIST env")

    mods = []
    for mod in split_csv(env["GAME_MODS_IDS_LIST"]):
        mod_details = mod.split("=")
        if not 0 < len(mod_details) < 3:
            raise ValueError(f"{mod} mod not defined properly")
        mod_id = validate_mod_id(mod_details[0], "GAME_MODS_IDS_LIST")
        if mod_id in seen_ids:
            continue
        mod_config = {"modId": mod_id}
        if len(mod_details) == 2:
            if not MOD_VERSION_RE.match(mod_details[1]):
                raise ValueError(f"{mod} mod version does not match the pattern")
            mod_config["version"] = mod_details[1]
        if required_default is not None:
            mod_config["required"] = required_default
        seen_ids.add(mod_id)
        mods.append(mod_config)
    return mods


def parse_mods_json_file(env, required_default, seen_ids):
    json_mods = load_json_file(env["GAME_MODS_JSON_FILE_PATH"])
    if not isinstance(json_mods, list):
        raise ValueError("GAME_MODS_JSON_FILE_PATH must contain an array")

    allowed_keys = ("modId", "name", "version", "required")
    mods = []
    for provided_mod in json_mods:
        if not isinstance(provided_mod, dict) or "modId" not in provided_mod:
            raise ValueError(
                "Entry in GAME_MODS_JSON_FILE_PATH file does not contain modId: "
                f"{provided_mod}"
            )
        mod_id = validate_mod_id(provided_mod["modId"], "GAME_MODS_JSON_FILE_PATH")
        if mod_id in seen_ids:
            continue
        valid_mod = {
            key: provided_mod[key] for key in allowed_keys if key in provided_mod
        }
        if required_default is not None and "required" not in valid_mod:
            valid_mod["required"] = required_default
        seen_ids.add(mod_id)
        mods.append(valid_mod)
    return mods


def apply_mods_config(config, env):
    required_default = default_mod_required(env)
    seen_ids = set()
    mods = []
    if env_defined(env, "GAME_MODS_IDS_LIST"):
        mods.extend(parse_mods_ids_list(env, required_default, seen_ids))
    if env_defined(env, "GAME_MODS_JSON_FILE_PATH"):
        mods.extend(parse_mods_json_file(env, required_default, seen_ids))
    config["game"]["mods"] = mods


def apply_persistence_config(config, env):
    game_properties = config["game"]["gameProperties"]
    if not any(env_defined(env, key) for key in PERSISTENCE_ENV_KEYS):
        game_properties.pop("persistence", None)
        return

    persistence = {}
    apply_env_overrides(persistence, env, PERSISTENCE_ENV_MAP)
    if env_defined(env, "PERSISTENCE_JSON_FILE_PATH"):
        persistence_json = load_json_file(env["PERSISTENCE_JSON_FILE_PATH"])
        for key in ("databases", "storages"):
            if key in persistence_json:
                persistence[key] = persistence_json[key]
    game_properties["persistence"] = persistence


def apply_operating_config(config, env):
    operating = {}
    apply_env_overrides(operating, env, OPERATING_ENV_MAP)
    if env_defined(env, "OPERATING_JOIN_QUEUE_MAX_SIZE"):
        operating["joinQueue"] = {
            "maxSize": parse_int(env, "OPERATING_JOIN_QUEUE_MAX_SIZE")
        }
    if operating:
        config["operating"] = operating
    else:
        config.pop("operating", None)


def build_config(env, base_config):
    config = copy.deepcopy(base_config)
    apply_server_config(config, env)
    apply_rcon_config(config, env)
    apply_env_overrides(config["game"], env, GAME_ENV_MAP)
    apply_game_properties(config, env)
    apply_mods_config(config, env)
    apply_persistence_config(config, env)
    apply_operating_config(config, env)
    return config
