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
        
    def _parse_pwlink_return(output: str) -> dict:
        elements = {}
        resource_id = None
        group_lineat = 0
        
        regex = re.compile(r'^(\s+\d+\s+)')
        for line in output.split('\n'):
            m = regex.match(line)
            if m:
                line_id = m.group().strip()
                resource_id = (re.sub(f'^{m.group()}', '', line)).split(':', maxsplit=1)[0]

                if not resource_id in elements:
                    elements[resource_id] = {"id": line_id}

                group_lineat = 0
                continue

            group_lineat += 1
            line = line.strip()

            if group_lineat == 1: 
                elements[resource_id]['alsa'] = line
            else:
                name, ch = line.split(':')
                if not 'channels' in elements[resource_id]:
                    elements[resource_id]['channels'] = []

                elements[resource_id]['name'] = name
                elements[resource_id]['channels'].append(ch)
                
        return elements

    def list_inputs() -> dict:
        output: list[str] = Pipewire()._run(['pw-link', '--input', '--verbose', '--id'])
        inputs = Pipewire._parse_pwlink_return(output)

        return inputs

    def list_outputs() -> dict:
        output: list[str] = Pipewire()._run(['pw-link', '--output', '--verbose', '--id'])
        items = Pipewire._parse_pwlink_return(output)

        return items

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