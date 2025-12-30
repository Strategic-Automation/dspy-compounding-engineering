import functools
import ipaddress
import socket
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from ..io.logger import logger


class PinnedTransport(httpx.HTTPTransport):
    """
    Custom transport that pins a hostname to a specific IP address.
    Ensures SNI and Host headers remain correct for SSL/TLS validation.
    """

    def __init__(self, hostname: str, pinned_ip: str, **kwargs):
        super().__init__(**kwargs)
        self.hostname = hostname
        self.pinned_ip = pinned_ip

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # If the request matches our target hostname, pin it to the safe IP
        if request.url.host == self.hostname:
            request.url = request.url.copy_with(host=self.pinned_ip)
            # Ensure SNI is set to the original hostname for SSL verification
            request.extensions["sni_hostname"] = self.hostname.encode("ascii")
        return super().handle_request(request)


class DocumentationFetcher:
    """
    Utility for fetching and parsing official documentation from URLs.
    Supports high-quality conversion via r.jina.ai and local fallback.
    """

    def __init__(self, use_jina: bool = True, timeout: int = 10):
        self.use_jina = use_jina
        self.timeout = timeout

    def _is_ip_private(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """
        Check if an IP address is private or reserved.
        Handles IPv4-mapped IPv6 normalization.
        """
        # Normalize IPv4-mapped IPv6 addresses (::ffff:192.168.1.1)
        if isinstance(ip, ipaddress.IPv6Address):
            mapped_ipv4 = ip.ipv4_mapped
            if mapped_ipv4:
                ip = mapped_ipv4

        return (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
        )

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def _resolve_ips(hostname: str) -> List[str]:
        """Resolve hostname to all possible IP addresses with simple caching."""
        try:
            # socket.getaddrinfo handles both v4 and v6
            addr_info = socket.getaddrinfo(hostname, None)
            return list({info[4][0] for info in addr_info}) if addr_info else []
        except socket.gaierror:
            return []

    def _get_safe_ip(self, hostname: str) -> tuple[Optional[str], Optional[str]]:
        """
        Resolve hostname and return (IP, ErrorMsg) only if ALL resolved IPs are safe.
        Returns (first resolved IP, None) if safe, otherwise (None, Reason).
        """
        if not hostname or hostname.lower() in ["localhost", "localhost.localdomain"]:
            return None, "Hostname 'localhost' is not permitted"

        try:
            # Check if it's already a literal IP
            try:
                ip = ipaddress.ip_address(hostname)
                if self._is_ip_private(ip):
                    return None, f"Literal IP {hostname} is a private/internal address"
                return str(ip), None
            except ValueError:
                pass

            # Resolve hostname to all possible IPs
            ips = DocumentationFetcher._resolve_ips(hostname)
            if not ips:
                return None, f"DNS resolution failed for {hostname}"

            # All resolved IPs must be safe
            for ip_str in ips:
                if self._is_ip_private(ipaddress.ip_address(ip_str)):
                    return None, f"Hostname {hostname} resolved to private IP {ip_str}"

            return ips[0], None
        except Exception as e:
            return None, f"Internal error during DNS check: {e}"

    def _is_safe_url(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Check if the URL is safe to fetch (not a private or reserved IP).
        Uses resolved IP to prevent DNS rebinding.
        """
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "URL missing netloc"

            if parsed.scheme not in ["http", "https"]:
                return False, f"Unsupported scheme: {parsed.scheme}"

            hostname = parsed.hostname
            if not hostname:
                return False, "URL missing hostname"

            # This also caches the DNS result for the subsequent fetch
            ip, error = self._get_safe_ip(hostname)
            return ip is not None, error
        except Exception as e:
            return False, f"URL check internal error: {e}"

    def fetch(self, url: str) -> str:
        """
        Fetch documentation from a URL and return it as Markdown.
        """
        if not url.startswith("http"):
            return f"Invalid URL: {url}"

        is_safe, reason = self._is_safe_url(url)
        if not is_safe:
            # Log resolution failure as warning, but potential SSRF as error
            if "DNS resolution failed" in (reason or ""):
                logger.warning(f"Could not fetch {url}: {reason}")
            else:
                logger.error(f"SSRF Protection: Blocked potentially unsafe URL: {url} ({reason})")
            return f"Error: {reason or 'URL is not permitted for security reasons.'}"

        if self.use_jina:
            try:
                content = self._fetch_via_jina(url)
                if content:
                    logger.success(f"Successfully fetched documentation via Jina for {url}")
                    return content
            except Exception as e:
                logger.warning(f"Jina fetch failed for {url}: {e}. Falling back to local parsing.")

        return self._fetch_locally(url)

    def _fetch_via_jina(self, url: str) -> Optional[str]:
        """
        Fetch via r.jina.ai for high-quality markdown.
        """
        # Note: We send the URL to Jina as a string. Jina performs the fetch.
        # We've already validated the URL is safe (not local) in self.fetch().
        jina_url = f"https://r.jina.ai/{url}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(jina_url)
            response.raise_for_status()
            return response.text

    def _fetch_locally(self, url: str) -> str:
        """
        Fallback fetch and parse locally using BeautifulSoup and markdownify.
        Uses IP pinning for DNS rebinding protection.
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            safe_ip = self._get_safe_ip(hostname)

            if not safe_ip:
                return (
                    f"Error: URL {url} resolved to an unsafe or unresolvable address. "
                    "Blocked for security reasons."
                )

            # Use PinnedTransport to prevent DNS rebinding attacks
            transport = PinnedTransport(hostname, safe_ip)
            with httpx.Client(
                timeout=self.timeout, follow_redirects=True, transport=transport
            ) as client:
                response = client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove non-content elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()

                # Convert to markdown
                markdown_content = md(str(soup), heading_style="ATX")
                logger.success(f"Successfully fetched and parsed documentation locally for {url}")
                return markdown_content.strip()
        except Exception as e:
            logger.error(f"Local documentation fetch failed for {url}", detail=str(e))
            return (
                f"Error: Unable to fetch documentation from {url} locally: {e}. "
                "Please check the URL or try again later."
            )
