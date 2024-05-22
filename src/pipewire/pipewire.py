import json
import re
import signal
import subprocess
import re
import threading
import logging
from time import sleep, time_ns, time
from ..utils.async_utils import debounce
from typing import Optional, Callable, List, Union
from pprint import pprint

LOW_LATENCY_NODE_NAME = 'whisper-low-latency-node'

class PwLink():
    def __init__(self, resource_name: str):
        self.resource_name = resource_name
        self.alsa: str = ''
        self.name: str = ''
        self.channels: dict = {}


class PwActiveConnectionLink():
    def __init__(self, tag, channel, _id):
        self.connected_tag: str = tag
        self.channel: str = channel
        self._id: str = _id

class PwLowLatencyNode():
    def __init__(self, node_id, name):
        self.node_id = node_id
        self.name = name


class Pipewire():
    top_output: Optional[subprocess.Popen] = None

    def __init__(self):
        pass

    def _run(command: List[str], quiet=False) -> str:
        to_check = command if isinstance(command, str) else ' '.join(command)

        try:
            if not quiet:
                logging.info(f'Running {command}')

            output = subprocess.run([*command], encoding='utf-8', shell=False, check=True, capture_output=True)
            output.check_returncode()
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            raise e

        return re.sub(r'\n$', '', output.stdout)

    def _parse_pwlink_return(output: str) -> dict[str, PwLink]:
        elements = {}
        resource_tag = None
        line_id = None
        group_line_at = 0

        regex = re.compile(r'^(\s+\d+\s+)')
        for line in output.split('\n'):
            if not line.strip():
                break

            m = regex.match(line)
            if m:
                line_id = m.group().strip()
                resource_tag = (re.sub(f'^{m.group()}', '', line)).split(':', maxsplit=1)[0]

                if not resource_tag in elements:
                    elements[resource_tag] = PwLink(resource_tag)

                group_line_at = 0
                continue

            group_line_at += 1
            line = line.strip()

            if group_line_at == 1:
                elements[resource_tag].alsa = line
            else:
                line_data = line.split(':', maxsplit=1) 

                if len(line_data) < 2:
                    del elements[resource_tag]
                    continue

                name, ch = line_data

                if not ch:
                    del elements[resource_tag]
                    continue

                elements[resource_tag].name = name
                elements[resource_tag].channels[line_id] = ch

        return elements

    def _parse_pwlink_list_return(output: str) -> list[str, dict[str, PwActiveConnectionLink]]:
        elements = {}
        output_id = None

        regex = re.compile(r'^(\s+\d+\s+)')
        conn_regex = re.compile(r'.*(\|\-\>\s*)')
        for line in output.split('\n'):
            if not line.strip():
                break

            m = regex.match(line)
            if ('|->' not in line) and ('|<-' not in line):
                output_id = m.group().strip()
                resource_tag = (re.sub(f'^{m.group()}', '', line)).split(':', maxsplit=1)[0]

                if not output_id in elements:
                    elements[output_id] = {}

                continue

            elif ('|->' in line):
                connection_id = m.group().strip()
                connected_resource = conn_regex.sub('', line)

                _id, connected_item = connected_resource.split(' ', maxsplit=1)
                elements[output_id][connection_id] = PwActiveConnectionLink(connected_item.split(':')[0], connected_item.split(':')[1], _id)

        return elements

    def check_installed(quiet=False) -> bool:
        try:
            Pipewire._run(['which', 'pw-cli']).strip() and Pipewire._run(['which', 'pw-link']).strip() and Pipewire._run(['pw-cli', 'info', '0']).strip()
        except:
            return False

        return True

    def list_inputs(quiet=False) -> dict[str, PwLink]:
        output: list[str] = Pipewire._run(['pw-link', '--input', '--verbose', '--id'], quiet=quiet)
        inputs = Pipewire._parse_pwlink_return(output)

        return inputs

    def list_outputs(quiet=False) -> dict[str, PwLink]:
        output: list[str] = Pipewire._run(['pw-link', '--output', '--verbose', '--id'], quiet=quiet)
        items = Pipewire._parse_pwlink_return(output)

        return items

    def link(inp: str, out: str):
        Pipewire._run(['pw-link', '--linger', inp, out])

    def unlink(link_id):
        Pipewire._run(['pw-link', '--disconnect', link_id])

    def list_links(quiet=False) -> list[str, dict[str, PwActiveConnectionLink]]:
        return Pipewire._parse_pwlink_list_return(Pipewire._run(['pw-link', '--links', '--id'], quiet=quiet))

    def get_info_raw() -> str:
        return Pipewire._run(['pw-cli', 'info', '0'])

    def list_objects():
        output = {}
        try:
            output = json.loads(Pipewire._run(['pw-dump', '--no-colors']))
        except:
            pass

        return output

    def get_default_clock_info():
        objs = Pipewire.list_objects()

        props_0 = objs[0]['info']['props']

        return {
            "default.clock.max-quantum": props_0.get("default.clock.max-quantum", -1),
            "default.clock.min-quantum": props_0.get("default.clock.min-quantum", -1),
            "default.clock.quantum": props_0.get("default.clock.quantum", -1),
            "default.clock.quantum-floor": props_0.get("default.clock.quantum-floor", -1),
            "default.clock.quantum-limit": props_0.get("default.clock.quantum-limit", -1),
            "default.clock.rate": props_0.get("default.clock.rate", -1),
        }

    def create_low_latency_node() -> PwLowLatencyNode:
        objs = Pipewire.list_objects()

        whisper_node_name = 0
        whisper_objs_names = []


        for obj in objs:
            if obj['type'] == 'PipeWire:Interface:Node' and \
                'info' in obj and \
                'props' in obj['info'] and \
                'node.name' in obj['info']['props'] and \
                LOW_LATENCY_NODE_NAME in obj['info']['props']['node.name']:

                _, count = obj['info']['props']['node.name'].split(LOW_LATENCY_NODE_NAME, maxsplit=1)
                count: str = count.replace('-', '')
                count = int(count)

                whisper_objs_names.append(count)

        while (whisper_node_name in whisper_objs_names):
            whisper_node_name += 1

        clock_rate = Pipewire.get_default_clock_info()
        buffer_size = 64

        if clock_rate['default.clock.min-quantum'] > 0:
            while buffer_size < clock_rate['default.clock.min-quantum']:
                buffer_size = buffer_size * 2

        node_name = f"{LOW_LATENCY_NODE_NAME}-{(whisper_node_name)}"
        node_conf = f"factory.name=support.null-audio-sink node.name={node_name} media.class=Audio/Sink object.linger=true"
        node_conf += f" audio.position=[FL FR] node.latency={buffer_size}/{clock_rate['default.clock.rate']}"

        Pipewire._run(['pw-cli', 'create-node', 'adapter', ('{' +  node_conf + '}')])

        objs = Pipewire.list_objects()
        node = Pipewire.find_node_by_name(objs, node_name)
        return PwLowLatencyNode(node_id=node['id'], name=node_name)

    def find_node_by_name(objs: list, name: str) -> dict:
        for obj in objs:
            if obj['type'] == 'PipeWire:Interface:Node' and \
                'info' in obj and \
                'props' in obj['info'] and \
                'node.name' in obj['info']['props'] and \
                name == obj['info']['props']['node.name']:

                return obj
        
        return None

    def destroy_node(node: PwLowLatencyNode):
        Pipewire._run(['pw-cli', 'destroy', node.name])

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


        



        


