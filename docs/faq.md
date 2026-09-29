# FAQ

**Does subhunt exploit or attack anything?**
No. It performs passive enumeration, DNS resolution and HTTP requests to
determine whether in-scope hosts are alive. It does not send payloads or test
for vulnerabilities.

**Does it only touch in-scope hosts?**
Hosts are kept only if they match an in-scope pattern and do not match any
out-of-scope pattern from the program's structured scope. You still remain
responsible for following the program's policy.

**Do I need Go or extra binaries?**
No. The built-in enumeration uses public Certificate Transparency APIs, and DNS
and HTTP are handled by Python libraries. `subfinder` is optional and improves
coverage.

**Where are my credentials stored?**
In your OS keyring when available (Secret Service on Linux, Keychain on macOS,
Credential Manager on Windows), otherwise in `credentials.json` with `0600`
permissions. Environment variables take precedence. See
[Configuration](configuration.md).

**Does subhunt send my data anywhere?**
It contacts only the HackerOne API, the public enumeration sources
(`crt.sh`, `crt.name`, `agniops`, `jsmon`, or `subfinder` sources), and the
in-scope target hosts for DNS/HTTP checks. Nothing is sent to the author.

**Which platforms and Python versions are supported?**
HackerOne on Linux, macOS and Windows, with Python 3.11, 3.12 and 3.13.

**Does it work on a headless server?**
Yes. If no keyring backend is available, credentials fall back to the `0600`
file, or you can use environment variables.
