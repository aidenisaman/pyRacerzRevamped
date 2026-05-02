"""
PyInstaller build script for pyRacerzRevamped.

Creates a standalone executable distribution that runs on target machines
without requiring Python/pygame installation.

Usage:
  python installer.py
  python installer.py --clean
  python installer.py --no-zip
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> None:
  print("Running:", " ".join(cmd))
  subprocess.run(cmd, cwd=str(cwd), check=True)


def get_build_python(root: Path) -> str:
  venv_dir = root / ".venv-build"
  if os.name == "nt":
    venv_python = venv_dir / "Scripts" / "python.exe"
  else:
    venv_python = venv_dir / "bin" / "python"

  if not venv_python.exists():
    print("Creating local build virtual environment...")
    run_cmd([sys.executable, "-m", "venv", str(venv_dir)], root)

  return str(venv_python)


def build(clean: bool, no_zip: bool) -> None:
  root = Path(__file__).resolve().parent
  spec_file = root / "pyRacerz.spec"

  if not spec_file.exists():
    raise FileNotFoundError(f"Missing spec file: {spec_file}")

  if clean:
    print("Cleaning previous build output...")
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "dist", ignore_errors=True)

  build_python = get_build_python(root)

  # Ensure build dependency is present in the isolated build environment.
  run_cmd([build_python, "-m", "pip", "install", "--upgrade", "pip"], root)
  run_cmd([build_python, "-m", "pip", "install", "--upgrade", "pyinstaller", "pygame", "numpy"], root)

  # Build using the existing project spec, which already bundles required assets.
  run_cmd([build_python, "-m", "PyInstaller", "--noconfirm", str(spec_file)], root)

  dist_dir = root / "dist"
  exe_name = "pyRacerz.exe" if os.name == "nt" else "pyRacerz"

  app_dir = None
  app_exe = None
  if dist_dir.exists():
    for child in sorted(dist_dir.iterdir()):
      if child.is_dir() and (child / exe_name).exists():
        app_dir = child
        app_exe = child / exe_name
        break

  if app_dir is None or app_exe is None:
    raise FileNotFoundError("Could not find built app folder in dist/ containing pyRacerz executable")

  if not no_zip:
    zip_base = dist_dir / app_dir.name
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=str(dist_dir), base_dir=app_dir.name)
    print(f"Created portable archive: {archive}")

  print("Build completed successfully.")
  print(f"Executable: {app_exe}")
  print("Distribute the built folder/archive and run the executable, not pyRacerz.py.")


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Build pyRacerz standalone executable with PyInstaller")
  parser.add_argument("--clean", action="store_true", help="remove existing build/dist before building")
  parser.add_argument("--no-zip", action="store_true", help="skip zip archive creation")
  return parser.parse_args()


if __name__ == "__main__":
  args = parse_args()
  try:
    build(clean=args.clean, no_zip=args.no_zip)
  except subprocess.CalledProcessError as exc:
    print(f"Build command failed with exit code {exc.returncode}")
    raise
  except Exception as exc:
    print(f"Build failed: {exc}")
    raise
