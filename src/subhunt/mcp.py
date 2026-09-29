import json

from mcp.server.mcpserver import MCPServer

from . import __version__
from .alive import check_hosts
from .enumerate import enumerate_domain, make_client
from .h1 import H1Client, load_scope

mcp = MCPServer(
    "subhunt",
    version=__version__,
    instructions="Find live, in-scope subdomains for HackerOne bug bounty programs.",
)


async def _live_hosts(
    handle: str,
    *,
    include_non_bounty: bool = False,
    only_wildcards: bool = False,
    dns_only: bool = False,
):
    with H1Client.from_env() as client:
        scope = load_scope(client, handle, include_non_bounty=include_non_bounty)

    hosts: set[str] = set()
    async with make_client() as http:
        for apex in scope.apexes(only_wildcards):
            hosts |= set(await enumerate_domain(apex, client=http))
    candidates = scope.keep(sorted(hosts), only_wildcards)
    return await check_hosts(candidates, dns_only=dns_only)


@mcp.tool()
async def find_live_subdomains(
    handle: str,
    include_non_bounty: bool = False,
    only_wildcards: bool = False,
    dns_only: bool = False,
) -> str:
    """Enumerate live, in-scope subdomains for a HackerOne program handle."""
    hosts = await _live_hosts(
        handle,
        include_non_bounty=include_non_bounty,
        only_wildcards=only_wildcards,
        dns_only=dns_only,
    )
    return json.dumps([item.to_dict() for item in hosts], ensure_ascii=False)


@mcp.tool()
def get_scope(handle: str, include_non_bounty: bool = False, only_wildcards: bool = False) -> str:
    """Return the parsed in-scope, out-of-scope and apex patterns for a program."""
    with H1Client.from_env() as client:
        scope = load_scope(client, handle, include_non_bounty=include_non_bounty)
    return json.dumps(
        {
            "program": handle,
            "in_scope": scope.in_scope_patterns(only_wildcards),
            "out_of_scope": scope.out_of_scope_patterns(),
            "apexes": scope.apexes(only_wildcards),
            "exclusions": [item.category for item in scope.exclusions],
        },
        ensure_ascii=False,
    )


def run() -> None:
    mcp.run()
