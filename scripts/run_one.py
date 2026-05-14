#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path

def run(cmd, cwd, env=None):
    print('$ ' + ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, env=env)

def ensure_local_library(root: Path, launcher_dir: Path) -> None:
    launcher_config = launcher_dir / 'launcher.json'
    if not launcher_config.exists():
        return
    data = json.loads(launcher_config.read_text())
    import physioblocks

    physioblocks_library = Path(physioblocks.__file__).resolve().parent / 'library'
    physioblocks_aliases = physioblocks_library / 'aliases'
    library_path = str((root / 'fontan_blocks').absolute())
    user_library_path = str((launcher_dir / 'user_library').absolute())
    libraries = [
        str(physioblocks_library),
        user_library_path,
        library_path,
    ]
    libraries += [str(Path(p)) for p in data.get('libraries', []) if Path(p).exists()]
    data['libraries'] = list(dict.fromkeys(libraries))

    aliases = [
        str(physioblocks_aliases),
        str((launcher_dir / 'user_aliases').absolute()),
    ]
    aliases += [str(Path(p)) for p in data.get('aliases', []) if Path(p).exists()]
    data['aliases'] = list(dict.fromkeys(aliases))
    launcher_config.write_text(json.dumps(data, indent=4) + '\n')

def main():
    p = argparse.ArgumentParser(description='Run one Fontan PhysioBlocks config.')
    p.add_argument('config', type=Path)
    p.add_argument('--series', default=None)
    p.add_argument('--launcher-dir', type=Path, default=Path('runs'))
    p.add_argument('-v', '--verbose', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    cfg = args.config if args.config.is_absolute() else root / args.config
    work = args.launcher_dir if args.launcher_dir.is_absolute() else root / args.launcher_dir
    work.mkdir(parents=True, exist_ok=True)
    if not (work / 'launcher.json').exists():
        run([sys.executable, '-m', 'physioblocks.launcher.configure', '-d', str(work)], root)
    ensure_local_library(root, work)
    cmd = [sys.executable, '-m', 'physioblocks.launcher', str(cfg)]
    if args.verbose:
        cmd.append('-v')
    if args.series:
        cmd += ['-s', args.series]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root) + os.pathsep + env.get('PYTHONPATH', '')
    run(cmd, work, env=env)
if __name__ == '__main__':
    main()
