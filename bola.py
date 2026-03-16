"""
Take incoming HTTP requests having specifieds headers/cookies and replay them
without these headers/cookies. The script also compare the reponse to find
possible diferences indicating the lack of proper authentication.
"""

import logging
import os
import json

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.net.http.http1 import assemble

# Duplicator for BOLA detection
# Duplicates the requests that has in its query or body data any instance
# of originalInput (loaded from options) and change it for replayInput
# (also loaded from options)
class Duplicator:
    def __init__(self):
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

    def request(self, flow: http.HTTPFlow):
        if flow.is_replay == "request":
            # The request shouldn't be send before user approval (handled by other script)
            flow.kill()

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
            self.not_replayed[flow.id] = None
            return
        
        # Avoid replaying requests but GET or POST
        if not (flow.request.method == "GET" or flow.request.method == "POST"):
            # Save ids of not replayed request to not write (save in disk) theis responses
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
            self.not_replayed[flow.id] = None
            return

        # If the code reachs here, the request should be replayed (after user approval)
        replayed_flow = flow.copy()

        # Create directory to save flow requests, responses and metadata
        flow_name = "flow-" + str(self.directory_count)
        self.directory_count += 1
        self.flows_names[flow.id] = flow_name
        self.flows_names[replayed_flow.id] = flow_name
        dir_name = "flows/" + self.flows_names[flow.id] + "/"
        os.makedirs(dir_name, exist_ok=True)
    
        # Change input data (in the path or in the body)
        replayed_flow.request.path = new_path
        replayed_flow.request.set_content(new_content.encode())

        # Save raw request for both flows
        self.save_raw_request(flow, "original_request.raw")
        self.save_raw_request(replayed_flow, "replay_request.raw")

        # Only interactive tools have a view. If we have one, add a duplicate entry
        # for our flow
        if "view" in ctx.master.addons:
            ctx.master.commands.call("view.flows.duplicate", [replayed_flow])

        ctx.master.commands.call("replay.client", [replayed_flow])       
    
    def response(self, flow: http.HTTPFlow):
        if flow.id in self.not_replayed:
            del self.not_replayed[flow.id]
            return
        
        # Save raw response for original flow
        self.save_raw_response(flow, "original_response.raw")

        # Metadata content
        # Last to be saved. After this file is write in disk, all the other
        # parts can work with no file lock or any other trouble
        metadata = {
            "url": flow.request.url,
            "method": flow.request.method,
            "status": "not replayed",
            "same-response": "undefined",
        }
        dir_name = "flows/" + self.flows_names[flow.id] + "/"
        with open(dir_name + "metadata.json", "w") as f:
            json.dump(metadata, f)
    
    def save_raw_request(self, flow: http.HTTPFlow, file_name: str):
        dir_name = "flows/" + self.flows_names[flow.id] + "/"
        with open(dir_name + file_name, "wb") as f:
            raw_request = assemble.assemble_request(flow.request)
            f.write(raw_request)
    
    def save_raw_response(self, flow: http.HTTPFlow, file_name: str):
        dir_name = "flows/" + self.flows_names[flow.id] + "/"
        with open(dir_name + file_name, "wb") as f:
            raw_response_headers = assemble.assemble_response_head(flow.response)
            raw_response = raw_response_headers + flow.response.content
            f.write(raw_response)

# Create log directories if they not exist
os.makedirs('flows/', exist_ok=True)
addons = [Duplicator()]