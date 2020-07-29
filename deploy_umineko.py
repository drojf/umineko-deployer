#!/usr/bin/env python3
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import pathlib
import datetime
import traceback
from typing import Tuple, List

idChannelUminekoDev = 384427969520599043
discord_token_path = 'token.token'

def lockElseExit(fp):
    import fcntl
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("Succesfully obtained lock")
    except IOError:
        raise Exception("Can't run script - another instance is running!")

def seven_zip(input_path, output_filename):
    subprocess.call(["7z", "a", output_filename, input_path])


def copy_files_from_repo(repo_url: str, branch: str, web_root: str, repo_target_path_pairs: List[Tuple[str, str, str]], as_zip):
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

            for file_in_repo_path, new_file_name, rel_target_path in repo_target_path_pairs:
                # checkout all the repo paths
                subprocess.call(['git', 'checkout', 'HEAD', file_in_repo_path], cwd=repo_clone_path)

                # calculate the correct repo path dep on if 'as_zip' is enabled
                original_source_path = os.path.join(repo_clone_path, file_in_repo_path)

                # rename the file
                path_after_renaming = os.path.join(os.path.dirname(original_source_path), new_file_name)
                print(f'Renaming path {original_source_path} to {path_after_renaming}')
                shutil.move(original_source_path, path_after_renaming)

                # calculate temporary zip file path (or just file path if not zipping)
                absolute_source_path = path_after_renaming + '.zip' if as_zip else ''

                #  zip each path if necessary
                if as_zip:
                    print(f'Zipping {path_after_renaming} -> {absolute_source_path}')
                    seven_zip(path_after_renaming, absolute_source_path)

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

async def do_deployment(channel):
    if len(sys.argv) < 2:
        await channel.send(f"Invalid arguments provided!")
        raise Exception("ERROR: need at least 1 argument: 'question' or 'answer' to determine which repo to update. Optional second argument is web root.")

    await channel.send(f"Build started on [{datetime.datetime.now()}]")
    await channel.send(f"Waiting 30 seconds for other push events...")
    await asyncio.sleep(30)

    # 'question' or 'answer'
    which_game = sys.argv[1]
    # the web root where the files will be output to
    web_folder = r'/home/07th-mod/web' if len(sys.argv) < 3 else sys.argv[2]

    print(f"Web folder: [{web_folder}] Game: [{which_game}]")

    if which_game == 'question':
        # Try to lock the lock file - exit on failure
        if not sys.platform.startswith('win32'):
            pid_file = '/tmp/drojf_deploy_umineko_question_instance.lock'
            fp = open(pid_file, 'w')

            lockElseExit(fp)

        await channel.send("Umineko Question Deployment Started...")
        # Umineko Question 1080p Patch
        copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'master', web_folder, [
            (r'InDevelopment/ManualUpdates/0.utf', '0.u', r'Beato/script-full.zip'),
        ], as_zip=True)

        # Umineko Question Voice Only Patch
        copy_files_from_repo(r'https://github.com/07th-mod/umineko-question.git', 'voice_only', web_folder, [
            (r'InDevelopment/ManualUpdates/0.utf', '0.u', r'Beato/script-voice-only.zip'),
        ], as_zip=True)
    elif which_game == 'answer':
        # Try to lock the lock file - exit on failure
        if not sys.platform.startswith('win32'):
            pid_file = '/tmp/drojf_deploy_umineko_answer_instance.lock'
            fp = open(pid_file, 'w')

            lockElseExit(fp)

        await channel.send("Umineko Answer Deployment Started...")
        # Umineko Answer Full and Voice Only Patch
        copy_files_from_repo(r'https://github.com/07th-mod/umineko-answer.git', 'master', web_folder, [
            (r'0.utf', '0.u', r'Bern/script-full.zip'),
            (r'voices-only/0.utf', '0.u', r'Bern/script-voice-only.zip'),
        ], as_zip=True)

        # Umineko Answer ADV Mode Patch
        copy_files_from_repo(r'https://github.com/07th-mod/umineko-answer.git', 'adv_mode', web_folder, [
            (r'0.utf', '0.u', r'Bern/script-adv-mode.zip'),
        ], as_zip=True)
    else:
        await channel.send(f"Unknown game provided")
        raise Exception("Unknown game provided")

    print("Deployment was successful!")
    await channel.send("Deployment was successful!")

class DummyChannel:
    async def send(self, message):
        print(message)

print("Logging into discord...")

try:
    import discord
    client = discord.Client()

    @client.event
    async def on_ready():
        try:
            print('We have logged in as {0.user}'.format(client))

            channel = client.get_channel(idChannelUminekoDev)
            if channel is not None:
                await do_deployment(channel)
            else:
                print("discord bot failed to get channel")
        except Exception as e:
            print("Failed due to exception", e)
            raise e
        finally:
            await client.logout()


    client.run(pathlib.Path(discord_token_path).read_text().strip())
except Exception as e:
    print("Discord init failed due to: ", e)
    traceback.print_exc()
    # TODO: this will only run if there's an error in the discord.Client() call or if discord is missing.
    # TODO: should probably use message passing or similar to notify discord client of messages rather than this way.
    print(f"Failed - trying again without discord")
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(do_deployment(DummyChannel()))

