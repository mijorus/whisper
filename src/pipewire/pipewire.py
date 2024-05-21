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


class Pipewire():
    def __init__(self):
        self.monitor: Optional[subprocess.Popen] = None
        self.top_output: Optional[subprocess.Popen] = None
        self.monitor_callback: Optional[Callable] = None

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
        output = Pipewire._run(['pw-cli', 'info'])
        rows = output.split('\n')

        result = {}

        o_id = ''
        s_reg = re.compile(r'^"')
        e_reg = re.compile(r'"$')

        for r in rows:
            trimmed: str = r.strip()

            if r.startswith('\tid'):
                [o_id, o_type] = trimmed.split(',', maxsplit=1)
                o_id = o_id.replace('id ', '')
                _, o_type = o_type.strip().split(' ',  maxsplit=1)

                result[o_id] = {'type': o_type}
            elif o_id:
                key, val = trimmed.split('=')
                key = key.strip()
                val = val.strip().replace('"', '')
                result[o_id][key] = val

        return result

    def get_default_clock_info():
        info_raw = Pipewire.get_info_raw()

        info = {'rate': -1, 'quantum': -1, 'min-quantum': -1}
        for r in info_raw.split('\n'):
            if 'default.clock.rate' in r:
                _, val = r.split('=', maxsplit=1)
                val = val.replace('"', '')
                info['rate'] = int(val)

            if 'default.clock.quantum' in r:
                _, val = r.split('=', maxsplit=1)
                val = val.replace('"', '')
                info['quantum'] = int(val)

            if 'default.clock.min-quantum' in r:
                _, val = r.split('=', maxsplit=1)
                val = val.replace('"', '')
                info['min-quantum'] = int(val)

        return info

    def create_low_latency_node() -> str:
        objs = Pipewire.list_objects()

        whisper_objs_count = -1

        for o, obj in objs.items():
            if 'PipeWire:Interface:Node' in obj['type'] and \
                'name' in obj and \
                LOW_LATENCY_NODE_NAME in obj['name']:

                whisper_objs_count += 1

        clock_rate = Pipewire.get_default_clock_info()
        buffer_size = 64

        if clock_rate['min-quantum'] > 0:
            while buffer_size < clock_rate['min-quantum']:
                buffer_size = buffer_size * 2

        node_name = f"{LOW_LATENCY_NODE_NAME}-{(whisper_objs_count + 1)}"
        node_conf = f"factory.name=support.null-audio-sink node.name={node_name}"
        node_conf += f" media.class=Audio/Sink object.linger=true audio.position=[FL FR] node.latency={buffer_size}/{clock_rate['rate']}"

        Pipewire._run(['pw-cli', 'create-node', 'adapter', ('{' +  node_conf + '}', )])

        objs = Pipewire.list_objects()

        for o, obj in objs.items():
            if 'PipeWire:Interface:Node' in obj['type'] and \
                'name' in obj and \
                node_name == obj['name']:

                return o

    def top_output(self, callback: Callable[[str], None] = None):
        # output = None

        # def run_command(callback: Callable[[str], None] = None):
        #     try:
        #         logging.info('Pipewire WATCH: starting top')
        #         self.top_output = subprocess.Popen(['pw-top'], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        #         last_call = time()
        #         while self.top_output:
        #             output  = self.top_output.communicate()[0]

        #             if (time() - last_call) > 3:
        #                 print(output)
        #                 logging.info('Pipewire TOP: executing callback ' + str(time_ns() - last_call))

        #                 last_call = time()

        #                 if callback:
        #                     callback(output)

        #     except subprocess.CalledProcessError as e:
        #         print(e.stderr)
        #         logging.error(msg=e.stderr)
        #         raise e

        # thread = threading.Thread(target=run_command, daemon=False, args=(callback,))
        # thread.start()
        # o =  self.top_output = subprocess.run([" pw-cli create-node adapter '{ factory.name=support.null-audio-sink node.name=whisper-low-latency-node-test media.class=Audio/Sink object.linger=true audio.position=[FL FR] monitor.channel-volumes=true monitor.passthrough=true node.latency=128/48000}'"], shell=True, check=True, encoding='utf-8')
        # print(o.stdout, o.stderr)
        Pipewire.list_objects()

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


        



        


