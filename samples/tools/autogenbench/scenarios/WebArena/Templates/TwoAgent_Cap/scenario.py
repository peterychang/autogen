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
from autogencap.DebugLog import Info

import time


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

ensemble = ComponentEnsemble()
pair = CAPPair(ensemble, user_proxy, web_surfer)


# Login to the necessary websites
for site in TASK["sites"]:
    if site in ["reddit", "gitlab", "shopping", "shopping_admin"]:
        if logging_enabled():
            log_event(os.path.basename(__file__), name="start_" + site + "_task")
        try:
            pair.initiate_chat(
                message=LOGIN_PROMPTS[site],
                #clear_history=True,
            )
                # Wait for the pair to finish
            try:
                while pair.running():
                    # Hang out for a while and print out
                    # status every now and then
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("Interrupted by user, shutting down.")
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


##################
testbed_utils.finalize(agents=[web_surfer, user_proxy])
