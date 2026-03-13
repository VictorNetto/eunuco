"""
Take incoming HTTP requests having specifieds headers/cookies and replay them
without these headers/cookies. The script also compare the reponse to find
possible diferences indicating the lack of proper authentication.
"""

import logging
import os
import json
import time

from mitmproxy.script import concurrent

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.net.http.http1 import assemble

class FlowStorage:
    def __init__(self):
        self.raw_request: dict[str, bytes] = {}
        self.raw_response: dict[str, bytes] = {}
        self.hash_response_body: dict[str, int] = {}
        self.status_code: dict[str, int] = {}

    def put_raw_request(self, flow_id: str, raw_request: bytes):
        self.raw_request[flow_id] = raw_request

    def put_raw_response(self, flow_id: str, raw_response: bytes):
        self.raw_response[flow_id] = raw_response
    
    def put_response_body(self, flow_id: str, response_body: bytes):
        self.hash_response_body[flow_id] = hash(response_body)
    
    def put_status_code(self, flow_id: str, status_code: int):
        self.status_code[flow_id] = status_code
    
    def pop(self, flow_id: str):
        data = self.raw_request[flow_id] + self.raw_response[flow_id]

        del self.raw_request[flow_id]
        del self.raw_response[flow_id]
        del self.hash_response_body[flow_id]
        del self.status_code[flow_id]

        return data
    
    def equal(self, flow_id1: str, flow_id2: str):
        hash_response_body1 = self.hash_response_body.get(flow_id1, '')
        hash_response_body2 = self.hash_response_body.get(flow_id2, '')
        status_code1 = self.status_code.get(flow_id1, '')
        status_code2 = self.status_code.get(flow_id2, '')

        if hash_response_body1 == '' or hash_response_body2 == '' or \
            status_code1 == '' or status_code2 == '':
            return None

        same_response_body = hash_response_body1 == hash_response_body2
        same_status_code = status_code1 == status_code2

        return same_response_body and same_status_code

# Track request/response pairs (original and replayed one), comparing them as soon as possible
# Request/reponse pairs are tracked using its flow.id in add_pair method
# Comparison between them are made in add_content method using the auxiliar FlowStorage instance
class Comparator:
    undefined = -1
    equal = 0
    different = 1

    def __init__(self, flow_storage: FlowStorage):
        self.pairs: dict[str, str] = {}
        self.flow_storage = flow_storage
        # self.content = {}
    
    def add_pair(self, flow_id1: str, flow_id2: str):
        self.pairs[flow_id1] = flow_id2
        self.pairs[flow_id2] = flow_id1
    
    def add_content(self, flow_id: str, response_body: bytes, status_code: int):
        self.flow_storage.put_response_body(flow_id, response_body)
        self.flow_storage.put_status_code(flow_id, status_code)

        other_flow_id = self.pairs.get(flow_id, '')

        result = (Comparator.undefined, '', '')

        flows_are_equal = self.flow_storage.equal(flow_id, other_flow_id)
        if flows_are_equal is not None:
            if flows_are_equal:
                logging.info(f"[*] Replayed request with equal responses: {other_flow_id} and {flow_id}")
                result = (Comparator.equal, other_flow_id, flow_id)
            else:
                logging.warning(f"[-] Replayed request with different responses: {other_flow_id} and {flow_id}")
                result = (Comparator.different, other_flow_id, flow_id)
        
        return result

