import csv
import io
import json

from rich.console import Console
from rich.table import Table

from .models import LiveHost


def render_table(hosts: list[LiveHost], console: Console) -> None:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("HOST", no_wrap=True)
    table.add_column("STATUS", justify="right")
    table.add_column("URL", overflow="fold")
    table.add_column("TITLE", overflow="ellipsis", max_width=40)
    table.add_column("IPS", overflow="fold")
    for item in hosts:
        table.add_row(
            item.host,
            str(item.status or ""),
            item.url or "",
            item.title or "",
            ", ".join(item.ips),
        )
    console.print(table)


def to_json(hosts: list[LiveHost]) -> str:
    return json.dumps([item.to_dict() for item in hosts], indent=2)


def to_csv(hosts: list[LiveHost]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["host", "status", "url", "title", "server", "ips"])
    for item in hosts:
        writer.writerow(
            [
                item.host,
                item.status or "",
                item.url or "",
                item.title or "",
                item.server or "",
                ",".join(item.ips),
            ]
        )
    return buffer.getvalue()


def to_markdown(hosts: list[LiveHost]) -> str:
    lines = ["| Host | Status | URL | Title |", "| --- | --- | --- | --- |"]
    for item in hosts:
        title = (item.title or "").replace("|", "\\|")
        lines.append(f"| {item.host} | {item.status or ''} | {item.url or ''} | {title} |")
    return "\n".join(lines)


def load_hosts(path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {item["host"] if isinstance(item, dict) else str(item) for item in payload}
    return set()
