import asyncio
import logging
import os
import sys

from autogen_core.application import SingleThreadedAgentRuntime, WorkerAgentRuntime
from autogen_core.application.protos.agent_events_pb2 import Input

# Add the local package directory to sys.path
# sys.path.append(os.path.abspath('../../../../python/packages/autogen-core'))
from autogen_core.components import DefaultTopicId
from dotenv import load_dotenv
from messages import ArticleCreated, AuditorAlert, AuditText, GraphicDesignCreated
from user_input import UserProxy

agnext_logger = logging.getLogger("autogen_core")


async def main() -> None:
    load_dotenv()
    agentHost = os.getenv("AGENT_HOST")
    agnext_logger.info("0")
    agnext_logger.info(agentHost)
    runtime = WorkerAgentRuntime(host_address=agentHost)
    # runtime = SingleThreadedAgentRuntime()

    agnext_logger.info("1")
    runtime.start()

    agnext_logger.info("2")

    await UserProxy.register(runtime, "UserProxy", lambda: UserProxy())
    agnext_logger.info("3")

    await runtime.publish_message(message=Input(message=""), topic_id="HelloAgents")
    await runtime.stop_when_signal()
    # await runtime.stop_when_idle()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    agnext_logger.setLevel(logging.DEBUG)
    agnext_logger.log(logging.DEBUG, "Starting worker")
    asyncio.run(main())
