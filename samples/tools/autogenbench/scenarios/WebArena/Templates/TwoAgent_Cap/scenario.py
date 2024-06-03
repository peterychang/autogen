import os
import json
import testbed_utils
import autogen
import evaluation_harness
import re
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.agentchat.contrib.mmagent import MultimodalAgent
from autogen.runtime_logging import logging_enabled, log_event

from autogencap.ag_adapter.CAPPair import CAPPair
from autogencap.ComponentEnsemble import ComponentEnsemble
from autogencap.ag_adapter.CAP2AG import CAP2AG
from autogencap.DebugLog import INFO
import autogencap.Config as Config

import time
Config.LOG_LEVEL = INFO

from evaluation_harness.env_config import (
    ACCOUNTS,
    GITLAB,
    MAP,
    REDDIT,
    SHOPPING,
    SHOPPING_ADMIN,
    WIKIPEDIA,
    HOMEPAGE,
    LOGIN_PROMPTS,
    SITE_DESCRIPTIONS,
    url_to_sitename,
)

testbed_utils.init()
##############################
class CAPWrapper:
    def __init__(self, network, first, second):
        self._network = network
        self._first_ag_agent = first
        self._second_ag_agent = second

        # TODO: Make the start_thread params configurable
        self._first_adptr = CAP2AG(
            ag_agent=self._first_ag_agent,
            the_other_name=self._second_ag_agent.name,
            init_chat=True,
            self_recursive=True,
            start_thread = False,
        )
        self._second_adptr = CAP2AG(
            ag_agent=self._second_ag_agent,
            the_other_name=self._first_ag_agent.name,
            init_chat=False,
            self_recursive=True,
            start_thread = False,
        )

    def initiate_chat_sync(self, agent, message: str):
        if not self.running():
            self._network.register(self._first_adptr)
            self._network.register(self._second_adptr)
            self._network.connect()
        
        # a little hacky hacky to get this to work
        agent_adptr = None
        other_adptr = None
        if agent == self._first_ag_agent:
            agent_adptr = self._first_adptr
            other_adptr = self._second_adptr
        else:
            agent_adptr = self._second_adptr
            other_adptr = self._first_adptr


        # Send a message to the user_proxy
        agent_connection = self._network.find_by_name(agent.name)
        agent_connection.send_txt_msg(message)

        # TODO: Make this aware of threaded agents
        while self.running():
            message1 = agent_adptr.get_message()
            agent_adptr.dispatch_message(message1)

            message2 = other_adptr.get_message()
            other_adptr.dispatch_message(message2)

        # TODO: It would be better to not fully disconnect here. Just wait for 
        #       additional messages OR a disconnect so that we don't have to keep
        #       creating wrappers for this workflow
        self._network.disconnect()

    # Do a single back-and-forth conversation
    def send_sync(self, agent, message: str):
        if not self.running():
            self._network.register(self._first_adptr)
            self._network.register(self._second_adptr)
            self._network.connect()
        
        # a little hacky hacky to get this to work
        agent_adptr = None
        other_adptr = None
        if agent == self._first_ag_agent:
            agent_adptr = self._first_adptr
            other_adptr = self._second_adptr
        else:
            agent_adptr = self._second_adptr
            other_adptr = self._first_adptr

        # Send a message to the user_proxy
        agent_connection = self._network.find_by_name(agent.name)
        agent_connection.send_txt_msg(message)

        message1 = agent_adptr.get_message()
        agent_adptr.dispatch_message(message1)

        message2 = other_adptr.get_message()
        other_adptr.dispatch_message(message2)

        self._network.disconnect()

    def running(self):
        return self._first_adptr.run and self._second_adptr.run

REPLACEMENTS = {
    "__REDDIT__": REDDIT,
    "__SHOPPING__": SHOPPING,
    "__SHOPPING_ADMIN__": SHOPPING_ADMIN,
    "__GITLAB__": GITLAB,
    "__WIKIPEDIA__": WIKIPEDIA,
    "__MAP__": MAP,
    "__HOMEPAGE__": HOMEPAGE,
}

# Expand the prompt and the full task
task_prompt = ""
TASK = None
with open("task_prompt.json.txt", "rt") as fh:
    task_prompt = fh.read()
with open("task_prompt.json", "wt") as fh:
    for k in REPLACEMENTS:
        task_prompt = task_prompt.replace(k, REPLACEMENTS[k])
    fh.write(task_prompt)
    TASK = json.loads(task_prompt)

full_task = ""
with open("full_task.json.txt", "rt") as fh:
    full_task = fh.read()
with open("full_task.json", "wt") as fh:
    for k in REPLACEMENTS:
        full_task = full_task.replace(k, REPLACEMENTS[k])
    fh.write(full_task)

# Load the LLM config list
config_list = autogen.config_list_from_json("OAI_CONFIG_LIST")
llm_config = testbed_utils.default_llm_config(config_list, timeout=300)

