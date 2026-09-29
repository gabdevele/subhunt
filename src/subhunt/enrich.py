import asyncio
import hashlib
import re
import socket
import ssl
from dataclasses import dataclass

import dns.asyncresolver
import dns.exception
import httpx
from cryptography import x509

from .models import Enrichment

MAX_BODY = 200_000

SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
)

TECH_SIGNATURES = (
    ("WordPress", "body", r"wp-content|wp-includes"),
    ("Drupal", "header", r"x-generator:\s*drupal"),
    ("Drupal", "body", r"sites/default/files"),
    ("Joomla", "body", r"/components/com_"),
    ("Magento", "cookie", r"frontend="),
    ("Shopify", "header", r"x-shopid|x-shardid"),
    ("Jenkins", "header", r"x-jenkins"),
    ("Grafana", "body", r"grafana"),
    ("Kibana", "header", r"kbn-name"),
    ("Elasticsearch", "body", r"you know, for search"),
    ("PHP", "header", r"x-powered-by:\s*php"),
    ("ASP.NET", "header", r"x-aspnet-version|x-powered-by:\s*asp\.net"),
    ("Ruby on Rails", "header", r"x-runtime|x-powered-by:\s*phusion"),
    ("Django", "cookie", r"csrftoken"),
    ("Laravel", "cookie", r"laravel_session|xsrf-token"),
    ("Spring Boot", "body", r"whitelabel error page|/actuator"),
    ("Express", "header", r"x-powered-by:\s*express"),
    ("Next.js", "body", r"/_next/"),
    ("Angular", "body", r"ng-version="),
    ("React", "body", r"react(?:-dom)?[.\-]"),
    ("Vue.js", "body", r"vue(?:\.min)?\.js|data-v-"),
    ("Nginx", "server", r"nginx"),
    ("Apache", "server", r"apache"),
    ("IIS", "server", r"microsoft-iis"),
    ("Tomcat", "server", r"coyote|tomcat"),
    ("Cloudflare", "header", r"cf-ray"),
    ("Varnish", "header", r"x-varnish"),
    ("Fastly", "header", r"x-served-by|x-fastly"),
    ("Akamai", "header", r"x-akamai"),
)

TAKEOVER_SERVICES = (
    ("GitHub Pages", ("github.io",), r"there isn't a github pages site here"),
    ("Heroku", ("herokuapp.com", "herokudns.com"), r"no such app"),
    (
        "AWS S3",
        ("s3.amazonaws.com", "s3-website"),
        r"nosuchbucket|the specified bucket does not exist",
    ),
    (
        "Azure",
        ("azurewebsites.net", "cloudapp.azure.com", "trafficmanager.net", "azurefd.net"),
        r"404 web site not found",
    ),
    ("Shopify", ("myshopify.com",), r"sorry, this shop is currently unavailable"),
    ("Fastly", ("fastly.net",), r"fastly error: unknown domain"),
    ("Pantheon", ("pantheonsite.io",), r"the gods are wise, but do not know of the site"),
    ("Zendesk", ("zendesk.com",), r"help center closed"),
    ("Netlify", ("netlify.app", "netlify.com"), r"not found - request id"),
    ("Vercel", ("vercel.app", "now.sh"), r"the deployment could not be found"),
    ("Surge", ("surge.sh",), r"project not found"),
    ("Tumblr", ("tumblr.com",), r"there's nothing here"),
    ("WordPress", ("wordpress.com",), r"do you want to register"),
    ("Readme", ("readme.io",), r"project doesnt exist"),
    ("Bitbucket", ("bitbucket.io",), r"repository not found"),
    ("Unbounce", ("unbouncepages.com",), r"the requested url was not found"),
)


@dataclass(frozen=True)
class EnrichOptions:
    enrich: bool = False
    takeover: bool = False

    @property
    def active(self) -> bool:
        return self.enrich or self.takeover


def missing_headers(response: httpx.Response) -> list[str]:
    present = {key.lower() for key in response.headers}
    return [header for header in SECURITY_HEADERS if header not in present]


def detect_tech(response: httpx.Response) -> list[str]:
    sources = {
        "header": "\n".join(f"{k}: {v}" for k, v in response.headers.items()).lower(),
        "cookie": "\n".join(response.headers.get_list("set-cookie")).lower(),
        "server": response.headers.get("server", "").lower(),
        "body": response.text[:MAX_BODY].lower(),
    }
    found: list[str] = []
    for name, source, pattern in TECH_SIGNATURES:
        if name not in found and re.search(pattern, sources[source]):
            found.append(name)
    return found


async def favicon_hash(client: httpx.AsyncClient, host: str) -> str | None:
    response = await _get(client, f"https://{host}/favicon.ico")
    if response is None or response.status_code != 200 or not response.content:
        return None
    if len(response.content) > MAX_BODY:
        return None
    return hashlib.sha256(response.content).hexdigest()[:16]


def tls_info(host: str, timeout: float = 5.0) -> tuple[str, str, list[str]] | None:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with (
            socket.create_connection((host, 443), timeout=timeout) as raw,
            context.wrap_socket(raw, server_hostname=host) as tls,
        ):
            der = tls.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError):
        return None
    if der is None:
        return None
    return _parse_cert(der)


def _parse_cert(der: bytes) -> tuple[str, str, list[str]] | None:
    try:
        cert = x509.load_der_x509_certificate(der)
        expires = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after
        sans: list[str] = []
        try:
            extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            sans = extension.value.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            pass
        return cert.issuer.rfc4514_string(), expires.date().isoformat(), sans
    except (TypeError, ValueError):
        return None


async def cname_target(host: str) -> str | None:
    try:
        answer = await dns.asyncresolver.resolve(host, "CNAME")
    except dns.exception.DNSException:
        return None
    return str(answer[0].target).rstrip(".").lower()


async def detect_takeover(host: str, response: httpx.Response) -> str | None:
    target = await cname_target(host)
    if target is None:
        return None
    for service, suffixes, signature in TAKEOVER_SERVICES:
        if target.endswith(suffixes) and re.search(signature, response.text, re.IGNORECASE):
            return service
    return None


def make_enricher(options: EnrichOptions):
    async def enricher(
        host: str, response: httpx.Response, client: httpx.AsyncClient
    ) -> Enrichment:
        result = Enrichment()
        if options.enrich:
            result.missing_headers = missing_headers(response)
            result.tech = detect_tech(response)
            result.favicon = await favicon_hash(client, host)
            info = await asyncio.to_thread(tls_info, host)
            if info is not None:
                result.tls_issuer, result.tls_expires, result.tls_sans = info
        if options.takeover:
            result.takeover = await detect_takeover(host, response)
        return result

    return enricher


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        return await client.get(url)
    except httpx.HTTPError:
        return None
