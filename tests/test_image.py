"""The test of the image (README.md, "Tests"). Python standard library and
the Docker CLI only. IMAGE_REF names the image.

The server runs as in its pod: HTTP mode with a bearer token, its own
approval off, a strict host key, and a read-only root file system with no
capability. Its one target is a fake host (tests/sshd) with a normal user,
on an internal Docker network. The keys and the token are made at the start
of the test and deleted at its end; none is in git. The calls go from a
Python container (tests/client.py) on the same network.
"""

import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

IMAGE = os.environ["IMAGE_REF"]
CLIENT_IMAGE = os.environ.get(
    "CLIENT_IMAGE",
    "python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928",
)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPSTREAM_COMMIT = "e31e99b9184ba6b3dd7b65ceb717c7620ddbd828"
TAG = uuid.uuid4().hex[:8]
UID = f"{os.getuid()}:{os.getgid()}"
HARDENED = [
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--user",
    UID,
    "--memory",
    "512m",
    "--tmpfs",
    f"/tmp:uid={os.getuid()},gid={os.getgid()}",
    "--tmpfs",
    f"/audit:uid={os.getuid()},gid={os.getgid()},mode=0700",
    "-e",
    "HOME=/tmp",
    "-e",
    "XDG_DATA_HOME=/audit",
]
CONFIG = """[defaults]
defaultProfile = "agent"
approvalMode = "auto"
commandTimeoutMs = 30000

[[profiles]]
name = "agent"
host = "testhost"
port = 22
user = "agent"
auth = "key"
keyRef = "/keys/agent_ed25519"
trustedHostKey = "{fingerprint}"
role = "operator"
group = "staging"
approvalPolicy = "auto"
announceAgent = false
"""


def docker(*args, check=True, timeout=300):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=timeout
    )


class ImageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="host-mcp-test-"))
        cls.containers, cls.token = [], secrets.token_hex(24)
        cls.net = f"host-mcp-test-{TAG}"
        cls.sshd_image = f"host-mcp-test-sshd:{TAG}"
        keys = cls.tmp / "keys"
        keys.mkdir(mode=0o700)
        docker("build", "-q", "-t", cls.sshd_image, str(HERE / "sshd"))
        for key in ("agent_ed25519", "host_ed25519"):
            docker(
                "run",
                "--rm",
                "--network",
                "none",
                "--user",
                UID,
                "-v",
                f"{keys}:/k",
                cls.sshd_image,
                "ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "test",
                "-f",
                f"/k/{key}",
            )
        line = docker(
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            UID,
            "-v",
            f"{keys}:/k:ro",
            cls.sshd_image,
            "ssh-keygen",
            "-lf",
            "/k/host_ed25519.pub",
        ).stdout
        cls.fingerprint = line.split()[1]
        assert cls.fingerprint.startswith("SHA256:"), "no fingerprint"
        docker("network", "create", "--internal", cls.net)
        cls.run_container("testhost", "-v", f"{keys}:/keys:ro", cls.sshd_image)
        cls.start_server("sshmcp", cls.fingerprint)
        # A server that pins another host key.
        cls.start_server("wrongkey", "SHA256:" + "A" * 43)
        cls.wait_ready("sshmcp")
        cls.wait_ready("wrongkey")

    @classmethod
    def tearDownClass(cls):
        for name in cls.containers:
            docker("rm", "-f", name, check=False)
        docker("network", "rm", cls.net, check=False)
        docker("image", "rm", "-f", cls.sshd_image, check=False)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def run_container(cls, alias, *args):
        name = f"host-mcp-test-{alias}-{TAG}"
        docker(
            "run",
            "-d",
            "--name",
            name,
            "--network",
            cls.net,
            "--network-alias",
            alias,
            *args,
        )
        cls.containers.append(name)
        return name

    @classmethod
    def start_server(cls, alias, fingerprint):
        cfg = cls.tmp / f"cfg-{alias}"
        cfg.mkdir(mode=0o700)
        (cfg / "config.toml").write_text(CONFIG.format(fingerprint=fingerprint))
        (cfg / "config.toml").chmod(0o600)
        cls.run_container(
            alias,
            *HARDENED,
            "-v",
            f"{cfg}:/cfg:ro",
            "-v",
            f"{cls.tmp}/keys/agent_ed25519:/keys/agent_ed25519:ro",
            IMAGE,
            "--config=/cfg/config.toml",
            "--transport=http",
            "--httpHost=0.0.0.0",
            "--httpPort=3000",
            "--hostKeyMode=strict",
            f"--allowedHosts={alias},{alias}:3000",
            f"--bearerToken={cls.token}",
        )

    @classmethod
    def call(cls, alias, calls=(), token=True, host=None):
        args = {
            "url": f"http://{alias}:3000/",
            "token": cls.token if token is True else token,
            "host": host,
            "calls": list(calls),
        }
        done = docker(
            "run",
            "--rm",
            "--network",
            cls.net,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--user",
            "65534:65534",
            "-v",
            f"{HERE}/client.py:/client.py:ro",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            CLIENT_IMAGE,
            "python",
            "-I",
            "/client.py",
            json.dumps(args),
            timeout=120,
        )
        return json.loads(done.stdout)

    @classmethod
    def wait_ready(cls, alias, seconds=60):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                if cls.call(alias)["status"] == 200:
                    return
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                pass
            time.sleep(1)
        name = f"host-mcp-test-{alias}-{TAG}"
        logs = docker("logs", name, check=False)
        raise AssertionError(
            f"not ready: {alias}\n{logs.stdout[-2000:]}{logs.stderr[-2000:]}"
        )

    def read(self, alias, command):
        out = self.call(
            alias,
            [
                [
                    "tools/call",
                    {
                        "name": "read-command",
                        "arguments": {"command": command, "profile": "agent"},
                    },
                ]
            ],
        )
        (result,) = out["results"]
        return json.dumps(result["body"])

    def test_the_image_is_the_upstream_tag_and_runs_as_65532(self):
        labels = json.loads(
            docker(
                "image", "inspect", IMAGE, "--format", "{{json .Config.Labels}}"
            ).stdout
        )
        self.assertEqual(labels["io.github.tnwks.upstream.revision"], UPSTREAM_COMMIT)
        self.assertEqual(labels["io.github.tnwks.upstream.version"], "v2.26.0")
        run = docker(
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "node",
            IMAGE,
            "-p",
            "const p = require('/app/package.json'); [process.getuid(), p.name, p.version].join(' ')",
        )
        self.assertEqual(run.stdout.strip(), "65532 ssh-mcp 2.26.0")
        self.assertIn(
            "MIT",
            docker(
                "run",
                "--rm",
                "--network",
                "none",
                "--entrypoint",
                "head",
                IMAGE,
                "-n",
                "1",
                "/app/LICENSE",
            ).stdout,
        )

    def test_a_call_with_no_token_or_another_token_gets_401(self):
        self.assertEqual(self.call("sshmcp", token=None)["status"], 401)
        self.assertEqual(
            self.call("sshmcp", token=secrets.token_hex(24))["status"], 401
        )

    def test_a_host_header_outside_the_allowed_hosts_is_refused(self):
        self.assertEqual(self.call("sshmcp", host="evil.example:3000")["status"], 403)

    def test_the_server_lists_the_tools_of_the_pinned_dump(self):
        (result,) = self.call("sshmcp", [["tools/list", {}]])["results"]
        names = sorted(t["name"] for t in result["body"]["result"]["tools"])
        dump = json.loads((ROOT / "tools/ssh-mcp.json").read_text())["tools"]
        self.assertEqual(names, dump)

    def test_a_listed_read_runs_as_the_normal_user_of_the_host(self):
        self.assertIn("test host ok", self.read("sshmcp", "cat /etc/test-motd"))
        denied = self.read("sshmcp", "cat /etc/test-root-only")
        self.assertNotIn("root only", denied)
        self.assertIn("Permission denied", denied)

    def test_a_host_key_that_is_not_the_pinned_one_gets_no_connection(self):
        out = self.read("wrongkey", "cat /etc/test-motd")
        self.assertNotIn("test host ok", out)
        self.assertIn("HOST_KEY_PIN_MISMATCH", out)


if __name__ == "__main__":
    unittest.main()
