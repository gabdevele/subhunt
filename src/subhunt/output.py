import csv
import io
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .models import Enrichment, LiveHost


def finding_summary(enrichment: Enrichment | None) -> str:
    if not enrichment:
        return ""
    parts = []
    if enrichment.takeover:
        parts.append(f"TAKEOVER={enrichment.takeover}")
    if enrichment.tech:
        parts.append("tech=" + ",".join(enrichment.tech[:4]))
    if enrichment.missing_headers:
        parts.append(f"missing-hdr={len(enrichment.missing_headers)}")
    return " · ".join(parts)


def render_table(hosts: list[LiveHost], console: Console) -> None:
    enriched = any(item.enrichment for item in hosts)
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("HOST", no_wrap=True)
    table.add_column("STATUS", justify="right")
    table.add_column("TITLE", overflow="ellipsis", max_width=40)
    if enriched:
        table.add_column("TECH", overflow="fold")
        table.add_column("FINDINGS", overflow="fold")
    table.add_column("IPS", overflow="fold")
    for item in hosts:
        row = [item.host, str(item.status or ""), item.title or ""]
        if enriched:
            enrichment = item.enrichment
            row.append(", ".join(enrichment.tech) if enrichment else "")
            row.append(finding_summary(enrichment))
        row.append(", ".join(item.ips))
        table.add_row(*row)
    console.print(table)


def to_json(hosts: list[LiveHost]) -> str:
    return json.dumps([item.to_dict() for item in hosts], indent=2)


def to_csv(hosts: list[LiveHost]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["host", "status", "title", "server", "tech", "findings", "ips"])
    for item in hosts:
        writer.writerow(
            [
                item.host,
                item.status or "",
                item.title or "",
                item.server or "",
                ",".join(item.enrichment.tech) if item.enrichment else "",
                finding_summary(item.enrichment),
                ",".join(item.ips),
            ]
        )
    return buffer.getvalue()


def to_markdown(hosts: list[LiveHost]) -> str:
    lines = ["| Host | Status | Title | Tech | Findings |", "| --- | --- | --- | --- | --- |"]
    for item in hosts:
        title = (item.title or "").replace("|", "\\|")
        tech = ", ".join(item.enrichment.tech) if item.enrichment else ""
        findings = finding_summary(item.enrichment).replace("|", "\\|")
        lines.append(f"| {item.host} | {item.status or ''} | {title} | {tech} | {findings} |")
    return "\n".join(lines)


def load_hosts(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return set()
    return {item["host"] for item in payload if isinstance(item, dict) and "host" in item}