if logging_enabled():
    log_event(os.path.basename(__file__), name="loaded_config_lists")

web_surfer = MultimodalWebSurferAgent(
    "web_surfer",
    llm_config=llm_config,
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0 or str(x).find("FINAL ANSWER") >= 0,
    human_input_mode="NEVER",
    headless=True,
    browser_channel="chromium",
    browser_data_dir=None,
    start_page=HOMEPAGE,
    debug_dir=os.getenv("WEB_SURFER_DEBUG_DIR", None),
)

user_proxy = MultimodalAgent(
    "user_proxy",
    system_message="""You are a general-purpose AI assistant and can handle many questions -- but you don't have access to a web browser. However, the user you are talking to does have a browser, and you can see the screen. Provide short direct instructions to them to take you where you need to go to answer the initial question posed to you.

Once the user has taken the final necessary action to complete the task, and you have fully addressed the initial request, reply with the word TERMINATE.""",
    llm_config=llm_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda x: False,
    max_consecutive_auto_reply=20,
)

#cap_web_surfer = CAP2AG(
#    ag_agent=web_surfer,
#    the_other_name=user_proxy.name,
#    init_chat=True,
#    self_recursive=True,
#    start_thread = False,
#)
#cap_user_proxy = CAP2AG(
#    ag_agent=user_proxy,
#    the_other_name=web_surfer.name,
#    init_chat=True,
#    self_recursive=True,
#    start_thread = True,
#)

ensemble = ComponentEnsemble()
#pair = CAPPair(ensemble, user_proxy, web_surfer)
#ensemble.register(cap_web_surfer)
#ensemble.register(cap_user_proxy)
#ensemble.connect()
#web_surfer_link = ensemble.find_by_name(web_surfer.name)
#user_proxy_link = ensemble.find_by_name(user_proxy.name)

#cap = CAPWrapper(ensemble, user_proxy, web_surfer)
# Login to the necessary websites
for site in TASK["sites"]:
    if site in ["reddit", "gitlab", "shopping", "shopping_admin"]:
        if logging_enabled():
            log_event(os.path.basename(__file__), name="start_" + site + "_task")
        try:
#            user_proxy_link.send_txt_msg(LOGIN_PROMPTS[site])
#
#            while cap_web_surfer.run and cap_user_proxy.run:
#                #message1 = cap_user_proxy.get_message()
#                #cap_user_proxy.dispatch_message(message1)
#
#                message2 = cap_web_surfer.get_message()
#                cap_web_surfer.dispatch_message(message2)
            cap = CAPWrapper(ensemble, user_proxy, web_surfer)
            cap.initiate_chat_sync(user_proxy, LOGIN_PROMPTS[site])
            time.sleep(0.5)
                    
        except Exception as e:
            import traceback

            if logging_enabled():
                exc_type = type(e).__name__
                exc_message = str(e)
                exc_traceback = traceback.format_exc().splitlines()
                log_event(
                    os.path.basename(__file__),
                    name="exception_thrown",
                    exc_type=exc_type,
                    exc_message=exc_message,
                    exc_traceback=exc_traceback,
                )

            raise e
        user_proxy.reset()
        web_surfer.reset()

Config.LOG_LEVEL = 0
# Navigate to the starting url
if logging_enabled():
    log_event(os.path.basename(__file__), name="navigate_start_url")
start_url = TASK["start_url"]
if start_url == REDDIT:
    start_url = start_url + "/forums"

cap = CAPWrapper(ensemble, user_proxy, web_surfer)
cap.send_sync(user_proxy, f"Type '{start_url}' into the address bar.")
user_proxy.reset()
web_surfer.reset()

Config.LOG_LEVEL = 1

print("MAIN TASK STARTING !#!#")

# Provide some background about the pages
site_description_prompt = ""
sitename = url_to_sitename(start_url)
if sitename:
    site_description_prompt = ", " + SITE_DESCRIPTIONS[sitename]

if logging_enabled():
    log_event(os.path.basename(__file__), name="main_task_initiate_chat")

try:
    cap = CAPWrapper(ensemble, user_proxy, web_surfer)
    cap.initiate_chat_sync(
        web_surfer,
        message=f"""
We are visiting the website {start_url}{site_description_prompt}. On this website, please complete the following task:

{TASK['intent']}
""".strip(),
    )
except Exception as e:
    import traceback

    if logging_enabled():
        exc_type = type(e).__name__
        exc_message = str(e)
        exc_traceback = traceback.format_exc().splitlines()
        log_event(
            os.path.basename(__file__),
            name="exception_thrown",
            exc_type=exc_type,
            exc_message=exc_message,
            exc_traceback=exc_traceback,
        )

    raise e


##################
testbed_utils.finalize(agents=[web_surfer, user_proxy])