class Duplicator:
    def __init__(self):
        self.flow_storage = FlowStorage()
        self.comparator = Comparator(self.flow_storage)
        self.not_replayed: dict[str, None] = {}
        
        self.directory_count = 0
        self.flows_names: dict[str, str] = {}

        # Load domains to repeat from a config file (domains.yaml)
        self.domains = []
        self.load_options()

    def load_options(self):
        try:
            with open('domains.yaml', 'r') as file:
                logging.info("[*] Reading domains.yaml file")
                lines = file.readlines()

                for line in lines:
                    if line.startswith("#"):
                        continue
                    self.domains.append(line.strip())

                logging.info(f"[*] Loaded Domains: {self.domains}")
        except FileNotFoundError:
            logging.error("[!] domains.yaml file not found")

    def load(self, loader):
        loader.add_option(
            name="originalInput",
            typespec=str,
            default="",
            help="Original Input",
        )

        loader.add_option(
            name="replayInput",
            typespec=str,
            default="",
            help="Replay Input",
        )

    @concurrent
    def request(self, flow: http.HTTPFlow):
        logging.warning(f"request() of {flow.id}, replayed: {flow.is_replay}")

        # Handle replayed flows as soon as possible and return to avoid infinite loop
        if flow.is_replay == "request":
            self.wait_user_approval(flow)

            # Avoid an infinite loop by not replaying already replayed requests
            return

        # Only domains in domains.yaml file will be replayed
        replay_request = False
        for domain in self.domains:
            if domain in flow.request.host:
                replay_request = True
                break
        if not replay_request:
            # Save ids of not replayed request to not write (save in disk) theis responses
            # in the self.response method
            self.not_replayed[flow.id] = None
            return
        
        # Avoid replaying requests that but GET or POST
        if not (flow.request.method == "GET" or flow.request.method == "POST"):
            # Save ids of not replayed request to not write (save in disk) theis responses
            # in the self.response method
            self.not_replayed[flow.id] = None
            return
        
        # Find any instance of originalInput and change it to replayInput in the parameters
        path = flow.request.path
        new_path = flow.request.path.replace(ctx.options.originalInput, ctx.options.replayInput)

        # Find any instance of originalInput and change it to replayInput in the request body
        content = flow.request.content.decode()
        new_content = content.replace(ctx.options.originalInput, ctx.options.replayInput)

        # Avoid replaying requests with the same data
        if path == new_path and content == new_content:
            # Save ids of not replayed request to not write (save in disk) theis responses
            # in the self.response method
            self.not_replayed[flow.id] = None
            return

        # If the code reachs here, the request should be replayed (after user approval)
        replayed_flow = flow.copy()
        self.comparator.add_pair(flow.id, replayed_flow.id)

        # Create directory to save flow requests, responses and metadata
        flow_name = "flow-" + str(self.directory_count)
        self.directory_count += 1
        self.flows_names[flow.id] = flow_name
        self.flows_names[replayed_flow.id] = flow_name
        # self.flows_names[replayed_flow.id] = directory
        dir_name = "flows/" + self.flows_names[flow.id] + "/"
        os.makedirs(dir_name, exist_ok=True)

    
        # Change input data (in the path or in the body)
        replayed_flow.request.path = new_path
        replayed_flow.request.set_content(new_content.encode())

        # Save raw request for both flows
        # Original
        self.flow_storage.put_raw_request(flow.id, assemble.assemble_request(flow.request))
        self.save_raw_request(dir_name, "original_request.raw", flow.id)
        # Replayed
        self.flow_storage.put_raw_request(replayed_flow.id, assemble.assemble_request(replayed_flow.request))
        self.save_raw_request(dir_name, "replayed_request.raw", replayed_flow.id)

        # Metadata content
        metadata = {
            "url": flow.request.url,
            "method": flow.request.method,
            "status": "status-a",
            "same-response": "undefined",
            "approved": "hold",
        }

        with open(dir_name + "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Only interactive tools have a view. If we have one, add a duplicate entry
        # for our flow
        if "view" in ctx.master.addons:
            ctx.master.commands.call("view.flows.duplicate", [replayed_flow])

        ctx.master.commands.call("replay.client", [replayed_flow])

    # def replay_flow(self, flow: http.HTTPFlow):
    #     dir_name = "flows/" + self.flows_names[flow.id] + "/"
    #     flow.intercept()

    #     approved = self.wait_user_approval(dir_name, flow)
    #     logging.warning(approved)
    #     if approved:
    #         logging.warning("Request replayed")
    #     else:
    #         logging.warning("Request not replayed")

    def wait_user_approval(self, flow: http.HTTPFlow):
        dir_name = "flows/" + self.flows_names[flow.id] + "/"

        if flow.intercepted == False:
            logging.warning(f"Intercepting flow {flow.id}")
            flow.intercept()
            
        with open(dir_name + "metadata.json", "r") as f:
            metadata = json.load(f)
            approved = metadata["approved"]

            if approved == "hold":
                time.sleep(5)
                self.wait_user_approval(flow)
            elif approved == "approved":
                logging.warning(f"Let it go {flow.id}")
                flow.resume()
                return
            elif approved == "not approved":
                logging.warning(f"Dont let it go")
                logging.warning(f"{flow.killable} {flow.id}")
                flow.kill()
                return        
        
        # logging.warning(approved)
        # if approved == "approved":
        #     logging.info(metadata)
        #     return True
        # elif approved == "not approved":
        #     return False
        # else:
        #     time.sleep(5)
        #     self.wait_user_approval(dir_name, flow)
    
    def response(self, flow: http.HTTPFlow):
        if flow.id in self.not_replayed:
            del self.not_replayed[flow.id]
            return

        if flow.response and flow.response.content:
            raw_response_headers = assemble.assemble_response_head(flow.response)
            raw_response = raw_response_headers + flow.response.content
            self.flow_storage.put_raw_response(flow.id, raw_response)

            result, flow_id1, flow_id2 = self.comparator.add_content(flow.id, flow.response.content, flow.response.status_code)

            if result == Comparator.undefined:
                return
            
            # Directory name to save flows resquests, responses and metadata
            dir_name = 'flows/' + self.flows_names[flow_id1] + "/"
            del self.flows_names[flow_id1]
            del self.flows_names[flow_id2]

            # Metadata content
            metadata = {
                "url": flow.request.url,
                "method": flow.request.method,
                "status": "status-a",
            }
            if result == Comparator.equal:
                metadata["response"] = "equal"
            elif result == Comparator.different:
                metadata["response"] = "different"

            # os.makedirs(dir_name, exist_ok=True)
            with open(dir_name + "metadata.json", "w") as f:
                json.dump(metadata, f)

            original_flow = ""
            replay_flow = ""
            if flow.is_replay:
                original_flow = flow_id1
                replay_flow = flow_id2
            else:
                original_flow = flow_id2
                replay_flow = flow_id1
            
            # Original request and response
            # with open(dir_name + "original_request.raw", "wb") as f:
            #     f.write(self.flow_storage.raw_request[original_flow])
            #     del self.flow_storage.raw_request[original_flow]
            
            with open(dir_name + "original_response.raw", "wb") as f:
                f.write(self.flow_storage.raw_response[original_flow])
                del self.flow_storage.raw_response[original_flow]

            # Replay request and response
            # with open(dir_name + "replay_request.raw", "wb") as f:
            #     f.write(self.flow_storage.raw_request[replay_flow])
            #     del self.flow_storage.raw_request[replay_flow]
            
            with open(dir_name + "replay_response.raw", "wb") as f:
                f.write(self.flow_storage.raw_response[replay_flow])
                del self.flow_storage.raw_response[replay_flow]
    
    def save_raw_request(self, dir_name: str, file: str, original_flow: str):
        with open(dir_name + file, "wb") as f:
            f.write(self.flow_storage.raw_request[original_flow])

    def safe_raw_requests(self, dir_name, original_flow, replay_flow):
        with open(dir_name + "original_request.raw", "wb") as f:
            f.write(self.flow_storage.raw_request[original_flow])
            del self.flow_storage.raw_request[original_flow]

        with open(dir_name + "replay_request.raw", "wb") as f:
            f.write(self.flow_storage.raw_request[replay_flow])
            del self.flow_storage.raw_request[replay_flow]

# Create log directories if they not exist
os.makedirs('flows/', exist_ok=True)

addons = [Duplicator()]