import os
import shutil
import subprocess
import sys
import tempfile
from typing import Tuple, List


def copy_files_from_repo(repo_url: str, branch: str, repo_target_path_pairs: List[Tuple[str, str]]):
    """
    does `git clone -n --depth=1 REPO_URL`
    For each (repo_path, target_path) pair
        - checkout the file (will need to be inside the repo to do this? call subprocess from inside repo)
        - deletes target_path if it exists (must be a file)
        - moves the repo_path to target_path (must be a file)
    deletes the repo
    :param branch:
    :param repo_url:
    :param repo_target_path_pairs: pair of RELATIVE repo path to ABSOLUTE output paths (if output path is relative, will be relative to current folder)
    :return:
    """

    try:

        with tempfile.TemporaryDirectory(prefix='drojf_umineko_deploy') as repo_clone_path:
            print(f"Will clone [{repo_url}] into [{repo_clone_path}]")

            # # git clone repo to specified folder. give a unique name to avoid conflicting with other files
            subprocess.call(['git', 'clone', '-n', '--depth=1', f'--branch={branch}', repo_url, repo_clone_path])

            # checkout all the repo paths
            for file_in_repo_path, _ in repo_target_path_pairs:
                subprocess.call(['git', 'checkout', 'HEAD', file_in_repo_path], cwd=repo_clone_path)

            # move
            for file_in_repo_path, target_path in repo_target_path_pairs:
                absolute_file_in_repo_path = os.path.join(repo_clone_path, file_in_repo_path)
                # delete target_path
                print(f'Moving {absolute_file_in_repo_path} -> {target_path}')
                if os.path.exists(target_path):
                    os.remove(target_path)

                # ensure target folder exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # move file from repo to destination
                shutil.move(absolute_file_in_repo_path, target_path)

    except PermissionError as permission_error:
        if sys.platform.startswith('win32') and 'WinError' in str(permission_error):
            print(f'Detected Windows folder deletion error - using fallback method.\nError was: "{permission_error}"')
            subprocess.call(['rmdir', '/s', '/q', repo_clone_path], shell=True)
        else:
            raise permission_error


# Umineko Question 1080p Patch
copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'master', [
    (r'InDevelopment/ManualUpdates/0.utf', r'umineko-question/full/0.utf'),
])

# Umineko Question Voice Only Patch
copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'voice_only', [
    (r'InDevelopment/ManualUpdates/0.utf', r'umineko-question/voice-only/0.utf'),
])

# Umineko Answer Full and Voice Only Patch
copy_files_from_repo(r'https://github.com/07th-mod/umineko-answer.git', 'master', [
    (r'0.utf', r'umineko-answer/full/0.utf'),
    (r'voices-only/0.utf', r'umineko-answer/voice-only/0.utf'),
])

# Umineko Answer ADV Mode Patch
copy_files_from_repo(r'https://github.com/07th-mod/umineko-answer.git', 'adv_mode', [
    (r'0.utf', r'umineko-answer/adv-mode/0.utf'),
])

print("Deployment was successful!")
