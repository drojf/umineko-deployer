import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Tuple, List


def copy_files_from_repo(repo_url: str, branch: str, web_root: str, repo_target_path_pairs: List[Tuple[str, str]], as_zip):
    """
    does `git clone -n --depth=1 REPO_URL`
    For each (repo_path, target_path) pair
        - checkout the file (will need to be inside the repo to do this? call subprocess from inside repo)
        - deletes target_path if it exists (must be a file)
        - moves the repo_path to target_path (must be a file)
    deletes the repo
    :param web_root:
    :param branch:
    :param repo_url:
    :param repo_target_path_pairs: pair of RELATIVE repo path to ABSOLUTE output paths (if output path is relative, will be relative to current folder)
    :return:
    """

    try:
        with tempfile.TemporaryDirectory(prefix='drojf_umineko_deploy') as repo_clone_path:
            print(f"Will clone [{repo_url}] into [{repo_clone_path}]")

            # git clone repo to specified folder. give a unique name to avoid conflicting with other files
            subprocess.call(['git', 'clone', '-n', '--depth=1', f'--branch={branch}', repo_url, repo_clone_path])

            for file_in_repo_path, rel_target_path in repo_target_path_pairs:
                # checkout all the repo paths
                subprocess.call(['git', 'checkout', 'HEAD', file_in_repo_path], cwd=repo_clone_path)

                # calculate the correct repo path dep on if 'as_zip' is enabled
                original_source_path = os.path.join(repo_clone_path, file_in_repo_path)
                absolute_source_path = original_source_path + '.zip' if as_zip else ''

                #  zip each path if necessary
                if as_zip:
                    print(f'Zipping {original_source_path} -> {absolute_source_path}')
                    with zipfile.ZipFile(absolute_source_path, 'w', compression=zipfile.ZIP_LZMA) as myzip:
                        myzip.write(original_source_path, arcname=os.path.basename(absolute_source_path))

                # delete the target_path
                target_path = os.path.join(web_root, rel_target_path)
                print(f'Deleting {target_path}')
                if os.path.exists(target_path):
                    os.remove(target_path)

                # ensure target folder exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # move file from repo to destination
                print(f'Moving {absolute_source_path} -> {target_path}')
                shutil.move(absolute_source_path, target_path)

    except PermissionError as permission_error:
        if sys.platform.startswith('win32') and 'WinError' in str(permission_error):
            print(f'Detected Windows folder deletion error - using fallback method.\nError was: "{permission_error}"')
            subprocess.call(['rmdir', '/s', '/q', repo_clone_path], shell=True)
        else:
            raise permission_error


def error_exit():
    print("ERROR: need at least 2 arguments. First argument is web folder root, second argument is 'question' or 'answer' to determine which repo to update")
    exit(-1)


if len(sys.argv) < 3:
    error_exit()

web_folder = sys.argv[1] # eg r'/home/developer/web'
which_game = sys.argv[2] # 'question' or 'answer'
print(f"Web folder: [{web_folder}] Game: [{which_game}]")


if which_game == 'question':
    # Umineko Question 1080p Patch
    copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'master', web_folder, [
        (r'InDevelopment/ManualUpdates/0.utf', r'Beato/script-full.zip'),
    ], as_zip=True)

    # Umineko Question Voice Only Patch
    copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'voice_only', web_folder, [
        (r'InDevelopment/ManualUpdates/0.utf', r'Beato/script-voice-only.zip'),
    ], as_zip=True)
elif which_game == 'answer':
    # Umineko Answer Full and Voice Only Patch
    copy_files_from_repo(r'https://github.com/07th-mod/umineko-answer.git', 'master', web_folder, [
        (r'0.utf', r'Bern/script-full.zip'),
        (r'voices-only/0.utf', r'Bern/script-voice-only.zip'),
    ], as_zip=True)

    # Umineko Answer ADV Mode Patch
    copy_files_from_repo(r'https://github.com/07th-mod/umineko-answer.git', 'adv_mode', web_folder, [
        (r'0.utf', r'Bern/script-adv-mode.zip'),
    ], as_zip=True)
else:
    error_exit()

print("Deployment was successful!")
