import subprocess
import re
import asyncio
import threading
from typing import Callable, List, Union


class Pipewire():
    def _run(self, command: List[str]) -> str:
        to_check = command if isinstance(command, str) else ' '.join(command)

        try:
            print(f'Running {command}')

            output = subprocess.run(['flatpak-spawn', '--host', *command], encoding='utf-8', shell=False, check=True, capture_output=True)
            output.check_returncode()
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            raise e

        return re.sub(r'\n$', '', output.stdout)

    def list_inputs() -> dict:
        output: list[str] = Pipewire()._run(['pw-link', '--input', '--verbose'])

        inputs = {}
        resource_id = None
        group_lineat = 0
        for line in output.split('\n'):
            if not re.match("^\s", line):
                resource_id = line.split(':')[0]

                if not resource_id in inputs:
                    inputs[resource_id] = {"id": line}

                group_lineat = 0
                continue

            group_lineat += 1
            line = line.strip()

            if group_lineat == 1: 
                inputs[resource_id]['alsa'] = line
            else:
                name, ch = line.split(':')
                if not 'channels' in inputs[resource_id]:
                    inputs[resource_id]['channels'] = []

                inputs[resource_id]['name'] = name
                inputs[resource_id]['channels'].append(ch)

        return inputs

# def threaded_sh(command: Union[str, List[str]], callback: Callable[[str], None]=None, return_stderr=False):
#     to_check = command if isinstance(command, str) else command[0]

#     def run_command(command: str, callback: Callable[[str], None]=None):
#         try:
#             output = sh(command, return_stderr)

#             if callback:
#                 callback(re.sub(r'\n$', '', output))

#         except subprocess.CalledProcessError as e:
#             log(e.stderr)
#             raise e

#     thread = threading.Thread(target=run_command, daemon=True, args=(command, callback, ))
#     thread.start()