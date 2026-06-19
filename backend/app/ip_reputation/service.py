"""
IP Reputation Service.

Provides:
  - Multi-provider IP reputation lookups with fallback
  - In-memory cache with TTL
  - Async HTTP client via httpx
  - Rate limiting for external API calls
  - AbuseIPDB, VirusTotal, IPQualityScore integration
"""

import asyncio
import json
import logging
import time
import socket
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict

import httpx
from sqlalchemy import select, update

from app.config import settings
from app.database import async_session
from app.ip_reputation.models import IPReputation

logger = logging.getLogger("server-stats.ip-reputation")


# ── Simple TTL Cache ────────────────────────────────────────────────────

class TTLCache:
    """Thread-safe in-memory cache with TTL eviction."""

    def __init__(self, maxsize: int = 10000, ttl: int = 1800):
        self._cache: OrderedDict[str, Tuple[float, dict]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[dict]:
        async with self._lock:
            if key not in self._cache:
                return None
            ts, value = self._cache[key]
            if time.time() - ts > self._ttl:
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: dict):
        async with self._lock:
            if len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)  # Remove oldest
            self._cache[key] = (time.time(), value)

    async def clear(self):
        async with self._lock:
            self._cache.clear()

    @property
    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)


# ── Rate Limiter ────────────────────────────────────────────────────────

class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, max_calls: int, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a slot is available."""
        while True:
            async with self._lock:
                now = time.time()
                # Remove old calls
                self._calls = [t for t in self._calls if now - t < self.period]
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return
            # Wait before retrying
            await asyncio.sleep(1)

    @property
    async def remaining(self) -> int:
        async with self._lock:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < self.period]
            return max(0, self.max_calls - len(self._calls))


# ── Provider Implementations ────────────────────────────────────────────

class AbuseIPDBProvider:
    """AbuseIPDB API v2 provider."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._enabled = bool(api_key)

    async def lookup(self, ip: str, client: httpx.AsyncClient) -> Optional[dict]:
        """Check IP reputation via AbuseIPDB."""
        if not self._enabled:
            return None
        try:
            response = await client.get(
                f"{self.base_url}/check",
                params={"ipAddress": ip, "maxAgeInDays": "90", "verbose": ""},
                headers={"Key": self.api_key, "Accept": "application/json"},
                timeout=10.0,
            )
            if response.status_code == 429:
                logger.warning(f"AbuseIPDB rate limited for {ip}")
                return None
            if response.status_code != 200:
                logger.warning(f"AbuseIPDB error for {ip}: {response.status_code}")
                return None

            data = response.json().get("data", {})
            return {
                "abuse_score": data.get("abuseConfidenceScore", 0),
                "country": data.get("countryCode") or data.get("countryName"),
                "isp": data.get("isp"),
                "usage_type": data.get("usageType"),
                "is_proxy": data.get("isProxy", False),
                "is_vpn": data.get("isVPN", False),
                "is_tor": data.get("isTor", False),
                "domain": data.get("domain"),
                "threat_flags": self._extract_threats(data),
                "raw_json": json.dumps(data),
            }
        except Exception as e:
            logger.error(f"AbuseIPDB lookup error for {ip}: {e}")
            return None

    def _extract_threats(self, data: dict) -> List[str]:
        flags = []
        if data.get("isProxy"):
            flags.append("proxy")
        if data.get("isVPN"):
            flags.append("vpn")
        if data.get("isTor"):
            flags.append("tor")
        if data.get("isBot"):
            flags.append("bot")
        if data.get("abuseConfidenceScore", 0) > 50:
            flags.append("malicious")
        return flags


