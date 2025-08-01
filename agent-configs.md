Developers and users of this MCP server are responsible for downloading, funding and configuring a LLM agent
to interact with the MCP server. Claude and Goose are common choices. Both have desktop and CLI versions
for at least a few operating systems (but nto necessarily both for all platforms.)

* https://docs.anthropic.com/en/docs/claude-code/setup
* https://docs.anthropic.com/en/docs/claude-code/mcp
* https://block.github.io/goose/docs/quickstart/
* https://block.github.io/goose/docs/getting-started/using-extensions/

For developers development, this repo prioritizes using the Claude CLI for integration testing. We provide a
`agent-configs/local-nmdc-mcp-for-claude.json` configuration file
for running Makefile targets like `local/claude-demo-studies-with-publications.txt`.It launches the live/local
MCP server with `uv run nmdc-mcp`. 

End users will generally want to run the MCP server pacakge that has been published to PyPI, using
`uvx nmdc-mcp`
