from pathlib import Path

import pytest

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.conversation.types import TextContent
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "cyanheads_git-mcp-server"


class TestGitAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_git_agent"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation historymust indicate:
        1. that the repository was successfully cloned
        2. that it has been cloned to a path that is appropriate for the task
        3. that the agent used the correct sequence of git commands

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_ask_git_for_clone(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        instructions = "Do a depth 1 clone of the repository https://github.com/modelcontextprotocol/servers"

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Check if there is now a servers directory
        assert (temp_working_dir / "servers").exists()

        # Ensure it has a README.md file
        assert (temp_working_dir / "servers" / "README.md").exists()

        assert "success" in text_result.lower()
        assert "servers" in text_result.lower()

        assert len(agent_tool_calls) < 4
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        # Agent may also call set_working_dir to set the working directory
        assert "git_clone" in tool_call_names
        assert "report_success" in tool_call_names

        clone_tool_call = next(tool_call for tool_call in agent_tool_calls if tool_call.name == "git_clone")
        assert clone_tool_call.arguments == {
            "repositoryUrl": "https://github.com/modelcontextprotocol/servers",
            "targetPath": "servers",
            "depth": 1,
        }
        assert agent_tool_calls[1].name == "report_success"

        return agent, instructions, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that a new branch was successfully created
        2. that the branch was created from the correct base branch
        3. that the working directory was switched to the new branch
        4. that the branch name follows good naming conventions (feature/, bugfix/, etc.)
        5. that the agent used the correct sequence of git commands

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_branch_management(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        instructions = """
        1. Clone the repository https://github.com/modelcontextprotocol/servers
        2. Create a new feature branch for issue #1234 from main
        3. Switch to the new branch
        """

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify the branch was created
        assert (temp_working_dir / "servers").exists()
        assert "feature/issue-1234" in text_result.lower()

        # Verify tool calls
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert len(agent_tool_calls) >= 3
        assert "git_clone" in tool_call_names
        assert "git_branch" in tool_call_names
        assert "git_checkout" in tool_call_names

        clone_tool_call = next(tool_call for tool_call in agent_tool_calls if tool_call.name == "git_clone")
        assert clone_tool_call.arguments == {
            "repositoryUrl": "https://github.com/modelcontextprotocol/servers",
            "targetPath": "servers",
        }
        branch_tool_call = next(tool_call for tool_call in agent_tool_calls if tool_call.name == "git_branch")
        assert branch_tool_call.arguments in [
            {
                "branchName": "feature/issue-1234",
                "baseBranch": "main",
            },
            {
                "branchName": "feature/issue-1234",
                "mode": "create",
                "startPoint": "main",
            },
        ]

        checkout_tool_call = next(tool_call for tool_call in agent_tool_calls if tool_call.name == "git_checkout")
        assert checkout_tool_call.arguments == {
            "branchOrPath": "feature/issue-1234",
        }

        return agent, instructions, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the remote was successfully added
        2. that the remote URL was correctly set
        3. that the remote was verified to be accessible
        4. that the remote was listed in the remote list
        5. that the agent used the correct sequence of git commands

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_remote_management(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        instructions = """
        1. Clone the repository https://github.com/modelcontextprotocol/servers
        2. Add a new remote called 'upstream' pointing to https://github.com/modelcontextprotocol/servers.git
        3. Verify the remote was added correctly
        4. List all remotes to confirm
        """

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify remote was added
        assert "upstream" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 3
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        assert "git_clone" in tool_call_names
        assert "git_remote" in tool_call_names

        remote_add_tool_call = next(
            tool_call for tool_call in agent_tool_calls if tool_call.name == "git_remote" and tool_call.arguments.get("mode") == "add"
        )
        assert remote_add_tool_call.arguments == {
            "name": "upstream",
            "url": "https://github.com/modelcontextprotocol/servers.git",
            "mode": "add",
        }

        show_tool_call = next(
            tool_call for tool_call in agent_tool_calls if tool_call.name == "git_remote" and tool_call.arguments.get("mode") == "show"
        )
        assert show_tool_call.arguments == {
            "name": "upstream",
            "mode": "show",
        }

        list_tool_call = next(
            tool_call for tool_call in agent_tool_calls if tool_call.name == "git_remote" and tool_call.arguments.get("mode") == "list"
        )
        assert list_tool_call.arguments == {
            "mode": "list",
        }

        return agent, instructions, text_result