class VirusTotalProvider:
    """VirusTotal API v3 provider."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._enabled = bool(api_key)

    async def lookup(self, ip: str, client: httpx.AsyncClient) -> Optional[dict]:
        """Check IP reputation via VirusTotal."""
        if not self._enabled:
            return None
        try:
            response = await client.get(
                f"{self.base_url}/ip_addresses/{ip}",
                headers={"x-apikey": self.api_key, "Accept": "application/json"},
                timeout=10.0,
            )
            if response.status_code == 429:
                logger.warning(f"VirusTotal rate limited for {ip}")
                return None
            if response.status_code != 200:
                logger.warning(f"VirusTotal error for {ip}: {response.status_code}")
                return None

            data = response.json().get("data", {})
            attributes = data.get("attributes", {})
            last_analysis = attributes.get("last_analysis_stats", {})

            # Calculate abuse score from detection ratio
            malicious = last_analysis.get("malicious", 0)
            suspicious = last_analysis.get("suspicious", 0)
            total = sum(last_analysis.values()) or 1
            abuse_score = min(100, int(((malicious + suspicious) / total) * 100))

            # Extract threat flags
            threat_flags = []
            if malicious > 0:
                threat_flags.append("malicious")
            if suspicious > 0:
                threat_flags.append("suspicious")

            return {
                "abuse_score": abuse_score,
                "country": attributes.get("country"),
                "isp": attributes.get("as_owner"),
                "usage_type": None,
                "is_proxy": attributes.get("proxy", False),
                "is_vpn": attributes.get("vpn", False),
                "is_tor": attributes.get("tor", False),
                "domain": attributes.get("reverse_dns"),
                "threat_flags": threat_flags,
                "raw_json": json.dumps(data),
                "asn": attributes.get("asn"),
                "asn_org": attributes.get("as_owner"),
            }
        except Exception as e:
            logger.error(f"VirusTotal lookup error for {ip}: {e}")
            return None


class IPQualityScoreProvider:
    """IPQualityScore API provider."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._enabled = bool(api_key)

    async def lookup(self, ip: str, client: httpx.AsyncClient) -> Optional[dict]:
        """Check IP reputation via IPQualityScore."""
        if not self._enabled:
            return None
        try:
            response = await client.get(
                f"{self.base_url}/{self.api_key}/{ip}",
                timeout=10.0,
            )
            if response.status_code == 429:
                logger.warning(f"IPQualityScore rate limited for {ip}")
                return None
            if response.status_code != 200:
                logger.warning(f"IPQualityScore error for {ip}: {response.status_code}")
                return None

            data = response.json()
            if data.get("success") is False:
                logger.warning(f"IPQualityScore lookup failed for {ip}: {data.get('message', '')}")
                return None

            fraud_score = data.get("fraud_score", 0)
            threat_flags = []
            if data.get("proxy", False):
                threat_flags.append("proxy")
            if data.get("vpn", False):
                threat_flags.append("vpn")
            if data.get("tor", False):
                threat_flags.append("tor")
            if data.get("bot_status", False):
                threat_flags.append("bot")
            if fraud_score > 50:
                threat_flags.append("malicious")

            return {
                "abuse_score": fraud_score,
                "country": data.get("country_code"),
                "isp": data.get("ISP"),
                "usage_type": data.get("organization"),
                "is_proxy": data.get("proxy", False),
                "is_vpn": data.get("vpn", False),
                "is_tor": data.get("tor", False),
                "is_malicious": fraud_score > 75,
                "domain": data.get("reverse_dns"),
                "threat_flags": threat_flags,
                "asn": data.get("ASN"),
                "asn_org": data.get("organization"),
                "raw_json": json.dumps(data),
            }
        except Exception as e:
            logger.error(f"IPQualityScore lookup error for {ip}: {e}")
            return None


# ── Main Reputation Service ──────────────────────────────────────────────

