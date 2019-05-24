#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
import pathlib
from typing import Tuple, List

idChannelBotSpam = 557048243696042055
discord_token_path = 'token.token'

# TODO: bot needs to login for each message sent - should only login once, then send messages on same connection.
def notify_by_discord(message_to_send):
    try:
        import discord

        client = discord.Client()

        @client.event
        async def on_ready():
            print('We have logged in as {0.user}'.format(client))

            channel = client.get_channel(idChannelBotSpam)
            if channel is not None:
                # send notification
                await channel.send(message_to_send)
            else:
                print("discord bot failed to get channel")

            # logout
            await client.logout()

        client.run(pathlib.Path(discord_token_path).read_text().strip())
    except Exception as e:
        print(f"Failed to send bot message: {e}")


def lockElseExit(fp):
    import fcntl
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("Succesfully obtained lock")
    except IOError:
        notify_failure_and_exit("Can't run script - another instance is running!")


def seven_zip(input_path, output_filename):
    subprocess.call(["7z", "a", output_filename, input_path])


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
                    seven_zip(original_source_path, absolute_source_path)

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


def notify_failure_and_exit(message):
    notify_by_discord(f"Task Failed!: {message}")
    print(message)
    exit(-1)


if len(sys.argv) < 2:
    notify_failure_and_exit("ERROR: need at least 1 argument: 'question' or 'answer' to determine which repo to update. Optional second argument is web root.")

# 'question' or 'answer'
which_game = sys.argv[1]
# the web root where the files will be output to
web_folder = r'/home/07th-mod/web' if len(sys.argv) < 3 else sys.argv[2]

print(f"Web folder: [{web_folder}] Game: [{which_game}]")

# Try to lock the lock file - exit on failure
if not sys.platform.startswith('win32'):
    pid_file = '/tmp/drojf_deploy_umineko_instance.lock'
    fp = open(pid_file, 'w')

    lockElseExit(fp)

if which_game == 'question':
    notify_by_discord("Umineko Question Deployment Started...")
    # Umineko Question 1080p Patch
    copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'master', web_folder, [
        (r'InDevelopment/ManualUpdates/0.utf', r'Beato/script-full.zip'),
    ], as_zip=True)

    # Umineko Question Voice Only Patch
    copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'voice_only', web_folder, [
        (r'InDevelopment/ManualUpdates/0.utf', r'Beato/script-voice-only.zip'),
    ], as_zip=True)
elif which_game == 'answer':
    notify_by_discord("Umineko Answer Deployment Started...")
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
    notify_failure_and_exit("Unknown game provided")

print("Deployment was successful!")
notify_by_discord("Deployment was successful!")