import io
import os
import pathlib
import platform
import sys
import urllib.request

from invoke import task

deps_options = ("runtime", "test", "dev")


@task
def install_deps(c, package=deps_options[0]):
    """install dependencies for runtime (default) or extra packages

    packages:
        - runtime: default, to run the backend
        - test: to run the test suite
        - dev: all deps to develop the backend"""
    if package not in deps_options:
        print(
            f"Invalid deps package `{package}`. Choose from: {','.join(deps_options)}"
        )
        sys.exit(1)

    try:
        import toml
    except ImportError:
        c.run("pip install toml>=0.10.2")

    packages = []
    manifest = toml.load("pyproject.toml")
    # include deps from required package and previous ones in list
    for option in deps_options[: deps_options.index("test") + 1]:
        packages += manifest["dependencies"][option]

    c.run(
        "pip install -r /dev/stdin",
        in_stream=io.StringIO("\n".join(packages)),
    )

    if package == "dev":
        c.run("pre-commit install", pty=True)


@task
def test(c, args="", path=""):
    """execute pytest with coverage

    args: additional pytest args to pass. ex: -x -v
    path: sub-folder or test file to test to limit scope"""
    with c.cd("src"):
        c.run(
            f"python -m pytest --cov=backend --cov-report term-missing {args} "
            f"../tests{'/' + path if path else ''}",
            pty=True,
        )
        c.run("coverage xml", pty=True)


@task
def get_codecov(c):
    """codecov binary path. Downloaded first if not present"""
    has_system_bin = c.run("command -v codecov", warn=True).exited == 0
    codecov_bin = pathlib.Path("./codecov").resolve()

    # download a local copy if none present
    if not codecov_bin.exists() and not has_system_bin:
        system = {"Linux": "linux", "Darwin": "macos"}.get(platform.system(), "-")
        url = f"https://uploader.codecov.io/latest/{system}/codecov"
        print("Downloading codecov from", url)
        with urllib.request.urlopen(url) as response, open(  # nosec
            codecov_bin, "wb"
        ) as fh:
            fh.write(response.read())
        c.run(f"chmod +x {codecov_bin}")
        return str(codecov_bin)
    if has_system_bin:
        return "codecov"
    return codecov_bin


@task
def upload_coverage(c):
    """upload coverage report to codecov. requires CODECOV_TOKEN"""
    report_fpath = pathlib.Path("src/coverage.xml")
    if not report_fpath.exists():
        print(f"Coverage report missing at {report_fpath}. Launching tests…")
        test(c)

    codecov_bin = get_codecov(c)
    token = os.getenv("CODECOV_TOKEN")
    c.run(
        f"{codecov_bin} --file {report_fpath}" + (f" --token {token}" if token else ""),
        pty=True,
    )


@task
def serve(c, args=""):
    """run devel HTTP server locally. Use --args to specify additional uvicorn args"""
    with c.cd("src"):
        c.run(f"python -m uvicorn backend.main:app --reload {args}", pty=True)