class IPReputationService:
    """
    Main service for IP reputation lookups with:
      - Multi-provider support with fallback
      - In-memory caching
      - SQLite persistence
      - Rate limiting
      - Reverse DNS lookup
    """

    def __init__(self):
        self.cache = TTLCache(maxsize=20000, ttl=settings.ip_reputation_cache_ttl)
        self.rate_limiter = RateLimiter(max_calls=settings.ip_reputation_rate_limit)
        self._http_client: Optional[httpx.AsyncClient] = None

        # Initialize providers
        self.providers = [
            AbuseIPDBProvider(
                settings.abuseipdb_api_key,
                settings.abuseipdb_base_url,
            ),
            VirusTotalProvider(
                settings.virustotal_api_key,
                settings.virustotal_base_url,
            ),
            IPQualityScoreProvider(
                settings.ipqualityscore_api_key,
                settings.ipqualityscore_base_url,
            ),
        ]

        # Filter to only enabled providers
        self.providers = [p for p in self.providers if p._enabled]

        if not self.providers:
            logger.warning("No IP reputation providers configured. "
                           "Set ABUSEIPDB_API_KEY, VIRUSTOTAL_API_KEY, or IPQUALITYSCORE_API_KEY in .env")

    @property
    async def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                timeout=httpx.Timeout(15.0),
            )
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _reverse_dns(self, ip: str) -> Optional[str]:
        """Perform reverse DNS lookup."""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror, OSError):
            return None

    async def _merge_results(self, results: List[dict]) -> dict:
        """Merge results from multiple providers, preferring higher scores."""
        if not results:
            return {}

        merged = {
            "abuse_score": 0,
            "country": None,
            "isp": None,
            "usage_type": None,
            "is_proxy": False,
            "is_vpn": False,
            "is_tor": False,
            "is_malicious": False,
            "domain": None,
            "asn": None,
            "asn_org": None,
            "threat_flags": [],
            "raw_json": None,
            "provider": results[0].get("provider", "unknown"),
        }

        for result in results:
            # Take the highest abuse score
            if result.get("abuse_score", 0) > merged["abuse_score"]:
                merged["abuse_score"] = result["abuse_score"]

            # Take first non-null value for each field
            if result.get("country") and not merged["country"]:
                merged["country"] = result["country"]
            if result.get("isp") and not merged["isp"]:
                merged["isp"] = result["isp"]
            if result.get("usage_type") and not merged["usage_type"]:
                merged["usage_type"] = result["usage_type"]
            if result.get("domain") and not merged["domain"]:
                merged["domain"] = result["domain"]
            if result.get("asn") and not merged["asn"]:
                merged["asn"] = result["asn"]
            if result.get("asn_org") and not merged["asn_org"]:
                merged["asn_org"] = result["asn_org"]

            # Boolean flags: OR them together
            if result.get("is_proxy"):
                merged["is_proxy"] = True
            if result.get("is_vpn"):
                merged["is_vpn"] = True
            if result.get("is_tor"):
                merged["is_tor"] = True
            if result.get("is_malicious"):
                merged["is_malicious"] = True

            # Combine threat flags
            for flag in result.get("threat_flags", []):
                if flag not in merged["threat_flags"]:
                    merged["threat_flags"].append(flag)

            # Store first raw JSON
            if result.get("raw_json") and not merged["raw_json"]:
                merged["raw_json"] = result["raw_json"]
                merged["provider"] = result.get("provider", "unknown")

        # Determine is_malicious based on threshold
        if merged["abuse_score"] >= settings.ip_reputation_abuse_threshold:
            merged["is_malicious"] = True

        return merged

    async def check_ip(self, ip: str) -> dict:
        """
        Check an IP address reputation.
        Returns cached result if available, otherwise queries external providers.
        """
        # 1. Check in-memory cache
        cached = await self.cache.get(ip)
        if cached:
            logger.debug(f"Cache hit for IP {ip}")
            return cached

        # 2. Check SQLite cache
        async with async_session() as session:
            result = await session.execute(
                select(IPReputation).where(IPReputation.ip == ip)
            )
            db_record = result.scalar_one_or_none()

            if db_record:
                # Check if TTL has expired
                if db_record.last_checked:
                    # SQLite stores naive datetimes, make them aware for comparison
                    lc = db_record.last_checked
                    if lc and lc.tzinfo is None:
                        lc = lc.replace(tzinfo=timezone.utc)
                    age = (datetime.now(timezone.utc) - lc).total_seconds()
                    if age < settings.ip_reputation_cache_ttl:
                        cached_dict = db_record.to_dict()
                        await self.cache.set(ip, cached_dict)
                        logger.debug(f"DB cache hit for IP {ip} (age: {age:.0f}s)")
                        return cached_dict
                # Expired — will re-fetch

        # 3. Query external providers
        if not settings.ip_reputation_enabled:
            # Return a basic record
            basic = {
                "ip": ip,
                "abuse_score": 0,
                "country": None,
                "isp": None,
                "usage_type": None,
                "is_proxy": False,
                "is_vpn": False,
                "is_tor": False,
                "is_malicious": False,
                "threat_flags": [],
                "domain": None,
                "asn": None,
                "asn_org": None,
                "provider": None,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
            await self.cache.set(ip, basic)
            return basic

        # Rate limit
        await self.rate_limiter.acquire()

        # Query all providers with timeout
        client = await self.http_client
        results = []
        for provider in self.providers:
            try:
                result = await provider.lookup(ip, client)
                if result:
                    result["provider"] = provider.__class__.__name__.replace("Provider", "")
                    results.append(result)
                    break  # Use first successful provider
            except Exception as e:
                logger.error(f"{provider.__class__.__name__} failed for {ip}: {e}")

        if not results:
            logger.warning(f"All providers failed for IP {ip}, trying reverse DNS only")
            domain = await self._reverse_dns(ip)
            merged = {
                "abuse_score": 0,
                "country": None,
                "isp": None,
                "usage_type": None,
                "is_proxy": False,
                "is_vpn": False,
                "is_tor": False,
                "is_malicious": False,
                "threat_flags": [],
                "domain": domain,
                "asn": None,
                "asn_org": None,
                "raw_json": None,
                "provider": "reverse_dns_only",
            }
        else:
            merged = await self._merge_results(results)

        # Enrich with reverse DNS if not already set
        if not merged.get("domain"):
            try:
                merged["domain"] = await self._reverse_dns(ip)
            except Exception:
                pass

        merged["ip"] = ip
        merged["last_checked"] = datetime.now(timezone.utc).isoformat()

        # 4. Save to SQLite
        try:
            async with async_session() as session:
                # Upsert
                stmt = select(IPReputation).where(IPReputation.ip == ip)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.abuse_score = merged["abuse_score"]
                    existing.country = merged.get("country")
                    existing.isp = merged.get("isp")
                    existing.usage_type = merged.get("usage_type")
                    existing.is_proxy = merged["is_proxy"]
                    existing.is_vpn = merged["is_vpn"]
                    existing.is_tor = merged["is_tor"]
                    existing.is_malicious = merged["is_malicious"]
                    existing.threat_flags = json.dumps(merged.get("threat_flags", []))
                    existing.domain = merged.get("domain")
                    existing.asn = merged.get("asn")
                    existing.asn_org = merged.get("asn_org")
                    existing.raw_json = merged.get("raw_json")
                    existing.provider = merged.get("provider")
                    existing.last_checked = datetime.now(timezone.utc)
                else:
                    session.add(IPReputation(
                        ip=ip,
                        abuse_score=merged["abuse_score"],
                        country=merged.get("country"),
                        isp=merged.get("isp"),
                        usage_type=merged.get("usage_type"),
                        is_proxy=merged["is_proxy"],
                        is_vpn=merged["is_vpn"],
                        is_tor=merged["is_tor"],
                        is_malicious=merged["is_malicious"],
                        threat_flags=json.dumps(merged.get("threat_flags", [])),
                        domain=merged.get("domain"),
                        asn=merged.get("asn"),
                        asn_org=merged.get("asn_org"),
                        raw_json=merged.get("raw_json"),
                        provider=merged.get("provider"),
                        last_checked=datetime.now(timezone.utc),
                    ))
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save IP reputation for {ip}: {e}")

        # 5. Cache in memory
        await self.cache.set(ip, merged)

        return merged

    async def batch_check(self, ips: List[str]) -> Dict[str, dict]:
        """Check multiple IPs and return results as dict keyed by IP."""
        results = {}
        tasks = []

        for ip in ips:
            # Check cache first
            cached = await self.cache.get(ip)
            if cached:
                results[ip] = cached
            else:
                tasks.append(ip)

        # Query uncached IPs with concurrency limit
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent lookups

        async def lookup(ip: str):
            async with semaphore:
                try:
                    result = await self.check_ip(ip)
                    results[ip] = result
                except Exception as e:
                    logger.error(f"Batch lookup error for {ip}: {e}")
                    results[ip] = {"ip": ip, "abuse_score": 0, "error": str(e)}

        if tasks:
            await asyncio.gather(*[lookup(ip) for ip in tasks])

        return results

    async def get_stats(self) -> dict:
        """Get summary statistics about IP reputation data."""
        from sqlalchemy import func

        async with async_session() as session:
            # Total unique IPs checked
            result = await session.execute(
                select(func.count(IPReputation.ip))
            )
            total_checked = result.scalar() or 0

            # Malicious IPs
            result = await session.execute(
                select(func.count(IPReputation.ip))
                .where(IPReputation.is_malicious == True)
            )
            malicious_count = result.scalar() or 0

            # Suspicious (abuse_score >= 30 but < 70)
            result = await session.execute(
                select(func.count(IPReputation.ip))
                .where(IPReputation.abuse_score >= 30)
                .where(IPReputation.abuse_score < 70)
            )
            suspicious_count = result.scalar() or 0

            # Top countries
            result = await session.execute(
                select(IPReputation.country, func.count(IPReputation.ip).label("count"))
                .where(IPReputation.country != None)
                .group_by(IPReputation.country)
                .order_by(func.count(IPReputation.ip).desc())
                .limit(10)
            )
            top_countries = [
                {"country": row.country, "count": row.count}
                for row in result.all()
            ]

            # Proxy / VPN / Tor flagged
            result = await session.execute(
                select(func.count(IPReputation.ip))
                .where(
                    (IPReputation.is_proxy == True) |
                    (IPReputation.is_vpn == True) |
                    (IPReputation.is_tor == True)
                )
            )
            flagged_count = result.scalar() or 0

            # Average abuse score
            result = await session.execute(
                select(func.avg(IPReputation.abuse_score))
            )
            avg_score = result.scalar() or 0.0

            # Cache stats
            cache_size = await self.cache.size
            rate_limit_remaining = await self.rate_limiter.remaining

        malicious_pct = round((malicious_count / total_checked * 100), 2) if total_checked > 0 else 0.0

        return {
            "total_ips_checked": total_checked,
            "malicious_count": malicious_count,
            "suspicious_count": suspicious_count,
            "malicious_percentage": malicious_pct,
            "flagged_count": flagged_count,
            "average_abuse_score": round(avg_score, 2),
            "top_countries": top_countries,
            "cache_size": cache_size,
            "rate_limit_remaining": rate_limit_remaining,
        }

    async def get_top_malicious(self, limit: int = 20) -> List[dict]:
        """Get highest risk IPs from the database."""
        async with async_session() as session:
            result = await session.execute(
                select(IPReputation)
                .order_by(IPReputation.abuse_score.desc())
                .limit(limit)
            )
            rows = result.scalars().all()

        return [row.to_dict() for row in rows]


# ── Global service singleton ────────────────────────────────────────────

ip_reputation_service = IPReputationService()