"""
IP Reputation database models.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON, Text
from datetime import datetime, timezone

from app.database import Base


class IPReputation(Base):
    """Cached IP reputation data from external threat intelligence providers."""
    __tablename__ = "ip_reputation"

    ip = Column(String(45), primary_key=True, index=True)
    abuse_score = Column(Integer, default=0)          # 0–100
    country = Column(String(100), nullable=True)
    isp = Column(String(255), nullable=True)
    usage_type = Column(String(100), nullable=True)    # hosting, residential, business, etc.
    is_proxy = Column(Boolean, default=False)
    is_vpn = Column(Boolean, default=False)
    is_tor = Column(Boolean, default=False)
    is_malicious = Column(Boolean, default=False)
    threat_flags = Column(JSON, nullable=True)         # ["proxy", "vpn", "bot", "spam", ...]
    domain = Column(String(255), nullable=True)        # Reverse DNS
    asn = Column(String(50), nullable=True)            # Autonomous System Number
    asn_org = Column(String(255), nullable=True)       # ASN organization
    raw_json = Column(Text, nullable=True)             # Full API response
    provider = Column(String(50), nullable=True)       # Which provider was used
    last_checked = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "abuse_score": self.abuse_score,
            "country": self.country,
            "isp": self.isp,
            "usage_type": self.usage_type,
            "is_proxy": self.is_proxy,
            "is_vpn": self.is_vpn,
            "is_tor": self.is_tor,
            "is_malicious": self.is_malicious,
            "threat_flags": self.threat_flags or [],
            "domain": self.domain,
            "asn": self.asn,
            "asn_org": self.asn_org,
            "provider": self.provider,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
        }

    def get_status(self) -> str:
        """Return SAFE, SUSPICIOUS, or MALICIOUS based on abuse score."""
        if self.abuse_score >= 70:
            return "MALICIOUS"
        elif self.abuse_score >= 30:
            return "SUSPICIOUS"
        return "SAFE"